import os
from pathlib import Path

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify
)

from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database.database import db, User


# -----------------------------------
# APPLICATION CONFIGURATION
# -----------------------------------

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, instance_relative_config=True)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-only-change-this-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + str(BASE_DIR / "instance" / "resume_analyzer.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["UPLOAD_FOLDER"] = str(BASE_DIR / "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# -----------------------------------
# DATABASE INITIALIZATION
# -----------------------------------

db.init_app(app)


# -----------------------------------
# LOGIN MANAGER
# -----------------------------------

login_manager = LoginManager()

login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


# -----------------------------------
# HOME PAGE
# -----------------------------------

@app.route("/")
def home():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# -----------------------------------
# USER REGISTRATION
# -----------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        confirm_password = request.form.get(
            "confirm_password", ""
        )

        # Validate empty fields
        if not username or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("register"))

        # Validate username
        if len(username) < 3 or len(username) > 80:
            flash(
                "Username must contain 3 to 80 characters.",
                "danger"
            )
            return redirect(url_for("register"))

        # Validate email
        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("register"))

        # Validate password
        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        # Check existing username
        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))

        # Check existing email
        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_email:
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        # Hash password
        hashed_password = generate_password_hash(password)

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()

            flash(
                "Registration successful! Please log in.",
                "success"
            )

            return redirect(url_for("login"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Registration failed")

            flash(
                "Something went wrong. Please try again.",
                "danger"
            )

            return redirect(url_for("register"))

    return render_template("register.html")


# -----------------------------------
# USER LOGIN
# -----------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        if not email or not password:
            flash(
                "Please enter your email and password.",
                "danger"
            )
            return redirect(url_for("login"))

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password_hash, password
        ):

            login_user(user)

            flash(
                f"Welcome back, {user.username}!",
                "success"
            )

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password.",
            "danger"
        )

        return redirect(url_for("login"))

    return render_template("login.html")


# -----------------------------------
# USER LOGOUT
# -----------------------------------

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash(
        "You have successfully logged out.",
        "success"
    )

    return redirect(url_for("login"))


# -----------------------------------
# USER DASHBOARD
# -----------------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    total_resumes = len(current_user.resumes)

    total_analyses = len(current_user.analyses)

    if total_analyses:
        average_match = sum(
            analysis.match_score
            for analysis in current_user.analyses
        ) / total_analyses
    else:
        average_match = 0

    latest_analyses = (
        db.session.query(
            __import__("database.database", fromlist=["Analysis"]).Analysis
        )
        .filter_by(user_id=current_user.id)
        .order_by(
            __import__("database.database", fromlist=["Analysis"]).Analysis.created_at.desc()
        )
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_resumes=total_resumes,
        total_analyses=total_analyses,
        average_match=round(average_match, 1),
        latest_analyses=latest_analyses
    )


# -----------------------------------
# HEALTH CHECK
# -----------------------------------

@app.route("/health")
def health():

    try:
        db.session.execute(db.text("SELECT 1"))

        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200

    except Exception:
        app.logger.exception("Database health check failed")

        return jsonify({
            "status": "unhealthy",
            "database": "connection failed"
        }), 500


# -----------------------------------
# ERROR HANDLING
# -----------------------------------

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error": "File is too large. Maximum size is 5 MB."
    }), 413


# -----------------------------------
# DATABASE SETUP
# -----------------------------------

def initialize_database():

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()


# -----------------------------------
# RUN APPLICATION
# -----------------------------------

if __name__ == "__main__":

    initialize_database()

    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )