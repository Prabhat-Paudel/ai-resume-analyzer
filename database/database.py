from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()


def utc_now():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """Database model for application users."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(256),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

    # One user can upload multiple resumes.
    resumes = db.relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # One user can have multiple analyses.
    analyses = db.relationship(
        "Analysis",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Resume(db.Model):
    """Database model for uploaded resumes."""

    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    extracted_text = db.Column(
        db.Text,
        nullable=False,
        default=""
    )

    skills = db.Column(
        db.JSON,
        nullable=False,
        default=list
    )

    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="resumes"
    )

    analyses = db.relationship(
        "Analysis",
        back_populates="resume",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Resume {self.filename}>"


class Analysis(db.Model):
    """Database model for job-matching analysis results."""

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    resume_id = db.Column(
        db.Integer,
        db.ForeignKey("resumes.id"),
        nullable=False,
        index=True
    )

    job_title = db.Column(
        db.String(150),
        nullable=False,
        default="Untitled Job"
    )

    job_description = db.Column(
        db.Text,
        nullable=False
    )

    match_score = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    matched_skills = db.Column(
        db.JSON,
        nullable=False,
        default=list
    )

    missing_skills = db.Column(
        db.JSON,
        nullable=False,
        default=list
    )

    suggestions = db.Column(
        db.JSON,
        nullable=False,
        default=list
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="analyses"
    )

    resume = db.relationship(
        "Resume",
        back_populates="analyses"
    )

    def __repr__(self):
        return (
            f"<Analysis {self.id}: "
            f"{self.match_score}%>"
        )