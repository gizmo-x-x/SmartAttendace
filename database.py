"""
database.py

Handles all SQLite database setup and queries for SnapAttend.
This is the only file that talks to the database directly - every other
file goes through the functions here instead of writing raw SQL itself.
No API keys or secrets are ever stored here - only attendance data.
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "snapattend.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, like a dictionary
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Creates all tables if they don't already exist. Safe to run every
    time the app starts - it won't wipe or duplicate existing data."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id INTEGER PRIMARY KEY,
            attendance_confirmed_emails INTEGER NOT NULL DEFAULT 0,
            study_reminder_emails INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matric_no TEXT NOT NULL UNIQUE,
            fields TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            confirmed_at TEXT NOT NULL,
            config TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES attendance_sessions (id),
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_outlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            course_code TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_payments (
            reference TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expected_amount INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_outline_id INTEGER NOT NULL,
            week_label TEXT,
            title TEXT NOT NULL,
            description TEXT,
            materials TEXT,
            studied INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (course_outline_id) REFERENCES course_outlines (id)
        )
    """)

    conn.commit()
    conn.close()


def get_or_create_course(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM courses WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        course_id = row["id"]
    else:
        cursor.execute("INSERT INTO courses (name) VALUES (?)", (name,))
        conn.commit()
        course_id = cursor.lastrowid
    conn.close()
    return course_id


def get_or_create_student(matric_no, fields_dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE matric_no = ?", (matric_no,))
    row = cursor.fetchone()
    fields_json = json.dumps(fields_dict)
    if row:
        student_id = row["id"]
        # Keep the student's stored details up to date with their latest info
        cursor.execute("UPDATE students SET fields = ? WHERE id = ?", (fields_json, student_id))
        conn.commit()
    else:
        cursor.execute(
            "INSERT INTO students (matric_no, fields) VALUES (?, ?)",
            (matric_no, fields_json),
        )
        conn.commit()
        student_id = cursor.lastrowid
    conn.close()
    return student_id


def save_attendance_session(course_name, config, students, teacher_id):
    """Saves one full confirmed attendance session (a course, a timestamp,
    and every student's weekly records) to the database."""
    course_id = get_or_create_course(course_name)

    conn = get_connection()
    cursor = conn.cursor()
    confirmed_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO attendance_sessions (course_id, teacher_id, confirmed_at, config) VALUES (?, ?, ?, ?)",
        (course_id, teacher_id, confirmed_at, json.dumps(config)),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()

    for student in students:
        matric_no = student.get("matric_no") or f"UNKNOWN-{student.get('student_name', 'row')}"
        student_id = get_or_create_student(matric_no, student)

        conn = get_connection()
        cursor = conn.cursor()
        for week_entry in student.get("weekly_attendance", []):
            cursor.execute(
                "INSERT INTO attendance_records (session_id, student_id, week, status) VALUES (?, ?, ?, ?)",
                (session_id, student_id, week_entry["week"], week_entry["status"]),
            )
        conn.commit()
        conn.close()

    return session_id


def get_all_sessions(teacher_id, page=1, per_page=20):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    cursor.execute("""
        SELECT s.id, s.confirmed_at, c.name AS course_name,
               (SELECT COUNT(DISTINCT student_id) FROM attendance_records WHERE session_id = s.id) AS student_count
        FROM attendance_sessions s
        JOIN courses c ON c.id = s.course_id
        WHERE s.teacher_id = ?
        ORDER BY s.confirmed_at DESC
        LIMIT ? OFFSET ?
    """, (teacher_id, per_page, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_pending_payment(reference, user_id, expected_amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pending_payments (reference, user_id, expected_amount) VALUES (?, ?, ?)",
                   (reference, user_id, expected_amount))
    conn.commit()
    conn.close()


def get_expected_amount(reference):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT expected_amount FROM pending_payments WHERE reference = ?", (reference,))
    row = cursor.fetchone()
    conn.close()
    return row["expected_amount"] if row else None


def get_session_details(session_id, teacher_id):
    """Returns everything needed to redisplay one past session: its config,
    course name, timestamp, and every student's full weekly record."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.confirmed_at, s.config, c.name AS course_name
        FROM attendance_sessions s
        JOIN courses c ON c.id = s.course_id
        WHERE s.id = ? AND s.teacher_id = ?
    """, (session_id, teacher_id))
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        return None

    cursor.execute("""
        SELECT st.matric_no, st.fields, ar.week, ar.status
        FROM attendance_records ar
        JOIN students st ON st.id = ar.student_id
        WHERE ar.session_id = ?
        ORDER BY st.id, ar.week
    """, (session_id,))
    record_rows = cursor.fetchall()
    conn.close()

    students_by_matric = {}
    for row in record_rows:
        matric_no = row["matric_no"]
        if matric_no not in students_by_matric:
            fields = json.loads(row["fields"])
            fields["weekly_attendance"] = []
            students_by_matric[matric_no] = fields
        students_by_matric[matric_no]["weekly_attendance"].append({
            "week": row["week"],
            "status": row["status"],
        })

    return {
        "id": session_row["id"],
        "course_name": session_row["course_name"],
        "confirmed_at": session_row["confirmed_at"],
        "config": json.loads(session_row["config"]),
        "students": list(students_by_matric.values()),
    }
def add_course_outline(user_id, course_name, course_code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO course_outlines (user_id, course_name, course_code) VALUES (?, ?, ?)",
        (user_id, course_name, course_code),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_course_outlines(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM course_outlines WHERE user_id = ? ORDER BY id", (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_course_outline(course_id, user_id, course_name, course_code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE course_outlines SET course_name = ?, course_code = ? WHERE id = ? AND user_id = ?",
        (course_name, course_code, course_id, user_id),
    )
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    return changed > 0


def delete_course_outline(course_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM topics WHERE course_outline_id = ?", (course_id,))
    cursor.execute("DELETE FROM course_outlines WHERE id = ? AND user_id = ?", (course_id, user_id))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    return changed > 0


def _course_belongs_to_user(course_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM course_outlines WHERE id = ? AND user_id = ?", (course_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def add_topic(course_id, user_id, week_label, title, description, materials):
    if not _course_belongs_to_user(course_id, user_id):
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO topics (course_outline_id, week_label, title, description, materials) VALUES (?, ?, ?, ?, ?)",
        (course_id, week_label, title, description, materials),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_study_progress(user_id):
    """Returns per-course topic completion counts for this user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT co.id, co.course_name, co.course_code,
               COUNT(t.id) AS total_topics,
               SUM(CASE WHEN t.studied = 1 THEN 1 ELSE 0 END) AS completed_topics
        FROM course_outlines co
        LEFT JOIN topics t ON t.course_outline_id = co.id
        WHERE co.user_id = ?
        GROUP BY co.id
        ORDER BY co.id
    """, (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_topics(course_id, user_id):
    if not _course_belongs_to_user(course_id, user_id):
        return []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE course_outline_id = ? ORDER BY id", (course_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_topic(topic_id, user_id, week_label, title, description, materials, studied):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE topics SET week_label = ?, title = ?, description = ?, materials = ?, studied = ?
        WHERE id = ? AND course_outline_id IN (SELECT id FROM course_outlines WHERE user_id = ?)
    """, (week_label, title, description, materials, 1 if studied else 0, topic_id, user_id))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    return changed > 0


def delete_topic(topic_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM topics WHERE id = ? AND course_outline_id IN
        (SELECT id FROM course_outlines WHERE user_id = ?)
    """, (topic_id, user_id))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    return changed > 0
def get_attendance_percentage_by_course(user_id):
    """Returns a list of {course_name, percentage} for this user's confirmed attendance."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.name AS course_name, ar.status
        FROM attendance_records ar
        JOIN attendance_sessions s ON s.id = ar.session_id
        JOIN courses c ON c.id = s.course_id
        WHERE s.teacher_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    totals = {}
    for row in rows:
        name = row["course_name"]
        status = row["status"]
        if status == "":
            continue
        if name not in totals:
            totals[name] = {"present": 0, "total": 0}
        totals[name]["total"] += 1
        if status == "Present":
            totals[name]["present"] += 1

    result = []
    for name, counts in totals.items():
        pct = round((counts["present"] / counts["total"]) * 100) if counts["total"] > 0 else 0
        result.append({"course_name": name, "percentage": pct})
    return result
def get_notification_settings(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notification_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"attendance_confirmed_emails": False, "study_reminder_emails": False}
    return {
        "attendance_confirmed_emails": bool(row["attendance_confirmed_emails"]),
        "study_reminder_emails": bool(row["study_reminder_emails"]),
    }


def set_notification_settings(user_id, attendance_confirmed_emails, study_reminder_emails):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notification_settings (user_id, attendance_confirmed_emails, study_reminder_emails)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            attendance_confirmed_emails = excluded.attendance_confirmed_emails,
            study_reminder_emails = excluded.study_reminder_emails
    """, (user_id, int(attendance_confirmed_emails), int(study_reminder_emails)))
    conn.commit()
    conn.close()