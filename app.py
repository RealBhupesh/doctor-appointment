from __future__ import annotations

import os
from datetime import date
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db_connection, init_schema, requires_postgres_on_vercel

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")


def init_db() -> None:
    conn = get_db_connection()
    init_schema(conn)
    conn.close()


def ensure_default_admin() -> None:
    conn = get_db_connection()
    admin = conn.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1").fetchone()
    if admin is None:
        conn.execute(
            """
            INSERT INTO users (full_name, email, password_hash, is_admin)
            VALUES (?, ?, ?, 1)
            """,
            ("Clinic Admin", "admin@clinic.com", generate_password_hash("admin123")),
        )
        conn.commit()
    conn.close()


def ensure_default_doctors() -> None:
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO doctors (name, specialty) VALUES (?, ?)",
            [
                ("Dr. Smith", "Cardiologist"),
                ("Dr. Patel", "General Physician"),
                ("Dr. Chen", "Dermatologist"),
            ],
        )
        conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Only admins can access that page.", "danger")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
def home():
    conn = get_db_connection()
    stats = conn.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved_count
        FROM appointments
        """
    ).fetchone()
    conn.close()
    return render_template("home.html", stats=stats)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password should be at least 6 characters.", "danger")
            return redirect(url_for("register"))

        conn = get_db_connection()
        existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            conn.close()
            flash("An account already exists with that email.", "warning")
            return redirect(url_for("register"))

        conn.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name, email, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()

        flash("Registration successful. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, full_name, email, password_hash, is_admin FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]
        session["email"] = user["email"]
        session["is_admin"] = bool(user["is_admin"])

        flash("Welcome back!", "success")
        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("booking"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():
    if request.method == "POST":
        doctor_name = request.form.get("doctor_name", "").strip()
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()
        reason = request.form.get("reason", "").strip()

        if not doctor_name or not appointment_date or not appointment_time or not reason:
            flash("Please complete all booking fields.", "danger")
            return redirect(url_for("booking"))

        try:
            selected_date = date.fromisoformat(appointment_date)
            if selected_date < date.today():
                flash("Please choose today or a future date.", "warning")
                return redirect(url_for("booking"))
        except ValueError:
            flash("Invalid appointment date.", "danger")
            return redirect(url_for("booking"))

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO appointments (user_id, doctor_name, appointment_date, appointment_time, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session["user_id"], doctor_name, appointment_date, appointment_time, reason),
        )
        conn.commit()
        conn.close()

        flash("Appointment request submitted.", "success")
        return redirect(url_for("booking"))

    conn = get_db_connection()
    doctors = conn.execute(
        "SELECT id, name, specialty FROM doctors ORDER BY name"
    ).fetchall()
    user_appointments = conn.execute(
        """
        SELECT id, doctor_name, appointment_date, appointment_time, reason, status, created_at
        FROM appointments
        WHERE user_id = ?
        ORDER BY appointment_date, appointment_time
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("booking.html", appointments=user_appointments, doctors=doctors)


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    appointments = conn.execute(
        """
        SELECT
            a.id,
            a.doctor_name,
            a.appointment_date,
            a.appointment_time,
            a.reason,
            a.status,
            a.created_at,
            u.full_name,
            u.email
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """
    ).fetchall()
    conn.close()
    return render_template("admin_dashboard.html", appointments=appointments)


@app.route("/admin/doctors")
@login_required
@admin_required
def admin_doctors():
    conn = get_db_connection()
    doctors = conn.execute(
        "SELECT id, name, specialty FROM doctors ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("admin_doctors.html", doctors=doctors)


@app.route("/admin/doctors/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_doctor():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        specialty = request.form.get("specialty", "").strip()
        if not name or not specialty:
            flash("Name and specialty are required.", "danger")
            return redirect(url_for("admin_add_doctor"))
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO doctors (name, specialty) VALUES (?, ?)",
            (name, specialty),
        )
        conn.commit()
        conn.close()
        flash("Doctor added successfully.", "success")
        return redirect(url_for("admin_doctors"))
    return render_template("admin_doctor_form.html", doctor=None)


@app.route("/admin/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_doctor(doctor_id: int):
    conn = get_db_connection()
    doctor = conn.execute(
        "SELECT id, name, specialty FROM doctors WHERE id = ?", (doctor_id,)
    ).fetchone()
    conn.close()
    if doctor is None:
        flash("Doctor not found.", "danger")
        return redirect(url_for("admin_doctors"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        specialty = request.form.get("specialty", "").strip()
        if not name or not specialty:
            flash("Name and specialty are required.", "danger")
            return redirect(url_for("admin_edit_doctor", doctor_id=doctor_id))
        conn = get_db_connection()
        conn.execute(
            "UPDATE doctors SET name = ?, specialty = ? WHERE id = ?",
            (name, specialty, doctor_id),
        )
        conn.commit()
        conn.close()
        flash("Doctor updated successfully.", "success")
        return redirect(url_for("admin_doctors"))
    return render_template("admin_doctor_form.html", doctor=doctor)


@app.route("/admin/doctors/<int:doctor_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_doctor(doctor_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    conn.commit()
    conn.close()
    flash("Doctor removed.", "success")
    return redirect(url_for("admin_doctors"))


@app.route("/admin/appointment/<int:appointment_id>/status", methods=["POST"])
@login_required
@admin_required
def update_appointment_status(appointment_id: int):
    new_status = request.form.get("status", "").strip().lower()
    allowed_statuses = {"pending", "approved", "cancelled", "completed"}
    if new_status not in allowed_statuses:
        flash("Invalid status selected.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE appointments SET status = ? WHERE id = ?",
        (new_status, appointment_id),
    )
    conn.commit()
    conn.close()
    flash("Appointment status updated.", "success")
    return redirect(url_for("admin_dashboard"))


_db_initialized = False


def _ensure_db_ready():
    """Run DB init once, on first request. Catches errors so the app can load."""
    global _db_initialized
    if _db_initialized:
        return
    try:
        init_db()
        ensure_default_admin()
        ensure_default_doctors()
        _db_initialized = True
    except Exception:
        _db_initialized = False
        raise


@app.route("/setup-required")
def setup_required():
    """Shown when on Vercel without Postgres."""
    return render_template("setup_required.html")


@app.before_request
def _before_request():
    # Block all routes (except setup page and static) when Postgres is required but missing
    if requires_postgres_on_vercel():
        if request.endpoint not in (None, "setup_required", "static"):
            return redirect(url_for("setup_required"))
    _ensure_db_ready()


if __name__ == "__main__":
    app.run(debug=True)
