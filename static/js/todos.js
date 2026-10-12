var filter = "all";

var list = document.getElementById("list");
var emptyBox = document.getElementById("empty");
var msg = document.getElementById("msg");
var TRASH = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>';

var PENCIL = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>';
var CHECK = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>';
var CROSS = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
var editingId = null;     

function showMsg(text) { msg.textContent = text; msg.hidden = false; }
function clearMsg() { msg.hidden = true; }


function api(url, method, body) {
    return fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined
    }).then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
            return { ok: res.ok, data: data };
        });
    }).catch(function () {
        return { ok: false, data: { error: "Cannot reach the server. Please try again." } };
    });
}


function render() {
    var active = tasks.filter(function (t) { return !t.is_done; }).length;
    var done = tasks.length - active;
    var tabs = document.querySelectorAll(".tab");
    tabs.forEach(function (tab) {
        var f = tab.dataset.filter;
        var count = f === "all" ? tasks.length : (f === "active" ? active : done);
        var label = f === "all" ? "All" : (f === "active" ? "Active" : "Completed");
        tab.textContent = label + " (" + count + ")";
        tab.classList.toggle("active", f === filter);
    });

    var shown = tasks.filter(function (t) {
        if (filter === "active") return !t.is_done;
        if (filter === "completed") return t.is_done;
        return true;
    });

    list.innerHTML = "";
    shown.forEach(function (t) { list.appendChild(makeItem(t)); });

    if (shown.length === 0) {
        emptyBox.textContent = tasks.length === 0 ? "No tasks yet. Add your first task above."
                            : filter === "active" ? "There's no current Tasks!"
                            : "No completed tasks yet.";
        emptyBox.hidden = false;
    } else {
        emptyBox.hidden = true;
    }
}

function iconButton(extraClass, label, svg, handler) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "icon " + extraClass;
    b.title = label;
    b.setAttribute("aria-label", label);
    b.innerHTML = svg;
    b.addEventListener("click", handler);
    return b;
}

function makeItem(t) {
    var li = document.createElement("li");
    li.className = "item" + (t.is_done ? " done" : "");

    var box = document.createElement("input");
    box.type = "checkbox";
    box.checked = t.is_done;
    box.setAttribute("aria-label", "Mark as complete");
    box.addEventListener("change", function () { toggleTask(t, box); });
    li.appendChild(box);

    if (t.id === editingId) {
        var input = document.createElement("input");
        input.type = "text";
        input.className = "edit-input";
        input.value = t.title;
        input.setAttribute("aria-label", "Edit task");
        input.addEventListener("keydown", function (e) {
            if (e.key === "Enter") { e.preventDefault(); saveEdit(t, input); }
            else if (e.key === "Escape") { cancelEdit(); }
        });
        li.appendChild(input);
        li.appendChild(iconButton("ok", "Save", CHECK, function () { saveEdit(t, input); }));
        li.appendChild(iconButton("", "Cancel", CROSS, cancelEdit));
        setTimeout(function () { input.focus(); input.select(); }, 0);
    } else {
        var title = document.createElement("span");
        title.className = "title";
        title.textContent = t.title;         
        li.appendChild(title);
        li.appendChild(iconButton("edit", "Edit", PENCIL, function () { startEdit(t); }));
        li.appendChild(iconButton("", "Delete", TRASH, function (e) { deleteTask(t, e.currentTarget); }));
    }
    return li;
}


document.getElementById("addForm").addEventListener("submit", function (e) {
    e.preventDefault();                   
    var input = document.getElementById("newTitle");
    var title = input.value.trim();

    if (title === "") { showMsg("Title is required"); return; }
    if (title.length > 200) { showMsg("Title is too long (200 characters at most)"); return; }

    api("/todos/add", "POST", { title: title }).then(function (r) {
        if (r.ok) {
            clearMsg();
            tasks.unshift({ id: r.data.id, title: r.data.title, is_done: false });   
            input.value = "";
            render();
        } else {
            showMsg(r.data.error || "Could not add the task.");
        }
    });
});


function toggleTask(t, box) {
    var wanted = box.checked;
    box.disabled = true;
    api("/todos/" + t.id + "/done", "PATCH", { is_done: wanted }).then(function (r) {
        if (r.ok) {
            clearMsg();
            t.is_done = wanted;
        } else {
            showMsg(r.data.error || "Could not update the task.");
            box.checked = !wanted;
        }
        render();
    });
}


function deleteTask(t, button) {
    if (!confirm("Are you sure you want to delete this task?")) return;
    button.disabled = true;
    api("/todos/" + t.id, "DELETE").then(function (r) {
        if (r.ok) {
            clearMsg();
            tasks = tasks.filter(function (x) { return x.id !== t.id; });
        } else {
            showMsg(r.data.error || "Could not delete the task.");
            button.disabled = false;
        }
        render();
    });
}


function startEdit(t) { clearMsg(); editingId = t.id; render(); }
function cancelEdit() { clearMsg(); editingId = null; render(); }

function saveEdit(t, input) {
    var title = input.value.trim();
    if (title === "") { showMsg("Title is required"); return; }
    if (title.length > 200) { showMsg("Title is too long (200 characters at most)"); return; }

    api("/todos/" + t.id, "PATCH", { title: title }).then(function (r) {
        if (r.ok) {
            clearMsg();
            t.title = r.data.title;
            editingId = null;
            render();
        } else {
            showMsg(r.data.error || "Could not update the task.");
        }
    });
}


document.querySelectorAll(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () { filter = tab.dataset.filter; render(); });
});

render();
