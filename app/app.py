import os
import sqlite3
from flask import Flask, request, session, redirect, url_for, render_template, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lab-dev-secret-change-me")

DB_PATH = os.path.join(os.path.dirname(__file__), "lab.db")


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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        );
        """
    )
    db.executemany(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        [
            ("admin", "admin123", "admin"),
            ("alice", "alice123", "user"),
            ("bob", "bob123", "user"),
        ],
    )
    db.executemany(
        "INSERT INTO products (name, category) VALUES (?, ?)",
        [
            ("Laptop", "electronics"),
            ("Headphones", "electronics"),
            ("Desk Lamp", "home"),
            ("Coffee Mug", "home"),
            ("Keyboard", "electronics"),
        ],
    )
    db.commit()
    db.close()


if not os.path.exists(DB_PATH):
    init_db()


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", user=session.get("username"), role=session.get("role"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # VULNERABLE: raw string concatenation, no parameterization.
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        db = get_db()
        try:
            cur = db.execute(query)
            row = cur.fetchone()
        except sqlite3.Error as e:
            return render_template("login.html", error=f"SQL error: {e}")

        if row:
            session["username"] = row["username"]
            session["role"] = row["role"]
            if row["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))
        error = "Invalid credentials"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = []
    error = None
    if q:
        # VULNERABLE: raw string concatenation, no parameterization.
        query = f"SELECT id, name, category FROM products WHERE category = '{q}'"
        db = get_db()
        try:
            results = db.execute(query).fetchall()
        except sqlite3.Error as e:
            error = f"SQL error: {e}"
    return render_template("search.html", q=q, results=results, error=error)


@app.route("/reset")
def reset():
    init_db()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Admin panel — only reachable when logged in with role == 'admin'.
# This part is intentionally NOT injectable: it's the feature you build
# and defend, not the exercise. Auth is checked server-side via session.
# ---------------------------------------------------------------------------

def admin_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    users = db.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    products = db.execute("SELECT id, name, category FROM products ORDER BY id").fetchall()
    return render_template("admin.html", users=users, products=products, admin=session.get("username"))


@app.route("/admin/users/add", methods=["POST"])
@admin_required
def admin_add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "user").strip() or "user"

    if username and password:
        db = get_db()
        # Parameterized on purpose — this is an admin-only internal action,
        # not the vulnerability under test.
        db.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, role),
        )
        db.commit()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
