import os
import json
from io import BytesIO
from functools import wraps

from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()  # must run BEFORE any of these imports below

from ocr_service import extract_attendance_data, DEFAULT_CONFIG
from pdf_service import generate_attendance_pdf, extract_data_from_pdf
from excel_service import generate_attendance_excel
import database
import auth_service
import study_ai_service
import email_service
import secrets as secrets_module
import hmac
import hashlib
import payment_service
from PIL import Image
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["null", "http://127.0.0.1:5500", "http://localhost:5500"]}})
limiter = Limiter(get_remote_address, app=app, default_limits=[])

print("Flask is using this folder:", os.getcwd())
print("Full database path:", os.path.abspath("snapattend.db"))
database.init_db()
auth_service.init_auth_tables()

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE_MB = 5

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_MB * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_config(raw_config_json):
    if not raw_config_json:
        return DEFAULT_CONFIG
    try:
        config = json.loads(raw_config_json)
    except json.JSONDecodeError:
        return DEFAULT_CONFIG
    if not isinstance(config, dict) or "columns" not in config or "numWeeks" not in config:
        return DEFAULT_CONFIG
    return config


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        user_id = auth_service.get_user_id_from_token(token)
        if not user_id:
            return jsonify({"error": "You must be logged in to do that."}), 401
        g.user_id = user_id
        return f(*args, **kwargs)
    return wrapper

def require_premium(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        plan = auth_service.get_effective_plan(g.user_id)
        if plan != "premium":
            return jsonify({"error": "This feature requires SnapAttend Premium.", "requires_upgrade": True}), 403
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return "SnapAttend backend is running!"


# ---------- AUTH ----------

@app.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")
    plan = payload.get("plan", "basic")
    email = payload.get("email", "")

    user_id, error = auth_service.create_user(username, password, plan, email)
    if error:
        return jsonify({"error": error}), 400

    code = auth_service.create_email_verification_code(user_id)
    if email:
        email_service.send_notification(email, "Verify your SnapAttend email", f"Your verification code is: {code}")

    token = auth_service.create_token(user_id)
    return jsonify({"token": token, "username": username.strip(), "plan": plan}), 201

@app.route("/verify-email", methods=["POST"])
@require_auth
def verify_email():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code", "").strip()
    if auth_service.verify_email_code(g.user_id, code):
        return jsonify({"message": "Email verified!"}), 200
    return jsonify({"error": "Invalid or expired code."}), 400

@app.route("/notification-settings", methods=["GET"])
@require_auth
def get_notifications():
    return jsonify(database.get_notification_settings(g.user_id)), 200


@app.route("/notification-settings", methods=["POST"])
@require_auth
def update_notifications():
    payload = request.get_json(silent=True) or {}
    database.set_notification_settings(
        g.user_id,
        payload.get("attendance_confirmed_emails", False),
        payload.get("study_reminder_emails", False),
    )
    return jsonify({"message": "Notification settings updated."}), 200

@app.route("/study-assistant/analyze", methods=["POST"])
@require_auth
@require_premium
def study_assistant_analyze():
    payload = request.get_json(silent=True) or {}
    course_name = (payload.get("course_name") or "").strip()
    topic_title = (payload.get("topic_title") or "").strip()
    topic_description = payload.get("topic_description", "")

    if not course_name or not topic_title:
        return jsonify({"error": "Course name and topic title are required."}), 400

    result = study_ai_service.analyze_topic(course_name, topic_title, topic_description)
    return jsonify(result), (200 if result["success"] else 500)


@app.route("/study-assistant/followup", methods=["POST"])
@require_auth
@require_premium
def study_assistant_followup():
    payload = request.get_json(silent=True) or {}
    course_name = (payload.get("course_name") or "").strip()
    topic_title = (payload.get("topic_title") or "").strip()
    previous_explanation = payload.get("previous_explanation", "")
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    result = study_ai_service.ask_followup(course_name, topic_title, previous_explanation, question)
    return jsonify(result), (200 if result["success"] else 500)

@app.route("/me", methods=["GET"])
@require_auth
def me():
    plan = auth_service.get_effective_plan(g.user_id)
    sub_info = auth_service.get_subscription_info(g.user_id)
    return jsonify({
        "username": auth_service.get_username(g.user_id),
        "plan": plan,
        "trial_end": sub_info.get("trial_end"),
        "subscription_status": sub_info.get("subscription_status"),
        "subscription_end": sub_info.get("subscription_end"),
    }), 200


@app.route("/upgrade", methods=["POST"])
@require_auth
def upgrade():
    # Placeholder for future payment integration - instantly grants Premium for now.
    auth_service.set_user_plan(g.user_id, "premium")
    return jsonify({"message": "Upgraded to Premium!", "plan": "premium"}), 200


@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")

    user_id, error = auth_service.verify_login(username, password)
    if error:
        return jsonify({"error": error}), 401

    if not auth_service.is_email_verified(user_id):
        return jsonify({"error": "Please verify your email first.", "needs_verification": True, "user_id": user_id}), 403

    token = auth_service.create_token(user_id)
    plan = auth_service.get_user_plan(user_id)
    return jsonify({"token": token, "username": auth_service.get_username(user_id), "plan": plan}), 200

@app.route("/resend-verification", methods=["POST"])
def resend_verification():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    user_id, error = auth_service.verify_login(username, password)
    if error:
        return jsonify({"error": error}), 401

    email = auth_service.get_user_email(user_id)
    if not email:
        return jsonify({"error": "No email on file for this account."}), 400

    code = auth_service.create_email_verification_code(user_id)
    email_service.send_notification(email, "Verify your SnapAttend email", f"Your verification code is: {code}")

    token = auth_service.create_token(user_id)
    return jsonify({"message": "Verification code sent.", "token": token}), 200


@app.route("/logout", methods=["POST"])
@require_auth
def logout():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    auth_service.delete_token(token)
    return jsonify({"message": "Logged out."}), 200

@app.route("/subscribe/initialize", methods=["POST"])
@require_auth
def subscribe_initialize():
    sub_info = auth_service.get_subscription_info(g.user_id)
    price = payment_service.get_price_for_user(sub_info.get("first_payment_done"))
    email = auth_service.get_user_email(g.user_id) or f"user{g.user_id}@snapattend.local"
    reference = f"snapattend_{g.user_id}_{secrets_module.token_hex(8)}"

    url, error = payment_service.initialize_transaction(email, price, reference)
    if error:
        return jsonify({"error": error}), 400
        database.save_pending_payment(reference, g.user_id, price)

    return jsonify({"authorization_url": url, "reference": reference, "amount": price}), 200


@app.route("/subscribe/verify/<reference>", methods=["GET"])
@require_auth
def subscribe_verify(reference):
    expected_amount = database.get_expected_amount(reference)
    if expected_amount is None:
        return jsonify({"error": "Unknown payment reference."}), 400

    success, amount_paid = payment_service.verify_transaction(reference)
    if not success:
        return jsonify({"error": "Payment not confirmed yet."}), 400

    if amount_paid is None or int(amount_paid) != int(expected_amount):
        return jsonify({"error": "Payment amount does not match. Please contact support."}), 400

    auth_service.record_successful_payment(g.user_id, reference)
    return jsonify({"message": "Payment confirmed! Premium activated.", "plan": "premium"}), 200


@app.route("/public-config", methods=["GET"])
def public_config():
    return jsonify({"whatsapp_number": os.environ.get("WHATSAPP_NUMBER", "")}), 200


# ---------- ATTENDANCE UPLOAD / AI EXTRACTION ----------

@app.route("/upload", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file found in the request."}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only JPG, JPEG, and PNG are allowed."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        with Image.open(filepath) as img:
            img.verify()
    except Exception:
        os.remove(filepath)
        return jsonify({"error": "This file is not a valid image."}), 400

    config = parse_config(request.form.get("config"))
    extraction_result = extract_attendance_data(filepath, config)

    try:
        os.remove(filepath)
    except OSError:
        pass  # not critical if cleanup fails

    return jsonify({
        "message": f"'{filename}' uploaded successfully!",
        "extraction": extraction_result,
        "config": config,
    }), 200
@app.route("/request-password-reset", methods=["POST"])
@limiter.limit("5 per minute")
def request_password_reset():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip()
    user = auth_service.get_user_by_email(email)
    if user:
        code = auth_service.create_reset_code(user["id"])
        email_service.send_reset_code(email, code)
    # Always return success, even if email not found - avoids leaking who has accounts
    return jsonify({"message": "If that email exists, a reset code has been sent."}), 200


@app.route("/reset-password", methods=["POST"])
@limiter.limit("5 per minute")
def reset_password_route():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip()
    code = payload.get("code", "").strip()
    new_password = payload.get("new_password", "")

    user_id, error = auth_service.verify_reset_code(email, code)
    if error:
        return jsonify({"error": error}), 400

    success, error = auth_service.reset_password(user_id, new_password)
    if not success:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Password reset successfully. You can now log in."}), 200


# ---------- CONFIRM / SAVE TO DATABASE ----------

@app.route("/confirm-attendance", methods=["POST"])
@require_auth
def confirm_attendance():
    payload = request.get_json(silent=True)
    if not payload or "students" not in payload:
        return jsonify({"error": "No student data received."}), 400

    students = payload["students"]
    config = payload.get("config") or DEFAULT_CONFIG
    num_weeks = config.get("numWeeks", 14)

    if not isinstance(students, list) or len(students) == 0:
        return jsonify({"error": "No students to confirm."}), 400

    valid_statuses = {"Present", "Absent", "Late", "Excused", ""}

    for index, student in enumerate(students):
        row_number = index + 1
        weekly_attendance = student.get("weekly_attendance") or []
        if len(weekly_attendance) != num_weeks:
            return jsonify({"error": f"Row {row_number}: expected {num_weeks} weeks of attendance."}), 400
        for week_entry in weekly_attendance:
            status = week_entry.get("status")
            if status not in valid_statuses:
                return jsonify({
                    "error": f"Row {row_number}, Week {week_entry.get('week')}: '{status}' is not a valid status."
                }), 400

    course_name = (payload.get("course_name") or "General").strip() or "General"

    try:
        session_id = database.save_attendance_session(course_name, config, students, g.user_id)
    except Exception as e:
        return jsonify({"error": f"Attendance was valid but could not be saved: {e}"}), 500

    settings = database.get_notification_settings(g.user_id)
    if settings["attendance_confirmed_emails"]:
        user_email = auth_service.get_user_email(g.user_id)
        if user_email:
            email_service.send_notification(
                user_email,
                "Attendance Confirmed",
                f"Your attendance for '{course_name}' has been recorded ({len(students)} student(s))."
            )

    return jsonify({
        "message": f"Attendance confirmed and saved for {len(students)} student(s) under '{course_name}'.",
        "session_id": session_id,
    }), 200


# ---------- PDF EXPORT / IMPORT ----------

@app.route("/export-pdf", methods=["POST"])
@require_auth
def export_pdf():
    payload = request.get_json(silent=True)
    if not payload or "students" not in payload:
        return jsonify({"error": "No student data received."}), 400

    students = payload["students"]
    config = payload.get("config") or DEFAULT_CONFIG
    num_weeks = config.get("numWeeks", 14)

    if not isinstance(students, list) or len(students) == 0:
        return jsonify({"error": "No students to export."}), 400

    valid_statuses = {"Present", "Absent", "Late", "Excused", ""}
    for index, student in enumerate(students):
        row_number = index + 1
        weekly_attendance = student.get("weekly_attendance") or []
        if len(weekly_attendance) != num_weeks:
            return jsonify({"error": f"Row {row_number}: expected {num_weeks} weeks of attendance."}), 400
        for week_entry in weekly_attendance:
            if week_entry.get("status") not in valid_statuses:
                return jsonify({"error": f"Row {row_number}, Week {week_entry.get('week')}: invalid status."}), 400

    pdf_bytes = generate_attendance_pdf(students, config)

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="attendance_register.pdf",
    )


@app.route("/import-pdf", methods=["POST"])
@require_auth
def import_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No PDF file found in the request."}), 400

    file = request.files["pdf"]
    if file.filename == "" or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a valid PDF file."}), 400

    pdf_bytes = file.read()
    result = extract_data_from_pdf(pdf_bytes)

    return jsonify(result), (200 if result["success"] else 400)


# ---------- EXCEL EXPORT ----------

@app.route("/export-excel", methods=["POST"])
@require_auth
def export_excel():
    payload = request.get_json(silent=True)
    if not payload or "students" not in payload:
        return jsonify({"error": "No student data received."}), 400

    students = payload["students"]
    config = payload.get("config") or DEFAULT_CONFIG
    num_weeks = config.get("numWeeks", 14)

    if not isinstance(students, list) or len(students) == 0:
        return jsonify({"error": "No students to export."}), 400

    valid_statuses = {"Present", "Absent", "Late", "Excused", ""}
    for index, student in enumerate(students):
        row_number = index + 1
        weekly_attendance = student.get("weekly_attendance") or []
        if len(weekly_attendance) != num_weeks:
            return jsonify({"error": f"Row {row_number}: expected {num_weeks} weeks of attendance."}), 400
        for week_entry in weekly_attendance:
            if week_entry.get("status") not in valid_statuses:
                return jsonify({"error": f"Row {row_number}, Week {week_entry.get('week')}: invalid status."}), 400

    try:
        excel_bytes = generate_attendance_excel(students, config)
    except Exception as e:
        app.logger.error(f"Excel generation failed: {e}")
        return jsonify({"error": "Could not generate the Excel file. Please try again."}), 500

    return send_file(
        BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="attendance_register.xlsx",
    )


# ---------- ATTENDANCE HISTORY ----------

@app.route("/attendance-history", methods=["GET"])
@require_auth
def attendance_history():
    page = request.args.get("page", 1, type=int)
    sessions = database.get_all_sessions(g.user_id, page=page)
    return jsonify({"sessions": sessions, "page": page}), 200


@app.route("/attendance-history/<int:session_id>", methods=["GET"])
@require_auth
def attendance_history_detail(session_id):
    details = database.get_session_details(session_id, g.user_id)
    if not details:
        return jsonify({"error": "Session not found."}), 404
    return jsonify(details), 200

@app.route("/courses", methods=["GET"])
@require_auth
@require_premium
def list_courses():
    return jsonify({"courses": database.get_course_outlines(g.user_id)}), 200


@app.route("/courses", methods=["POST"])
@require_auth
@require_premium
def create_course():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("course_name") or "").strip()
    code = (payload.get("course_code") or "").strip()
    if not name:
        return jsonify({"error": "Course name is required."}), 400
    course_id = database.add_course_outline(g.user_id, name, code)
    return jsonify({"id": course_id}), 201

@app.route("/attendance-by-course", methods=["GET"])
@require_auth
def attendance_by_course():
    data = database.get_attendance_percentage_by_course(g.user_id)
    return jsonify({"courses": data}), 200

@app.route("/study-progress", methods=["GET"])
@require_auth
@require_premium
def study_progress():
    progress = database.get_study_progress(g.user_id)
    return jsonify({"progress": progress}), 200


@app.route("/courses/<int:course_id>", methods=["PUT"])
@require_auth
@require_premium
def edit_course(course_id):
    payload = request.get_json(silent=True) or {}
    name = (payload.get("course_name") or "").strip()
    code = (payload.get("course_code") or "").strip()
    if not database.update_course_outline(course_id, g.user_id, name, code):
        return jsonify({"error": "Course not found."}), 404
    return jsonify({"message": "Updated."}), 200


@app.route("/courses/<int:course_id>", methods=["DELETE"])
@require_auth
@require_premium
def remove_course(course_id):
    if not database.delete_course_outline(course_id, g.user_id):
        return jsonify({"error": "Course not found."}), 404
    return jsonify({"message": "Deleted."}), 200


@app.route("/courses/<int:course_id>/topics", methods=["GET"])
@require_auth
@require_premium
def list_topics(course_id):
    return jsonify({"topics": database.get_topics(course_id, g.user_id)}), 200


@app.route("/courses/<int:course_id>/topics", methods=["POST"])
@require_auth
@require_premium
def create_topic(course_id):
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Topic title is required."}), 400
    topic_id = database.add_topic(
        course_id, g.user_id,
        payload.get("week_label", ""), title,
        payload.get("description", ""), payload.get("materials", ""),
    )
    if topic_id is None:
        return jsonify({"error": "Course not found."}), 404
    return jsonify({"id": topic_id}), 201


@app.route("/topics/<int:topic_id>", methods=["PUT"])
@require_auth
@require_premium
def edit_topic(topic_id):
    payload = request.get_json(silent=True) or {}
    ok = database.update_topic(
        topic_id, g.user_id,
        payload.get("week_label", ""), payload.get("title", ""),
        payload.get("description", ""), payload.get("materials", ""),
        payload.get("studied", False),
    )
    if not ok:
        return jsonify({"error": "Topic not found."}), 404
    return jsonify({"message": "Updated."}), 200


@app.route("/topics/<int:topic_id>", methods=["DELETE"])
@require_auth
@require_premium
def remove_topic(topic_id):
    if not database.delete_topic(topic_id, g.user_id):
        return jsonify({"error": "Topic not found."}), 404
    return jsonify({"message": "Deleted."}), 200


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": f"File is too large. Max allowed size is {MAX_FILE_SIZE_MB}MB."}), 413



@app.errorhandler(500)
def handle_internal_error(e):
    app.logger.error(f"Internal error: {e}")
    return jsonify({"error": "Something went wrong on our end. Please try again."}), 500

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode)