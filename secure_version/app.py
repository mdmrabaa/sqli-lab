"""
SQLi Training Lab — HARDENED VERSION
--------------------------------------
Same two endpoints as the vulnerable app, but using parameterized
queries (SQLite placeholders) plus basic input validation. Deploy
this after the SQLi exercise and re-run the same payloads to show
students that they now fail.

Changes vs. the vulnerable version:
  1. All queries use '?' placeholders — user input is never
     concatenated into SQL text.
  2. The /search category is validated against an allow-list.
  3. Error messages no longer leak the underlying DB error or the
     raw query text to the client.
"""

import os
import sqlite3
from flask import Flask, request, render_template, g

DB_PATH = os.path.join(os.path.dirname(__file__), "lab.db")
ALLOWED_CATEGORIES = {"electronics", "fitness", "office"}

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


@app.route("/login", methods=["GET", "POST"])
def login():
    result = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # SAFE: parameterized query, no string concatenation
        db = get_db()
        cur = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        row = cur.fetchone()
        if row:
            result = f"Login success — welcome {row['username']} (role: {row['role']})"
        else:
            result = "Login failed — invalid credentials"

    return render_template("login.html", result=result, query_shown=None)


@app.route("/search")
def search():
    q = request.args.get("q", "")
    rows = []
    error = None

    if q:
        # SAFE: allow-list validation + parameterized query
        if q not in ALLOWED_CATEGORIES:
            error = "Unknown category"
        else:
            db = get_db()
            cur = db.execute(
                "SELECT name, category, price FROM products WHERE category = ?",
                (q,),
            )
            rows = cur.fetchall()

    return render_template("search.html", rows=rows, q=q, query_shown=None, error=error)


@app.route("/reset")
def reset():
    init_db()
    return "Database reset to initial seed data. <a href='/'>Back</a>"


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    if not os.path.exists(DB_PATH):
        init_db()
