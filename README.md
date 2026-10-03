# SQL Injection Training Lab

A tiny Flask app built for Week 1 (SQL Injection) of the cybersecurity
training programme. It ships in two versions:

- **`app/`** — intentionally vulnerable (raw string-concatenated SQL)
- **`secure_version/`** — hardened (parameterized queries + allow-list)

Both are the same two endpoints (`/login`, `/search`) so you can run the
exact same payloads before and after hardening and see the difference.

> ⚠ **Use only in a supervised training context.** No real user data,
> no reused passwords, and don't point scanners at it from outside the
> course. Treat the deployed URL as a shared lab resource, not a
> production app.

## 1. Push to GitHub

```bash
cd sqli-lab
git init
git add .
git commit -m "SQLi training lab (vulnerable + hardened versions)"
git branch -M main
git remote add origin https://github.com/<your-username>/sqli-lab.git
git push -u origin main
```

## 2. Deploy online with Render (free tier)

You asked to test this online rather than locally — Render's free web
service tier works well here since the app is a single lightweight
Flask process with a SQLite file.

1. Go to https://render.com, sign in, and click **New → Web Service**.
2. Connect the GitHub repo you just pushed.
3. Render will detect `render.yaml` and pre-fill the settings
   (root dir `app`, build `pip install -r requirements.txt`, start
   `gunicorn app:app`). If it doesn't auto-detect, set those manually.
4. Deploy. You'll get a URL like `https://sqli-training-lab.onrender.com`.
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
Both return a successful login without knowing the real password. The
page shows the exact query that ran, so students can see why it broke.

### Endpoint 2 — UNION-based extraction (`/search?q=...`)
The query is:
```sql
SELECT name, category, price FROM products WHERE category = '<input>'
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
  `fitness`, `office`) *and* uses placeholders, so the UNION payload
  is rejected outright with "Unknown category."

Run the exact same payloads from Section 3 against the hardened
deployment and confirm both fail — that's the Séance 3 "defense"
deliverable.

## Local run (optional, if you ever want to sanity-check before pushing)

```bash
cd app   # or secure_version
pip install -r requirements.txt
python app.py
# visit http://localhost:5000
```

## Admin Panel

Both versions now include a session-based admin panel at `/admin`:

- **Login** with `admin / admin123` to access it
- **Add users** — create new accounts with a chosen role (user/admin)
- **Delete users** — remove accounts from the panel
- **View products** — see the current product catalog

The admin panel is protected by a server-side `admin_required` decorator that
checks `session["role"] == "admin"`. It is intentionally **not** injectable —
it's the feature you build and defend, not the exercise.

## Files

```
sqli-lab/
├── render.yaml              # Render deploy config (points at app/)
├── app/                     # VULNERABLE version
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
