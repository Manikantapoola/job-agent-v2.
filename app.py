import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dotenv import load_dotenv
import atexit

load_dotenv()

from database import db, User, Job, Application

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///job_agent.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "resumes\\base"

db.init_app(app)

scheduler = BackgroundScheduler()

def scheduled_job():
    with app.app_context():
        from agent.job_agent import run_agent_cycle
        users = User.query.filter_by(is_active=True).all()
        for user in users:
            try:
                run_agent_cycle(user.id)
            except Exception as e:
                logger.error(f"Agent cycle failed: {e}")

scheduler.add_job(scheduled_job, "interval", hours=3, id="job_agent_cycle")
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

@app.route("/")
def index():
    user = User.query.first()
    if not user:
        return redirect(url_for("onboarding"))
    return redirect(url_for("dashboard"))

@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if request.method == "POST":
        data = request.form
        resume_file = request.files.get("resume")
        resume_path = ""
        if resume_file and resume_file.filename:
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            resume_path = os.path.join(app.config["UPLOAD_FOLDER"], resume_file.filename)
            resume_file.save(resume_path)
        user = User(
            full_name=data["full_name"],
            email=data["email"],
            phone=data["phone"],
            age=int(data.get("age", 0)),
            location=data.get("location", "USA"),
            linkedin_url=data.get("linkedin_url", ""),
            github_url=data.get("github_url", ""),
            portfolio_url=data.get("portfolio_url", ""),
            target_roles=data.get("target_roles", "AI/ML Engineer,AI Product Manager,AI Data Analyst,AI Analyst"),
            preferred_work_mode=data.get("preferred_work_mode", "Remote"),
            experience_level=data.get("experience_level", "Entry Level"),
            resume_path=resume_path,
            notify_email=data.get("notify_email", data["email"]),
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("onboarding.html")

@app.route("/dashboard")
def dashboard():
    user = User.query.first()
    if not user:
        return redirect(url_for("onboarding"))
    applications = (
        Application.query.join(Job)
        .filter(Job.user_id == user.id)
        .order_by(Application.created_at.desc())
        .limit(50).all()
    )
    stats = {
        "total_applied": Application.query.join(Job).filter(Job.user_id == user.id).count(),
        "avg_match": round(db.session.query(db.func.avg(Job.match_score)).filter(Job.user_id == user.id).scalar() or 0, 1),
        "pending": Application.query.join(Job).filter(Job.user_id == user.id, Application.status == "applied").count(),
    }
    return render_template("dashboard.html", user=user, applications=applications, stats=stats)

@app.route("/api/run-now", methods=["POST"])
def run_now():
    from agent.job_agent import run_agent_cycle
    user = User.query.first()
    if not user:
        return jsonify({"error": "No user found"}), 404
    try:
        result = run_agent_cycle(user.id)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/job/<int:job_id>")
def api_job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    app_record = Application.query.filter_by(job_id=job_id).first()
    return jsonify({
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "source": job.source,
        "match_score": job.match_score,
        "match_reason": job.match_reasons,
        "description": job.description or "No description available",
        "url": job.url,
        "status": job.status,
        "hr_name": job.hr_name or "",
        "hr_email": job.hr_email or "",
        "hr_title": job.hr_title or "",
        "followup_sent": job.followup_sent or False,
        "followup_email": job.followup_email_text or "",
        "resume_path": app_record.tailored_resume_path if app_record else "",
        "applied_at": app_record.applied_at.isoformat() if app_record and app_record.applied_at else "",
    })

@app.route("/api/resume-text/<int:job_id>")
def api_resume_text(job_id):
    app_record = Application.query.filter_by(job_id=job_id).first()
    if not app_record or not app_record.tailored_resume_path:
        return jsonify({"error": "No resume found"}), 404
    try:
        from docx import Document
        doc = Document(app_record.tailored_resume_path)
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append({
                    "text": para.text.strip(),
                    "bold": any(run.bold for run in para.runs),
                    "style": para.style.name if para.style else ""
                })
        return jsonify({"paragraphs": paragraphs, "path": app_record.tailored_resume_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download-resume/<int:job_id>")
def download_resume(job_id):
    app_record = Application.query.filter_by(job_id=job_id).first()
    if not app_record or not app_record.tailored_resume_path:
        return "No resume found", 404
    try:
        return send_file(
            app_record.tailored_resume_path,
            as_attachment=True,
            download_name=f"resume_{job_id}.docx"
        )
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, use_reloader=False)