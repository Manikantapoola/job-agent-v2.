import logging
from datetime import datetime
from database import db, User, Job, Application
from agent.scraper import JobScraper
from agent.matcher import JobMatcher
from agent.resume_tailor import ResumeTailor
from agent.applier import JobApplier
from agent.notifier import Notifier
from agent.followup import FollowUpSender

logger = logging.getLogger(__name__)

MAX_APPLICATIONS_PER_CYCLE = 50

def run_agent_cycle(user_id):
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    summary = {"jobs_found": 0, "jobs_matched": 0, "jobs_applied": 0, "jobs_failed": 0, "jobs_skipped": 0}
    logger.info(f"Starting cycle for {user.email}")

    scraper = JobScraper(user)
    raw_jobs = scraper.scrape_all()

    new_jobs = [j for j in raw_jobs if j.get("url") and not Job.query.filter_by(url=j["url"]).first()]
    summary["jobs_found"] = len(new_jobs)
    logger.info(f"{len(new_jobs)} new jobs after dedup")

    matcher = JobMatcher(user)
    matched = []

    for job_data in new_jobs:
        try:
            score, reason = matcher.compute_match(job_data.get("description", ""))
            hr_name, hr_email, hr_title = "", "", ""
            if job_data.get("url"):
                try:
                    hr_name, hr_email, hr_title = scraper.scrape_hr_contact(job_data["url"])
                except Exception:
                    pass
            job = Job(
                user_id=user.id,
                title=job_data["title"],
                company=job_data["company"],
                location=job_data.get("location", "Remote"),
                description=job_data.get("description", ""),
                url=job_data["url"],
                source=job_data.get("source", "unknown"),
                match_score=score,
                match_reasons=reason,
                status="matched" if score >= 50 else "rejected",
                hr_name=hr_name,
                hr_email=hr_email,
                hr_title=hr_title,
            )
            db.session.add(job)
            db.session.flush()
            if score >= 50:
                matched.append(job)
        except Exception as e:
            logger.error(f"Error processing job data: {e}")
            continue

    db.session.commit()
    summary["jobs_matched"] = len(matched)
    logger.info(f"{len(matched)} jobs matched")

    tailor = ResumeTailor(user)
    applier = JobApplier(user)
    followup = FollowUpSender(user)
    applied_jobs = []
    applications_this_cycle = 0

    for job in matched:
        if applications_this_cycle >= MAX_APPLICATIONS_PER_CYCLE:
            logger.info(f"Reached max {MAX_APPLICATIONS_PER_CYCLE} applications for this cycle. Stopping.")
            summary["jobs_skipped"] += len(matched) - applications_this_cycle
            break

        try:
            tailored_path = tailor.tailor(job)
            resume_text = tailor._read_resume()
            app_record = Application(job_id=job.id, tailored_resume_path=tailored_path)
            db.session.add(app_record)
            db.session.flush()

            try:
                success, message = applier.apply(job, tailored_path)
            except Exception as e:
                success = False
                message = f"Apply error: {str(e)[:200]}"

            if success:
                app_record.status = "applied"
                app_record.applied_at = datetime.utcnow()
                app_record.confirmation_text = message
                job.status = "applied"
                summary["jobs_applied"] += 1
                applied_jobs.append(job)
                applications_this_cycle += 1
                logger.info(f"Applied: {job.title} at {job.company}")

                try:
                    sent, email_text = followup.send_followup(job, resume_text)
                    if sent:
                        job.followup_sent = True
                        job.followup_email_text = email_text
                        logger.info(f"Followup sent to {job.hr_email}")
                except Exception as e:
                    logger.error(f"Followup error: {e}")

            else:
                app_record.status = "failed"
                app_record.error_log = message
                job.status = "failed"
                summary["jobs_failed"] += 1
                logger.warning(f"Failed: {job.title} — {message}")

            db.session.commit()

        except Exception as e:
            logger.error(f"Error on job {job.id}: {e}")
            summary["jobs_failed"] += 1
            try:
                db.session.rollback()
            except Exception:
                pass
            continue

    if applied_jobs:
        try:
            Notifier(user).send_summary(applied_jobs, summary)
        except Exception as e:
            logger.error(f"Notification error: {e}")

    user.last_run_at = datetime.utcnow()
    db.session.commit()
    logger.info(f"Cycle done: {summary}")
    return summary