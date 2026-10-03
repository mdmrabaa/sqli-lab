"""
SQLi Training Lab — INTENTIONALLY VULNERABLE
----------------------------------------------
This app is built for a controlled cybersecurity training programme
(Week 1 — SQL Injection). It deliberately builds SQL queries with
raw string concatenation so students can observe and exploit classic
SQL injection flaws, then compare against the hardened version in
/secure_version.

DO NOT use real data, real credentials, or deploy this anywhere that
isn't clearly marked as a training lab. Do not point automated
scanners/attack tools at third-party infrastructure without permission.
"""

import os
import sqlite3
from flask import Flask, request, render_template, g

DB_PATH = os.path.join(os.path.dirname(__file__), "lab.db")

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS products;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );
        """
    )
    db.executemany(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        [
            ("admin", "SuperSecret123!", "admin"),
            ("alice", "password1", "user"),
            ("bob", "letmein", "user"),
        ],
    )
    db.executemany(
        "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
        [
            ("Wireless Mouse", "electronics", 19.99),
            ("Mechanical Keyboard", "electronics", 59.99),
            ("Yoga Mat", "fitness", 24.50),
            ("Water Bottle", "fitness", 12.00),
            ("Notebook", "office", 3.50),
            ("Desk Lamp", "office", 22.00),
        ],
    )
    db.commit()
    db.close()


@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------
# VULNERABLE ENDPOINT 1: Login — classic auth-bypass SQL injection
#   Try username:  admin' --
#   Try username:  ' OR '1'='1
# ---------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    result = None
    query_shown = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # VULNERABLE: raw string concatenation, no parameterization
        query = (
            f"SELECT * FROM users WHERE username = '{username}' "
            f"AND password = '{password}'"
        )
        query_shown = query
        db = get_db()
        try:
            cur = db.execute(query)
            row = cur.fetchone()
            if row:
                result = f"Login success — welcome {row['username']} (role: {row['role']})"
            else:
                result = "Login failed — invalid credentials"
        except sqlite3.Error as e:
            result = f"DB error: {e}"

    return render_template("login.html", result=result, query_shown=query_shown)


# ---------------------------------------------------------------------
# VULNERABLE ENDPOINT 2: Product search — UNION-based data extraction
#   Try: ' UNION SELECT id, username, password, role FROM users --
# ---------------------------------------------------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    rows = []
    query_shown = None
    error = None

    if q:
        # VULNERABLE: raw string concatenation, no parameterization
        query = f"SELECT name, category, price FROM products WHERE category = '{q}'"
        query_shown = query
        db = get_db()
        try:
            cur = db.execute(query)
            rows = cur.fetchall()
        except sqlite3.Error as e:
            error = str(e)

    return render_template("search.html", rows=rows, q=q, query_shown=query_shown, error=error)


@app.route("/reset")
def reset():
    # Convenience endpoint for the lab: re-seed the DB to a clean state
    init_db()
    return "Database reset to initial seed data. <a href='/'>Back</a>"


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # When run under gunicorn (Render), make sure DB exists at import time
    if not os.path.exists(DB_PATH):
        init_db()
