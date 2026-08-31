import os
import re
import secrets
import sqlite3
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

BRANCHES = ("IT", "CSE", "AIML", "AIDS", "ENTC", "Mechanical", "Civil")
RESOURCE_TYPES = ("Notes", "PYQ", "Assignment", "Lab Manual", "Practical", "Syllabus")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=MAX_FILE_SIZE,
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    DATABASE=str(DATABASE),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def get_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def close_db():
    conn = getattr(__import__("flask").g, "_database", None)
    if conn is not None:
        conn.close()


@app.teardown_appcontext
def teardown_db(_exception=None):
    close_db()


def db():
    from flask import g
    if "_database" not in g:
        g._database = get_db()
    return g._database


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
            abort(400, description="Invalid or missing security token. Please refresh the page and try again.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        if session.get("user_role") != "admin":
            flash("Admin access is required.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def clean_text(value, max_length=120):
    return " ".join((value or "").strip().split())[:max_length]


def valid_pdf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_upload_name(original_name):
    stem = secure_filename(Path(original_name).stem) or "resource"
    return f"{stem[:60]}-{uuid.uuid4().hex}.pdf"


@app.errorhandler(413)
def file_too_large(_error):
    flash("File is too large. Maximum allowed size is 10 MB.", "error")
    return redirect(url_for("upload"))


@app.route("/")
def home():
    row = db().execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN resource_type='Notes' THEN 1 ELSE 0 END) AS notes,
            SUM(CASE WHEN resource_type='PYQ' THEN 1 ELSE 0 END) AS pyqs
        FROM resources
    """).fetchone()
    return render_template("index.html", stats=row)


@app.route("/notes")
@login_required
def notes():
    search = clean_text(request.args.get("search"), 100)
    branch = request.args.get("branch", "")
    semester = request.args.get("semester", "")

    query = "SELECT * FROM resources WHERE resource_type='Notes'"
    params = []

    if search:
        query += " AND (title LIKE ? OR subject LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if branch in BRANCHES:
        query += " AND branch=?"
        params.append(branch)
    else:
        branch = ""
    if semester.isdigit() and 1 <= int(semester) <= 8:
        query += " AND semester=?"
        params.append(int(semester))
    else:
        semester = ""

    query += " ORDER BY id DESC"
    notes = db().execute(query, params).fetchall()
    return render_template("notes.html", notes=notes, search=search, branch=branch, semester=semester)


@app.route("/pyq")
@login_required
def pyq():
    search = clean_text(request.args.get("search"), 100)
    branch = request.args.get("branch", "")
    semester = request.args.get("semester", "")

    query = "SELECT * FROM resources WHERE resource_type='PYQ'"
    params = []

    if search:
        query += " AND (title LIKE ? OR subject LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if branch in BRANCHES:
        query += " AND branch=?"
        params.append(branch)
    else:
        branch = ""
    if semester.isdigit() and 1 <= int(semester) <= 8:
        query += " AND semester=?"
        params.append(int(semester))
    else:
        semester = ""

    query += " ORDER BY id DESC"
    pyqs = db().execute(query, params).fetchall()
    return render_template("pyq.html", pyqs=pyqs, search=search, branch=branch, semester=semester)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = clean_text(request.form.get("full_name"), 80)
        email = clean_text(request.form.get("email"), 120).lower()
        roll_number = clean_text(request.form.get("roll_number"), 40).upper()
        branch = request.form.get("branch", "")
        semester = request.form.get("semester", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#]).{8,72}$"

        if not full_name or len(full_name) < 2:
            flash("Please enter a valid full name.", "error")
        elif not re.fullmatch(email_pattern, email):
            flash("Please enter a valid email address.", "error")
        elif not roll_number or len(roll_number) < 2:
            flash("Please enter a valid registration number.", "error")
        elif branch not in BRANCHES:
            flash("Please select a valid branch.", "error")
        elif not semester.isdigit() or not 1 <= int(semester) <= 8:
            flash("Please select a valid semester.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        elif not re.fullmatch(password_pattern, password):
            flash("Password must be 8–72 characters and include uppercase, lowercase, number and special character.", "error")
        else:
            try:
                db().execute("""
                    INSERT INTO users
                    (full_name, email, roll_number, branch, semester, password_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    full_name, email, roll_number, branch, int(semester),
                    generate_password_hash(password)
                ))
                db().commit()
                flash("Registration successful. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email or registration number is already registered.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        roll_number = clean_text(request.form.get("roll_number"), 40).upper()
        password = request.form.get("password", "")

        user = db().execute("""
            SELECT id, full_name, password_hash, role
            FROM users
            WHERE roll_number=?
        """, (roll_number,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid registration number or password.", "error")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["user_role"] = user["role"] or "student"
        session["csrf_token"] = secrets.token_urlsafe(32)
        flash(f"Welcome, {user['full_name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    connection = db()
    row = connection.execute("""
        SELECT
            COUNT(*) AS total_resources,
            SUM(CASE WHEN resource_type='Notes' THEN 1 ELSE 0 END) AS total_notes,
            SUM(CASE WHEN resource_type='PYQ' THEN 1 ELSE 0 END) AS total_pyqs
        FROM resources
    """).fetchone()
    recent_resources = connection.execute("""
        SELECT id, title, subject, branch, semester, resource_type, filename, uploaded_at
        FROM resources
        ORDER BY id DESC
        LIMIT 6
    """).fetchall()
    return render_template(
        "dashboard.html",
        stats=row,
        recent_resources=recent_resources,
        name=session["user_name"],
    )


@app.route("/profile")
@login_required
def profile():
    connection = db()
    user = connection.execute("""
        SELECT full_name, email, roll_number, branch, semester, role, created_at
        FROM users WHERE id=?
    """, (session["user_id"],)).fetchone()

    uploads = connection.execute("""
        SELECT * FROM resources
        WHERE uploaded_by=?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    stats = connection.execute("""
        SELECT
            COUNT(*) AS total_uploads,
            SUM(CASE WHEN resource_type='Notes' THEN 1 ELSE 0 END) AS total_notes,
            SUM(CASE WHEN resource_type='PYQ' THEN 1 ELSE 0 END) AS total_pyqs
        FROM resources WHERE uploaded_by=?
    """, (session["user_id"],)).fetchone()
    return render_template("profile.html", user=user, uploads=uploads, stats=stats)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        title = clean_text(request.form.get("title"), 120)
        subject = clean_text(request.form.get("subject"), 100)
        branch = request.form.get("branch", "")
        semester = request.form.get("semester", "")
        resource_type = request.form.get("resource_type", "")
        file = request.files.get("pdf")

        if not title or not subject:
            flash("Title and subject are required.", "error")
        elif branch not in BRANCHES:
            flash("Please select a valid branch.", "error")
        elif not semester.isdigit() or not 1 <= int(semester) <= 8:
            flash("Please select a valid semester.", "error")
        elif resource_type not in RESOURCE_TYPES:
            flash("Please select a valid resource type.", "error")
        elif not file or not file.filename:
            flash("Please select a PDF file.", "error")
        elif not valid_pdf(file.filename):
            flash("Only PDF files are allowed.", "error")
        else:
            filename = safe_upload_name(file.filename)
            path = UPLOAD_FOLDER / filename
            file.save(path)

            try:
                db().execute("""
                    INSERT INTO resources
                    (title, subject, branch, semester, resource_type, filename, uploaded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    title, subject, branch, int(semester), resource_type,
                    filename, session["user_id"]
                ))
                db().commit()
                flash("Resource uploaded successfully.", "success")
                return redirect(url_for("profile"))
            except Exception:
                if path.exists():
                    path.unlink()
                raise

    return render_template("upload.html", branches=BRANCHES, resource_types=RESOURCE_TYPES)


@app.route("/edit_resource/<int:id>", methods=["GET", "POST"])
@login_required
def edit_resource(id):
    resource = db().execute("""
        SELECT * FROM resources
        WHERE id=? AND uploaded_by=?
    """, (id, session["user_id"])).fetchone()

    if resource is None:
        flash("Resource not found or you do not have permission to edit it.", "error")
        return redirect(url_for("profile"))

    if request.method == "POST":
        title = clean_text(request.form.get("title"), 120)
        subject = clean_text(request.form.get("subject"), 100)
        branch = request.form.get("branch", "")
        semester = request.form.get("semester", "")
        resource_type = request.form.get("resource_type", "")

        if not title or not subject or branch not in BRANCHES or not semester.isdigit() or not 1 <= int(semester) <= 8 or resource_type not in RESOURCE_TYPES:
            flash("Please provide valid resource details.", "error")
        else:
            db().execute("""
                UPDATE resources
                SET title=?, subject=?, branch=?, semester=?, resource_type=?
                WHERE id=? AND uploaded_by=?
            """, (title, subject, branch, int(semester), resource_type, id, session["user_id"]))
            db().commit()
            flash("Resource updated successfully.", "success")
            return redirect(url_for("profile"))

    return render_template("edit_resource.html", resource=resource, branches=BRANCHES, resource_types=RESOURCE_TYPES)


@app.route("/delete_resource/<int:id>", methods=["POST"])
@login_required
def delete_resource(id):
    resource = db().execute("""
        SELECT filename FROM resources
        WHERE id=? AND uploaded_by=?
    """, (id, session["user_id"])).fetchone()

    if resource is None:
        flash("Resource not found.", "error")
        return redirect(url_for("profile"))

    db().execute("DELETE FROM resources WHERE id=? AND uploaded_by=?", (id, session["user_id"]))
    db().commit()

    path = UPLOAD_FOLDER / resource["filename"]
    if path.exists():
        path.unlink()

    flash("Resource deleted successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/admin")
@admin_required
def admin_panel():
    connection = db()
    users = connection.execute("""
        SELECT id, full_name, email, roll_number, branch, semester, role, created_at
        FROM users ORDER BY id DESC
    """).fetchall()
    resources = connection.execute("""
        SELECT resources.*, users.full_name AS uploader_name
        FROM resources LEFT JOIN users ON users.id=resources.uploaded_by
        ORDER BY resources.id DESC
    """).fetchall()
    totals = connection.execute("""
        SELECT
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM resources) AS total_resources,
            (SELECT COUNT(*) FROM users WHERE role='admin') AS total_admins
    """).fetchone()
    return render_template("admin.html", users=users, resources=resources, totals=totals)


@app.route("/admin/resource/<int:id>/delete", methods=["POST"])
@admin_required
def admin_delete_resource(id):
    resource = db().execute("SELECT filename FROM resources WHERE id=?", (id,)).fetchone()
    if resource:
        db().execute("DELETE FROM resources WHERE id=?", (id,))
        db().commit()
        path = UPLOAD_FOLDER / resource["filename"]
        if path.exists():
            path.unlink()
        flash("Resource deleted successfully.", "success")
    else:
        flash("Resource not found.", "error")
    return redirect(url_for("admin_panel"))


@app.route("/admin/user/<int:id>/role", methods=["POST"])
@admin_required
def admin_update_role(id):
    role = request.form.get("role")
    if role not in {"admin", "student"}:
        flash("Invalid role selected.", "error")
    elif id == session["user_id"] and role != "admin":
        flash("You cannot remove your own admin access.", "error")
    else:
        result = db().execute("UPDATE users SET role=? WHERE id=?", (role, id))
        db().commit()
        if result.rowcount:
            flash("User role updated successfully.", "success")
        else:
            flash("User not found.", "error")
    return redirect(url_for("admin_panel"))


@app.route("/admin/user/<int:id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(id):
    if id == session["user_id"]:
        flash("You cannot delete your own admin account.", "error")
        return redirect(url_for("admin_panel"))

    connection = db()
    user = connection.execute("SELECT id, full_name FROM users WHERE id=?", (id,)).fetchone()
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin_panel"))

    resources = connection.execute(
        "SELECT filename FROM resources WHERE uploaded_by=?", (id,)
    ).fetchall()
    connection.execute("DELETE FROM resources WHERE uploaded_by=?", (id,))
    connection.execute("DELETE FROM users WHERE id=?", (id,))
    connection.commit()

    for resource in resources:
        path = UPLOAD_FOLDER / resource["filename"]
        if path.exists():
            path.unlink()

    flash(f"User {user['full_name']} and their uploaded resources were deleted.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
