from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.models import (
    get_user_by_email,
    get_user_by_email_or_username,
    create_user,
)
from auth.auth_utils import hash_password, verify_password, validate_email, validate_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            user = get_user_by_email(email)
            if user and verify_password(password, user["password"]):
                session["user_id"]  = user["user_id"]
                session["username"] = user["username"]
                flash("Welcome back, " + user["username"] + "!", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "error")
        except Exception as e:
            flash("Database connection failed. Please check your Supabase project is active.", "error")
            print(f"[VidhiAI] Login error: {e}")
    return render_template("login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not username or len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return render_template("signup.html")
        if not validate_email(email):
            flash("Invalid email address.", "error")
            return render_template("signup.html")
        valid, msg = validate_password(password)
        if not valid:
            flash(msg, "error")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")

        existing = get_user_by_email_or_username(email, username)
        if existing:
            flash("Email or username already registered.", "error")
            return render_template("signup.html")

        hashed = hash_password(password)
        user   = create_user(username, email, hashed)
        session["user_id"]  = user["user_id"]
        session["username"] = user["username"]
        flash("Account created! Welcome, " + username + ".", "success")
        return redirect(url_for("dashboard"))
    return render_template("signup.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))
