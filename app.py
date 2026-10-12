import re
import os
import bcrypt
import pymysql
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from pymysql.constants import CLIENT
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

EMAIL_PATTERN = re.compile(r"^[^@ ]+@[^@ .]+([.][^@ .]+)+$")

def get_db():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                        database=DB_NAME, cursorclass=pymysql.cursors.DictCursor,
                        client_flag=CLIENT.FOUND_ROWS)



@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("todos"))

    if request.method == "GET":
        return render_template("login.html", errors={}, email="")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")


    errors = {}
    if email == "":
        errors["email"] = "Email is required"
    elif not EMAIL_PATTERN.match(email):
        errors["email"] = "Email is not valid"
    if password == "":
        errors["password"] = "Password is required"
    if errors:
        return render_template("login.html", errors=errors, email=email)


    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, name, password_hash FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    conn.close()


    if user is None or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return render_template("login.html", errors={"form": "Invalid email or password"}, email=email)

    session["user_id"] = user["user_id"]
    session["name"] = user["name"]
    return redirect(url_for("todos"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("todos"))

    if request.method == "GET":
        return render_template("register.html", errors={}, name="", email="")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")


    errors = {}
    if name == "":
        errors["name"] = "Name is required"
    if email == "":
        errors["email"] = "Email is required"
    if password == "":
        errors["password"] = "Password is required"
    if confirm_password == "":
        errors["confirm_password"] = "Confirm password is required"
    elif password != confirm_password:
        errors["confirm_password"] = "Passwords do not match"
    if errors:
        return render_template("register.html", errors=errors, name=name, email=email)


    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                    (email, name, password_hash))
        conn.commit()
        new_user_id = cur.lastrowid          
    except pymysql.err.IntegrityError as e:
        if e.args[0] == 1062:                
            return render_template("register.html", errors={"email": "Email Already Exists"},
                                        name=name, email=email)
        raise
    finally:
        conn.close()


    session["user_id"] = new_user_id
    session["name"] = name
    return redirect(url_for("todos"))



def run_write(sql, params):
    """Run one INSERT / UPDATE / DELETE with parameters and return (rows matched, new id)."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount, cur.lastrowid
    finally:
        conn.close()


def api_error(message, status):
    return jsonify({"error": message}), status


@app.route("/todos")
def todos():
    if "user_id" not in session:
        return redirect(url_for("login"))

    tasks, load_error = [], False
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT todo_id, title, is_done, created_at FROM todos "
                    "WHERE user_id = %s ORDER BY todo_id DESC", (session["user_id"],))
        for row in cur.fetchall():
            tasks.append({"id": row["todo_id"], "title": row["title"], "is_done": bool(row["is_done"])})
        conn.close()
    except pymysql.MySQLError:
        load_error = True
    return render_template("todos.html", name=session["name"], tasks=tasks, load_error=load_error)


@app.route("/todos/add", methods=["POST"])
def add_todo():
    if "user_id" not in session:
        return api_error("Please log in again.", 401)

    title = (request.get_json(silent=True) or {}).get("title", "")
    title = title.strip() if isinstance(title, str) else ""


    if title == "":
        return api_error("Title is required", 400)
    if len(title) > 200:
        return api_error("Title is too long (200 characters at most)", 400)

    try:
        _, new_id = run_write("INSERT INTO todos (user_id, title) VALUES (%s, %s)",
                            (session["user_id"], title))
    except pymysql.MySQLError:
        return api_error("Could not add the task. Please try again.", 500)
    return jsonify({"id": new_id, "title": title, "is_done": False}), 201


@app.route("/todos/<int:todo_id>/done", methods=["PATCH"])
def mark_todo(todo_id):
    if "user_id" not in session:
        return api_error("Please log in again.", 401)

    is_done = 1 if (request.get_json(silent=True) or {}).get("is_done") else 0
    try:
        matched, _ = run_write("UPDATE todos SET is_done = %s WHERE todo_id = %s AND user_id = %s",
                            (is_done, todo_id, session["user_id"]))
    except pymysql.MySQLError:
        return api_error("Could not update the task. Please try again.", 500)

    if matched == 0:                       
        return api_error("Task not found.", 404)
    return jsonify({"id": todo_id, "is_done": bool(is_done)})


@app.route("/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id):
    if "user_id" not in session:
        return api_error("Please log in again.", 401)

    try:
        
        deleted, _ = run_write("DELETE FROM todos WHERE todo_id = %s AND user_id = %s",
                            (todo_id, session["user_id"]))
    except pymysql.MySQLError:
        return api_error("Could not delete the task. Please try again.", 500)

    if deleted == 0:
        return api_error("Task not found.", 404)
    return jsonify({"deleted": todo_id})


@app.route("/todos/<int:todo_id>", methods=["PATCH"])
def edit_todo(todo_id):
    if "user_id" not in session:
        return api_error("Please log in again.", 401)

    title = (request.get_json(silent=True) or {}).get("title", "")
    title = title.strip() if isinstance(title, str) else ""

    
    if title == "":
        return api_error("Title is required", 400)
    if len(title) > 200:
        return api_error("Title is too long (200 characters at most)", 400)

    try:
        matched, _ = run_write("UPDATE todos SET title = %s WHERE todo_id = %s AND user_id = %s",
                            (title, todo_id, session["user_id"]))
    except pymysql.MySQLError:
        return api_error("Could not update the task. Please try again.", 500)

    if matched == 0:                      
        return api_error("Task not found.", 404)
    return jsonify({"id": todo_id, "title": title})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
