
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
import hashlib
import json
from datetime import datetime
from functools import wraps
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "devices.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                device_id TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS blockchain_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                record_hash TEXT NOT NULL
            )
        """)


# ---------------- HELPERS ----------------

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def create_hash(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def add_blockchain_record(device_id, action):
    timestamp = datetime.now().isoformat(timespec="seconds")
    record_data = f"{device_id}|{action}|{timestamp}"
    record_hash = create_hash(record_data)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO blockchain_records
            (device_id, action, timestamp, record_hash)
            VALUES (?, ?, ?, ?)
        """, (device_id, action, timestamp, record_hash))


# ---------------- HOME PAGE ----------------

@app.route("/", endpoint="index")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("register.html")

        password_hash = create_hash(password)

        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO users (username, password, created_at)
                    VALUES (?, ?, ?)
                """, (
                    username,
                    password_hash,
                    datetime.now().isoformat(timespec="seconds")
                ))

            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("That username already exists.", "error")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_hash = create_hash(password)

        with get_db() as conn:
            user = conn.execute("""
                SELECT * FROM users
                WHERE username = ? AND password = ?
            """, (username, password_hash)).fetchone()

        if user:
            session.clear()
            session["username"] = user["username"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    username = session["username"]

    with get_db() as conn:
        devices = conn.execute("""
            SELECT * FROM devices
            WHERE owner = ?
            ORDER BY id DESC
        """, (username,)).fetchall()

        total = conn.execute("""
            SELECT COUNT(*) FROM devices
            WHERE owner = ?
        """, (username,)).fetchone()[0]

        active = conn.execute("""
            SELECT COUNT(*) FROM devices
            WHERE owner = ? AND status = 'Authenticated'
        """, (username,)).fetchone()[0]

        denied = conn.execute("""
            SELECT COUNT(*) FROM blockchain_records
            WHERE action = 'Authentication denied'
        """).fetchone()[0]

        records = conn.execute("""
            SELECT * FROM blockchain_records
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

    return render_template(
        "dashboard.html",
        username=username,
        devices=devices,
        records=records,
        total=total,
        active=active,
        denied=denied
    )

# ---------------- DEVICE AUTHENTICATION PAGE ----------------

@app.route("/authenticate", methods=["GET", "POST"])
@login_required
def authenticate():
    if request.method == "POST":
        device_name = request.form.get("device_name", "").strip()
        device_id = request.form.get("device_id", "").strip()

        if not device_name or not device_id:
            flash("Please enter both device name and device ID.", "error")
            return render_template("authentication.html")

        with get_db() as conn:
            existing_device = conn.execute(
                "SELECT id FROM devices WHERE device_id = ?",
                (device_id,)
            ).fetchone()

        if existing_device:
            add_blockchain_record(device_id, "Authentication denied")
            flash("A device with this ID is already registered.", "error")
            return render_template("authentication.html")

        with get_db() as conn:
            conn.execute("""
                INSERT INTO devices
                (device_name, device_id, owner, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                device_name,
                device_id,
                session["username"],
                "Authenticated",
                datetime.now().isoformat(timespec="seconds")
            ))

        add_blockchain_record(device_id, "Device authenticated")
        flash("Device authenticated and recorded successfully.", "success")
        return redirect(url_for("blockchain"))

    return render_template("authentication.html")


# ---------------- AUTHENTICATION HISTORY ----------------

@app.route("/history")
@login_required
def history():
    with get_db() as conn:
        records = conn.execute("""
            SELECT *
            FROM blockchain_records
            ORDER BY id DESC
        """).fetchall()

    return render_template("history.html", records=records)


# ---------------- BLOCKCHAIN RECORDS ----------------

@app.route("/blockchain")
@login_required
def blockchain():
    with get_db() as conn:
        records = conn.execute("""
            SELECT * FROM blockchain_records
            ORDER BY id DESC
        """).fetchall()

    return render_template("blockchain.html", records=records)


# ---------------- API: BLOCKCHAIN DATA ----------------

@app.route("/api/blockchain")
@login_required
def blockchain_api():
    with get_db() as conn:
        records = conn.execute("""
            SELECT * FROM blockchain_records
            ORDER BY id DESC
        """).fetchall()

    result = [
        {
            "id": record["id"],
            "device_id": record["device_id"],
            "action": record["action"],
            "timestamp": record["timestamp"],
            "hash": record["record_hash"]
        }
        for record in records
    ]

    return app.response_class(
        response=json.dumps(result),
        status=200,
        mimetype="application/json"
    )


# ---------------- ERROR HANDLERS ----------------

@app.errorhandler(404)
def page_not_found(error):
    return "Page not found. Please check the URL.", 404


@app.errorhandler(500)
def internal_server_error(error):
    return (
        "An internal server error occurred. "
        "Check the VS Code terminal for the error details.",
        500
    )


# ---------------- START APPLICATION ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
