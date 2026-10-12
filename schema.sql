DROP DATABASE IF EXISTS registration;
create database if not exists registration;
use registration; 
create table users(
user_id int not null auto_increment , 
email VARCHAR(255) not null,
name VARCHAR(255) not null, 
password_hash VARCHAR(255) not null, 
registration_date timestamp not null default current_timestamp,
primary key(user_id),
unique(email)
);
use registration;
create TABLE todos(
    todo_id    INT          NOT NULL AUTO_INCREMENT,
    user_id    INT          NOT NULL,
    title      VARCHAR(200) NOT NULL,
    is_done    TINYINT(1)   NOT NULL DEFAULT 0,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (todo_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

