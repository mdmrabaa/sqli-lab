# FCS — SQL Injection Training Lab

A modern Flask app built for the FCS cybersecurity training programme
(Week 1 — SQL Injection). It ships in two versions:

- **`app/`** — intentionally vulnerable (raw string-concatenated SQL)
- **`secure_version/`** — hardened (parameterized queries + allow-list)

Both are the same two endpoints (`/login`, `/search`) so you can run the
exact same payloads before and after hardening and see the difference.

> **Use only in a supervised training context.** No real user data,
> no reused passwords, and don't point scanners at it from outside the
> course. Treat the deployed URL as a shared lab resource, not a
> production app.

## 1. Push to GitHub

```bash
cd sqli-lab
git init
git add .
git commit -m "FCS SQLi training lab (vulnerable + hardened versions)"
git branch -M main
git remote add origin https://github.com/<your-username>/sqli-lab.git
git push -u origin main
```

## 2. Deploy online with Render (free tier)

1. Go to https://render.com, sign in, and click **New -> Web Service**.
2. Connect the GitHub repo you just pushed.
3. Render will detect `render.yaml` and pre-fill the settings
   (root dir `app`, build `pip install -r requirements.txt`, start
   `gunicorn app:app`). If it doesn't auto-detect, set those manually.
4. Deploy. You'll get a URL like `https://fcs-sqli-lab.onrender.com`.
5. Visit `/reset` once after the first deploy to seed the database
   (it also auto-seeds on first run).

**Note on Render's free tier:** the instance spins down after periods
of inactivity and the filesystem is ephemeral — if it restarts, SQLite
resets to whatever `init_db()` seeds, which is fine for a lab (use
`/reset` any time you want a clean slate mid-session).

### Deploying the hardened version later

When you're ready for the "defense" phase, repeat the same Render
steps but point `rootDir` at `secure_version` instead of `app` — either
as a second Render service (so both are live side by side for
comparison) or by swapping the root dir on the same service and
redeploying.

## 3. Exploiting the vulnerable version

### Endpoint 1 — Login bypass (`/login`)
The query is built as:
```sql
SELECT * FROM users WHERE username = '<input>' AND password = '<input>'
```
Try as **username**, leaving password blank:
```
admin' --
```
or:
```
' OR '1'='1
```
Both return a successful login without knowing the real password.

### Endpoint 2 — UNION-based extraction (`/search?q=...`)
The query is:
```sql
SELECT id, name, category FROM products WHERE category = '<input>'
```
Try as the search box value:
```
' UNION SELECT id, username, password FROM users --
```
This dumps the `users` table's id/username/password into the
product-search results table (3 columns match, so the UNION works
without guessing column count — point that out as a teaching note:
in a real test, students would typically have to discover the column
count first, e.g. with `' ORDER BY 4 --` to find where it breaks).

## 4. Retesting after hardening

`secure_version/app.py` makes the same two queries safe:
- `/login` uses `?` placeholders instead of string formatting, so
  `admin' --` is treated as a literal username that doesn't exist.
- `/search` validates `q` against an allow-list (`electronics`,
  `home`) *and* uses placeholders, so the UNION payload
  is rejected outright with "Unknown category."

Run the exact same payloads from Section 3 against the hardened
deployment and confirm both fail — that's the defense deliverable.

## 5. Live Demo: Switch Between Vulnerable and Hardened Mode

The `app/` version includes a built-in toggle so you can switch
between vulnerable and hardened mode **without changing code** —
perfect for live classroom demos.

### How to switch

**Vulnerable mode (default):**
```bash
cd app
python app.py
```

**Hardened mode:**
```bash
cd app
set SECURE_MODE=1
python app.py
```

**Or with a single command (Windows PowerShell):**
```powershell
cd app
$env:SECURE_MODE="1"; python app.py
```

**Or on Linux/Mac:**
```bash
cd app
SECURE_MODE=1 python app.py
```

### Demo flow for students

1. Start in **vulnerable mode** — run the payloads, show they work
2. Stop the server
3. Start in **hardened mode** (`SECURE_MODE=1`) — run the **same payloads**
4. Show students the payloads now fail
5. Open the code and highlight the one-line difference:
   ```python
   # Vulnerable
   query = f"SELECT * FROM users WHERE username = '{username}'"
   db.execute(query)

   # Hardened
   db.execute("SELECT * FROM users WHERE username = ?", (username,))
   ```

## Admin Panel

Both versions include a session-based admin panel at `/admin`:

- **Login** with `admin / admin123` to access it
- **Add users** — create new accounts with a chosen role (user/admin)
- **Delete users** — remove accounts from the panel
- **Add products** — add new products with name and category
- **Delete products** — remove products from the catalog
- **View products** — see the current product catalog
- **Stats dashboard** — see total users, products, and admin count
- **Reset database** — re-seed the database to its original state

The admin panel is protected by a server-side `admin_required` decorator that
checks `session["role"] == "admin"`. It is intentionally **not** injectable —
it's the feature you build and defend, not the exercise.

## Search requires login

The `/search` endpoint now requires authentication. If you try to
search without logging in, you'll be redirected to the login page.
This teaches students that access control is a separate layer from
input validation — both are needed for a secure app.

## 6. How to Protect Against SQL Injection

SQL injection happens when user input is concatenated directly into
SQL queries. Here's how to prevent it:

### Rule #1: Use Parameterized Queries (Prepared Statements)

**Vulnerable (string concatenation):**
```python
query = f"SELECT * FROM users WHERE username = '{username}'"
db.execute(query)
```

**Safe (parameterized):**
```python
db.execute("SELECT * FROM users WHERE username = ?", (username,))
```

The database driver treats `?` placeholders as **data only** —
never as SQL syntax. Even if `username` contains `' OR '1'='1`,
it's just a string value, not executable SQL.

### Rule #2: Use an ORM (Object-Relational Mapper)

ORMs like SQLAlchemy automatically parameterize queries:
```python
# SQLAlchemy example
user = session.query(User).filter_by(username=username).first()
```

### Rule #3: Input Validation / Allow-lists

If input must match a fixed set of values, validate against an
allow-list before using it:
```python
ALLOWED_CATEGORIES = {"electronics", "home"}

if q not in ALLOWED_CATEGORIES:
    return "Unknown category", 400
```

### Rule #4: Least Privilege Database Accounts

Don't connect to your database as `root` or a superuser. Create
a dedicated account with only the permissions it needs:
```sql
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT ON lab_db.* TO 'app_user'@'localhost';
```

### Rule #5: Escape Output (Defense in Depth)

If you must display user input in HTML, escape it to prevent
XSS (Cross-Site Scripting):
```python
from markupsafe import escape
return f"<p>{escape(user_input)}</p>"
```

### Rule #6: Use Web Application Firewalls (WAF)

A WAF can detect and block common injection patterns before they
reach your application. This is a safety net, not a replacement
for secure coding.

### Rule #7: Regular Security Testing

- Run automated scanners (e.g., OWASP ZAP, sqlmap) against your app
- Perform manual penetration testing
- Review code for string concatenation in SQL queries

### Quick Reference: Vulnerable vs Safe

| Vulnerable | Safe |
|---|---|
| `f"SELECT * FROM t WHERE col = '{val}'"` | `db.execute("SELECT * FROM t WHERE col = ?", (val,))` |
| `f"INSERT INTO t VALUES ('{a}', '{b}')"` | `db.execute("INSERT INTO t VALUES (?, ?)", (a, b))` |
| `f"DELETE FROM t WHERE id = {id}"` | `db.execute("DELETE FROM t WHERE id = ?", (id,))` |

## Local run (optional, if you ever want to sanity-check before pushing)

```bash
cd app   # or secure_version
pip install -r requirements.txt
python app.py
# visit http://localhost:5000
```

## Files

```
sqli-lab/
├── render.yaml              # Render deploy config (points at app/)
├── app/                     # VULNERABLE version (with SECURE_MODE toggle)
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
│       ├── base.html        # Shared layout (nav, banner, styles)
│       ├── index.html
│       ├── login.html
│       ├── search.html
│       └── admin.html       # Admin panel
├── secure_version/           # HARDENED version
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── login.html
│       ├── search.html
│       └── admin.html
└── README.md
```
