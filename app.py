import os
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "ghrcem_study_portal_2026"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- NOTES ----------------

@app.route("/notes")
def notes():

    search = request.args.get("search", "").strip()
    branch = request.args.get("branch", "")
    semester = request.args.get("semester", "")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT *
        FROM resources
        WHERE resource_type='Notes'
    """

    params = []

    if search:
        query += " AND (title LIKE ? OR subject LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if branch:
        query += " AND branch=?"
        params.append(branch)

    if semester:
        query += " AND semester=?"
        params.append(semester)

    query += " ORDER BY id DESC"

    cursor.execute(query, params)

    notes = cursor.fetchall()

    conn.close()

    return render_template(
        "notes.html",
        notes=notes,
        search=search,
        branch=branch,
        semester=semester
    )
# ---------------- PYQ ----------------

@app.route("/pyq")
def pyq():

    # Get Search Keyword
    search = request.args.get("search", "").strip()

    # Connect Database
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Search
    if search == "":

        cursor.execute("""
            SELECT *
            FROM resources
            WHERE resource_type='PYQ'
            ORDER BY id DESC
        """)

    else:

        cursor.execute("""
            SELECT *
            FROM resources
            WHERE resource_type='PYQ'
            AND (
                title LIKE ?
                OR subject LIKE ?
            )
            ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%"))

    pyqs = cursor.fetchall()

    conn.close()

    return render_template(
        "pyq.html",
        pyqs=pyqs,
        search=search
    )


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # ---------------- GET FORM DATA ----------------
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        roll_number = request.form["roll_number"].strip()
        branch = request.form["branch"]
        semester = request.form["semester"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # ---------------- EMAIL VALIDATION ----------------
        email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'

        if not re.match(email_pattern, email):
            flash("Please enter a valid email address.")
            return redirect(url_for("register"))

        # ---------------- PASSWORD MATCH ----------------
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        # ---------------- STRONG PASSWORD ----------------
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#]).{8,}$'

        if not re.match(pattern, password):
            flash("Password is not strong enough.")
            return redirect(url_for("register"))

        # ---------------- HASH PASSWORD ----------------
        password_hash = generate_password_hash(password)

        # ---------------- DATABASE ----------------
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Check Duplicate Email
        cursor.execute(
            "SELECT id FROM users WHERE email=?",
            (email,)
        )

        if cursor.fetchone():
            conn.close()
            flash("Email already registered.")
            return redirect(url_for("register"))

        # Check Duplicate Registration Number
        cursor.execute(
            "SELECT id FROM users WHERE roll_number=?",
            (roll_number,)
        )

        if cursor.fetchone():
            conn.close()
            flash("Registration Number already exists.")
            return redirect(url_for("register"))

        # Insert New User
        cursor.execute("""
        INSERT INTO users
        (full_name, email, roll_number, branch, semester, password_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            full_name,
            email,
            roll_number,
            branch,
            semester,
            password_hash
        ))

        conn.commit()
        conn.close()

        # ---------------- SUCCESS ----------------
        flash("✅ Registration Successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # ---------------- GET FORM DATA ----------------
        roll_number = request.form["roll_number"].strip()
        password = request.form["password"]

        # ---------------- CONNECT DATABASE ----------------
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # ---------------- CHECK USER ----------------
        cursor.execute("""
            SELECT id, full_name, password_hash
            FROM users
            WHERE roll_number = ?
        """, (roll_number,))

        user = cursor.fetchone()

        conn.close()

        # ---------------- ACCOUNT NOT FOUND ----------------
        if user is None:
            flash("❌ Account not found. Please create an account first.")
            return redirect(url_for("register"))

        # ---------------- WRONG PASSWORD ----------------
        if not check_password_hash(user[2], password):
            flash("❌ Incorrect password.")
            return redirect(url_for("login"))

        # ---------------- LOGIN SUCCESS ----------------
        session["user_id"] = user[0]
        session["user_name"] = user[1]

        flash(f"✅ Welcome, {user[1]}!")

        return redirect(url_for("dashboard"))

    # ---------------- OPEN LOGIN PAGE ----------------
    return render_template("login.html")

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    # Check Login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Connect Database
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Total Notes
    cursor.execute(
        "SELECT COUNT(*) FROM resources WHERE resource_type='Notes'"
    )
    total_notes = cursor.fetchone()[0]

    # Total PYQs
    cursor.execute(
        "SELECT COUNT(*) FROM resources WHERE resource_type='PYQ'"
    )
    total_pyqs = cursor.fetchone()[0]

    conn.close()

    # Open Dashboard
    return render_template(
        "dashboard.html",
        name=session["user_name"],
        total_notes=total_notes,
        total_pyqs=total_pyqs
    )

# ---------------- PROFILE ----------------

@app.route("/profile")
def profile():

    # Check Login
    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ================= User Details =================

    cursor.execute("""
        SELECT
            full_name,
            roll_number,
            branch,
            semester
        FROM users
        WHERE id=?
    """, (session["user_id"],))

    user = cursor.fetchone()

    # ================= User Uploads =================

    cursor.execute("""
        SELECT *
        FROM resources
        WHERE uploaded_by=?
        ORDER BY id DESC
    """, (session["user_id"],))

    uploads = cursor.fetchall()

    # ================= Statistics =================

    cursor.execute("""
        SELECT COUNT(*)
        FROM resources
        WHERE uploaded_by=?
    """, (session["user_id"],))

    total_uploads = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM resources
        WHERE uploaded_by=?
        AND resource_type='Notes'
    """, (session["user_id"],))

    total_notes = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM resources
        WHERE uploaded_by=?
        AND resource_type='PYQ'
    """, (session["user_id"],))

    total_pyqs = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        uploads=uploads,
        total_uploads=total_uploads,
        total_notes=total_notes,
        total_pyqs=total_pyqs
    )
# ---------------- EDIT RESOURCE ----------------

@app.route("/edit_resource/<int:id>", methods=["GET", "POST"])
def edit_resource(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get resource
    cursor.execute("""
        SELECT *
        FROM resources
        WHERE id=?
        AND uploaded_by=?
    """, (id, session["user_id"]))

    resource = cursor.fetchone()

    if resource is None:
        flash("Resource not found.")
        conn.close()
        return redirect(url_for("profile"))

    # Update
    if request.method == "POST":

        title = request.form["title"]
        subject = request.form["subject"]
        branch = request.form["branch"]
        semester = request.form["semester"]
        resource_type = request.form["resource_type"]

        cursor.execute("""
            UPDATE resources
            SET
                title=?,
                subject=?,
                branch=?,
                semester=?,
                resource_type=?
            WHERE id=?
            AND uploaded_by=?
        """,
        (
            title,
            subject,
            branch,
            semester,
            resource_type,
            id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash("Resource updated successfully.", "profile")

        return redirect(url_for("profile"))

    conn.close()

    return render_template(
        "edit_resource.html",
        resource=resource
    )

# ---------------- DELETE RESOURCE ----------------

@app.route("/delete_resource/<int:id>")
def delete_resource(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Pehle filename lo
    cursor.execute("""
        SELECT filename
        FROM resources
        WHERE id=?
        AND uploaded_by=?
    """, (id, session["user_id"]))

    file = cursor.fetchone()

    if file:

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file[0])

        if os.path.exists(file_path):
            os.remove(file_path)

        cursor.execute("""
            DELETE FROM resources
            WHERE id=?
            AND uploaded_by=?
        """, (id, session["user_id"]))

        conn.commit()

    conn.close()

    flash("Resource deleted successfully.", "profile")

    return redirect(url_for("profile"))
# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()
    flash("Logged out successfully.")

    return redirect(url_for("home"))

# ==========================================
# Upload Notes / PYQ
# ==========================================
@app.route("/upload", methods=["GET", "POST"])
def upload():

    # ------------------------------
    # Check if user is logged in
    # ------------------------------
    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    # ------------------------------
    # If user submits the upload form
    # ------------------------------
    if request.method == "POST":

        # Get form data
        title = request.form["title"]
        subject = request.form["subject"]
        branch = request.form["branch"]
        semester = request.form["semester"]
        resource_type = request.form["resource_type"]

        # Get uploaded PDF file
        file = request.files["pdf"]

        # Check if a file is selected
        if file.filename == "":
            flash("Please select a PDF file.")
            return redirect(url_for("upload"))

        # Convert filename into a safe format
        filename = secure_filename(file.filename)

        # Save PDF inside static/uploads folder
        file.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

        # ------------------------------
        # Save resource details in database
        # ------------------------------
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO resources
        (
            title,
            subject,
            branch,
            semester,
            resource_type,
            filename,
            uploaded_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            subject,
            branch,
            semester,
            resource_type,
            filename,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        # Success message
        flash("✅ Resource Uploaded Successfully!", "upload")
        return redirect(url_for("upload"))

    # Open Upload Page
    return render_template("upload.html")


#print(app.url_map)
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)