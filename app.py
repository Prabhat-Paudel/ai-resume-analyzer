
import os
import uuid
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from sqlalchemy import text

from database.database import db, User, Resume, Analysis

from services.resume_parser import extract_text_from_pdf
from services.skill_extractor import extract_skills
from services.job_matcher import match_job


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

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

ALLOWED_EXTENSIONS = {"pdf"}


# --------------------------------------------------
# DATABASE AND LOGIN CONFIGURATION
# --------------------------------------------------

db.init_app(app)

login_manager = LoginManager()

login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# --------------------------------------------------
# USER REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")

        elif len(username) < 3 or len(username) > 80:
            flash("Username must be between 3 and 80 characters.", "danger")

        elif "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")

        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")

        elif password != confirm_password:
            flash("Passwords do not match.", "danger")

        else:

            existing_user = User.query.filter(
                (User.username == username) |
                (User.email == email)
            ).first()

            if existing_user:
                flash("Username or email already exists.", "danger")

            else:

                new_user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password)
                )

                try:
                    db.session.add(new_user)
                    db.session.commit()

                    flash("Registration successful. Please log in.", "success")

                    return redirect(url_for("login"))

                except Exception:
                    db.session.rollback()
                    flash("Registration failed. Please try again.", "danger")

    return render_template("register.html")


# --------------------------------------------------
# USER LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):

            login_user(user)

            flash("Login successful!", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# --------------------------------------------------
# USER LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", "success")

    return redirect(url_for("login"))


# --------------------------------------------------
# USER DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    total_resumes = Resume.query.filter_by(
        user_id=current_user.id
    ).count()

    total_analyses = Analysis.query.filter_by(
        user_id=current_user.id
    ).count()

    recent_analyses = Analysis.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Analysis.created_at.desc()
    ).limit(5).all()

    scores = [
        analysis.match_score
        for analysis in Analysis.query.filter_by(
            user_id=current_user.id
        ).all()
        if analysis.match_score is not None
    ]

    average_score = (
        round(sum(scores) / len(scores), 2)
        if scores else 0
    )

    return render_template(
        "dashboard.html",
        total_resumes=total_resumes,
        total_analyses=total_analyses,
        average_score=average_score,
        recent_analyses=recent_analyses
    )


# --------------------------------------------------
# RESUME UPLOAD AND ANALYSIS
# --------------------------------------------------

@app.route("/upload-resume", methods=["GET", "POST"])
@login_required
def upload_resume():

    if request.method == "POST":

        if "resume" not in request.files:
            flash("Please select a resume.", "danger")
            return redirect(url_for("upload_resume"))

        file = request.files["resume"]

        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("upload_resume"))

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "danger")
            return redirect(url_for("upload_resume"))

        original_filename = secure_filename(file.filename)

        if not original_filename:
            flash("Invalid filename.", "danger")
            return redirect(url_for("upload_resume"))

        filename = f"{uuid.uuid4().hex}_{original_filename}"

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        try:

            # Save uploaded PDF
            file.save(file_path)

            # Check PDF signature
            with open(file_path, "rb") as pdf_file:
                if pdf_file.read(5) != b"%PDF-":
                    raise ValueError("Invalid PDF file.")

            # Extract text from PDF
            extracted_text = extract_text_from_pdf(file_path)

            if not extracted_text:
                raise ValueError(
                    "No readable text found in the PDF."
                )

            # Detect resume skills
            skills = extract_skills(extracted_text)

            # Save resume in database
            resume = Resume(
                user_id=current_user.id,
                filename=filename,
                extracted_text=extracted_text,
                skills=skills
            )

            db.session.add(resume)
            db.session.commit()

            flash(
                "Resume uploaded and analyzed successfully!",
                "success"
            )

            return redirect(
                url_for(
                    "analysis_result",
                    resume_id=resume.id
                )
            )

        except Exception as error:

            db.session.rollback()

            if os.path.exists(file_path):
                os.remove(file_path)

            app.logger.exception("Resume upload failed")

            flash(
                str(error) if isinstance(error, ValueError)
                else "Unable to process the resume.",
                "danger"
            )

            return redirect(url_for("upload_resume"))

    return render_template("upload_resume.html")


# --------------------------------------------------
# RESUME ANALYSIS RESULT
# --------------------------------------------------

@app.route("/analysis/<int:resume_id>")
@login_required
def analysis_result(resume_id):

    resume = Resume.query.filter_by(
        id=resume_id,
        user_id=current_user.id
    ).first_or_404()

    return render_template(
        "analysis_result.html",
        resume=resume
    )


# --------------------------------------------------
# JOB MATCHING
# --------------------------------------------------

@app.route("/job-match/<int:resume_id>", methods=["GET", "POST"])
@login_required
def job_match(resume_id):

    resume = Resume.query.filter_by(
        id=resume_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":

        job_title = request.form.get(
            "job_title", ""
        ).strip()

        job_description = request.form.get(
            "job_description", ""
        ).strip()

        if not job_title or not job_description:
            flash("Please enter the job title and description.", "danger")

            return redirect(
                url_for("job_match", resume_id=resume.id)
            )

        result = match_job(
            resume.skills or [],
            job_description
        )

        analysis = Analysis(
            user_id=current_user.id,
            resume_id=resume.id,
            job_title=job_title,
            job_description=job_description,
            match_score=result["match_score"],
            matched_skills=result["matched_skills"],
            missing_skills=result["missing_skills"],
            suggestions=result["suggestions"]
        )

        try:

            db.session.add(analysis)
            db.session.commit()

            return render_template(
                "job_match.html",
                resume=resume,
                result=result,
                analysis=analysis
            )

        except Exception:
            db.session.rollback()
            app.logger.exception("Job matching failed")

            flash("Unable to save job analysis.", "danger")

            return redirect(
                url_for("job_match", resume_id=resume.id)
            )

    return render_template(
        "job_match.html",
        resume=resume
    )


# --------------------------------------------------
# ANALYSIS HISTORY
# --------------------------------------------------

@app.route("/history")
@login_required
def history():

    analyses = Analysis.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Analysis.created_at.desc()
    ).all()

    return render_template(
        "history.html",
        analyses=analyses
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.route("/health")
def health():

    try:
        db.session.execute(text("SELECT 1"))

        return jsonify({
            "status": "success",
            "message": "Application and database are working."
        })

    except Exception:
        app.logger.exception("Health check failed")

        return jsonify({
            "status": "error",
            "message": "Database connection failed."
        }), 500


# --------------------------------------------------
# FILE SIZE ERROR
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):

    flash("File is too large. Maximum size is 5 MB.", "danger")

    return redirect(url_for("upload_resume"))


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def initialize_database():

    os.makedirs(BASE_DIR / "instance", exist_ok=True)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    initialize_database()

    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )
