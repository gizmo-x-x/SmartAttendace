"""
auth_service.py

Handles account creation, login verification, and session tokens.
Passwords are NEVER stored in plain text - only a secure one-way hash.
"""

import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "snapattend.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT,
            password_hash TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'basic',
            trial_end TEXT,
            subscription_status TEXT NOT NULL DEFAULT 'none',
            subscription_end TEXT,
            first_payment_done INTEGER NOT NULL DEFAULT 0,
            email_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()


def create_user(username, password, plan="basic", email=""):
    """Creates a new account. Returns (user_id, error_message).
    error_message is None on success."""
    username = username.strip()
    if len(username) < 3:
        return None, "Username must be at least 3 characters."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    if password.isalpha() or password.isdigit():
        return None, "Password must contain both letters and numbers."
    if plan not in ("basic", "premium"):
        plan = "basic"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return None, "That username is already taken."

    password_hash = generate_password_hash(password)
    from datetime import datetime, timedelta
    trial_end = (datetime.now() + timedelta(days=10)).isoformat()

    cursor.execute(
        "INSERT INTO users (username, email, password_hash, plan, trial_end) VALUES (?, ?, ?, ?, ?)",
        (username, email.strip(), password_hash, plan, trial_end),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id, None


def get_user_email(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["email"] if row and row["email"] else None


def verify_login(username, password):
    """Checks credentials. Returns (user_id, error_message)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()

    if not row or not check_password_hash(row["password_hash"], password):
        return None, "Incorrect username or password."

    return row["id"], None

def create_email_verification_code(user_id):
    code = f"{random.randint(0, 999999):06d}"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO password_reset_codes (user_id, code, expires_at)
        VALUES (?, ?, ?)
    """, (user_id, "VERIFY-" + code, (datetime.now() + timedelta(hours=24)).isoformat()))
    conn.commit()
    conn.close()
    return code


def verify_email_code(user_id, code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, expires_at FROM password_reset_codes
        WHERE user_id = ? AND code = ? AND used = 0 ORDER BY id DESC LIMIT 1
    """, (user_id, "VERIFY-" + code))
    row = cursor.fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < datetime.now():
        conn.close()
        return False
    cursor.execute("UPDATE password_reset_codes SET used = 1 WHERE id = ?", (row["id"],))
    cursor.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True


def is_email_verified(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email_verified FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row["email_verified"]) if row else False


def create_token(user_id):
    token = secrets.token_hex(32)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO auth_tokens (token, user_id) VALUES (?, ?)", (token, user_id))
    conn.commit()
    conn.close()
    return token


def get_user_id_from_token(token):
    if not token:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, created_at FROM auth_tokens WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None

    created = datetime.fromisoformat(row["created_at"])
    if datetime.now() - created > timedelta(days=7):
        delete_token(token)
        return None

    return row["user_id"]


def get_username(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["username"] if row else None


def get_user_plan(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT plan FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["plan"] if row else "basic"


def set_user_plan(user_id, plan):
    if plan not in ("basic", "premium"):
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, user_id))
    conn.commit()
    conn.close()
    return True


def delete_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()

import random
from datetime import datetime, timedelta


def get_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE email = ?", (email.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_reset_code(user_id):
    code = f"{random.randint(0, 999999):06d}"
    expires_at = (datetime.now() + timedelta(minutes=15)).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO password_reset_codes (user_id, code, expires_at) VALUES (?, ?, ?)",
        (user_id, code, expires_at),
    )
    conn.commit()
    conn.close()
    return code


def verify_reset_code(email, code):
    user = get_user_by_email(email)
    if not user:
        return None, "No account found with that email."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, expires_at, attempts FROM password_reset_codes
        WHERE user_id = ? AND used = 0
        ORDER BY id DESC LIMIT 1
    """, (user["id"],))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None, "Invalid or already-used code."

    if row["attempts"] >= 5:
        conn.close()
        return None, "Too many incorrect attempts. Please request a new code."

    if datetime.fromisoformat(row["expires_at"]) < datetime.now():
        conn.close()
        return None, "This code has expired. Please request a new one."

    cursor.execute("SELECT code FROM password_reset_codes WHERE id = ?", (row["id"],))
    stored_code = cursor.fetchone()["code"]

    if stored_code != code:
        cursor.execute("UPDATE password_reset_codes SET attempts = attempts + 1 WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return None, "Incorrect code."

    cursor.execute("UPDATE password_reset_codes SET used = 1 WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return user["id"], None


def reset_password(user_id, new_password):
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    if new_password.isalpha() or new_password.isdigit():
        return False, "Password must contain both letters and numbers."
    password_hash = generate_password_hash(new_password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()
    return True, None
def get_effective_plan(user_id):
    """Checks trial/subscription expiry, auto-downgrades if needed, returns the
    real current plan. This is the ONLY trusted source of plan status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT trial_end, subscription_status, subscription_end, plan FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "basic"

    now = datetime.now()
    effective = "basic"

    if row["trial_end"] and now <= datetime.fromisoformat(row["trial_end"]):
        effective = "premium"
    elif row["subscription_status"] == "active" and row["subscription_end"] and now <= datetime.fromisoformat(row["subscription_end"]):
        effective = "premium"

    if effective != row["plan"]:
        cursor.execute("UPDATE users SET plan = ? WHERE id = ?", (effective, user_id))
        conn.commit()

    conn.close()
    return effective


def get_subscription_info(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT trial_end, subscription_status, subscription_end, first_payment_done FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}


def record_successful_payment(user_id, reference):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_end, first_payment_done FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    now = datetime.now()
    current_end = datetime.fromisoformat(row["subscription_end"]) if row["subscription_end"] else None
    start_from = current_end if (current_end and current_end > now) else now
    new_end = (start_from + timedelta(days=30)).isoformat()

    cursor.execute("""
        UPDATE users SET subscription_status = 'active', subscription_end = ?,
        first_payment_done = 1, plan = 'premium' WHERE id = ?
    """, (new_end, user_id))
    conn.commit()
    conn.close()