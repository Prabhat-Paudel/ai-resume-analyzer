import os
from pathlib import Path

from flask import Flask, jsonify
from flask_login import LoginManager

from database.database import db, User


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, instance_relative_config=True)

# Use an environment variable for the secret key.
# The fallback is only for local development.
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-only-change-this-secret-key"
)

# SQLite database location.
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + str(BASE_DIR / "instance" / "resume_analyzer.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload configuration.
app.config["UPLOAD_FOLDER"] = str(BASE_DIR / "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Initialize extensions.
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# --------------------------------------------------
# USER SESSION MANAGEMENT
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    """Load a user from the database for Flask-Login."""
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route("/")
def home():
    """Temporary home page until the frontend is built."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">
        <title>AI Resume Analyzer</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f1f5f9;
                margin: 0;
                padding: 60px 20px;
                text-align: center;
            }
            .card {
                background: white;
                max-width: 650px;
                margin: auto;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.08);
            }
            h1 {
                color: #2563eb;
            }
            p {
                color: #475569;
                line-height: 1.7;
            }
            .badge {
                display: inline-block;
                background: #dcfce7;
                color: #166534;
                padding: 8px 14px;
                border-radius: 20px;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>AI Resume Analyzer</h1>
            <span class="badge">Backend Running</span>
            <p>
                Welcome to your AI-powered Resume Analyzer
                and Job Matcher project.
            </p>
            <p>
                Flask is running. The database models are
                configured and ready for development.
            </p>
        </div>
    </body>
    </html>
    """


@app.route("/health")
def health():
    """Check whether the application and database are working."""
    try:
        db.session.execute(db.text("SELECT 1"))

        return jsonify({
            "status": "healthy",
            "application": "AI Resume Analyzer",
            "database": "connected"
        }), 200

    except Exception:
        app.logger.exception("Database health check failed")

        return jsonify({
            "status": "unhealthy",
            "database": "connection failed"
        }), 500


@app.errorhandler(413)
def file_too_large(error):
    """Handle uploaded files that exceed the configured size."""
    return jsonify({
        "error": "File is too large. Maximum size is 5 MB."
    }), 413


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def initialize_database():
    """Create required folders and database tables."""
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    initialize_database()

    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )