import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, user):
        self.user = user

    def send_summary(self, applied_jobs, summary):
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")
        if not smtp_user or not smtp_pass:
            logger.warning("SMTP not configured, skipping email")
            return
        try:
            rows = ""
            for job in applied_jobs:
                rows += f"<tr><td>{job.title}</td><td>{job.company}</td><td>{job.match_score:.0f}%</td><td><a href='{job.url}'>View</a></td></tr>"
            html = f"""<html><body style="font-family:Arial,sans-serif;padding:20px;">
<h2 style="color:#1e40af;">Job Agent Report — {datetime.utcnow().strftime('%b %d, %Y')}</h2>
<p>Applied to <strong>{summary['jobs_applied']}</strong> jobs. Scanned {summary['jobs_found']} total.</p>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%;">
<tr style="background:#f3f4f6;"><th>Role</th><th>Company</th><th>Match</th><th>Link</th></tr>
{rows}
</table>
<p style="color:#6b7280;font-size:12px;">Next cycle in approximately 3 hours.</p>
</body></html>"""
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Job Agent Applied to {summary['jobs_applied']} Jobs"
            msg["From"] = smtp_user
            msg["To"] = self.user.notify_email or self.user.email
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, self.user.notify_email or self.user.email, msg.as_string())
            logger.info("Summary email sent")
        except Exception as e:
            logger.error(f"Email error: {e}")