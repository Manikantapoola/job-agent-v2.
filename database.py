from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    age = db.Column(db.Integer)
    location = db.Column(db.String(100), default="USA")
    linkedin_url = db.Column(db.String(300))
    github_url = db.Column(db.String(300))
    portfolio_url = db.Column(db.String(300))
    target_roles = db.Column(db.Text, default="AI/ML Engineer,AI Product Manager,AI Data Analyst,AI Analyst")
    preferred_work_mode = db.Column(db.String(30), default="Remote")
    experience_level = db.Column(db.String(30), default="Entry Level")
    resume_path = db.Column(db.String(300))
    notify_email = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_run_at = db.Column(db.DateTime)
    jobs = db.relationship("Job", backref="user", lazy=True)

    def target_roles_list(self):
        return [r.strip() for r in self.target_roles.split(",")]


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200))
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    url = db.Column(db.String(500), unique=True)
    source = db.Column(db.String(50))
    match_score = db.Column(db.Float, default=0.0)
    match_reasons = db.Column(db.Text)
    status = db.Column(db.String(30), default="found")
    found_at = db.Column(db.DateTime, default=datetime.utcnow)
    hr_name = db.Column(db.String(200))
    hr_email = db.Column(db.String(200))
    hr_title = db.Column(db.String(200))
    followup_sent = db.Column(db.Boolean, default=False)
    followup_email_text = db.Column(db.Text)
    applications = db.relationship("Application", backref="job", lazy=True)


class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    status = db.Column(db.String(30), default="pending")
    tailored_resume_path = db.Column(db.String(300))
    applied_at = db.Column(db.DateTime)
    confirmation_text = db.Column(db.Text)
    error_log = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)