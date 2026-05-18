import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class FollowUpSender:
    def __init__(self, user):
        self.user = user
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    def send_followup(self, job, resume_text):
        if not job.hr_email:
            logger.info(f"No HR email for {job.title}, skipping followup")
            return False, "No HR email found"
        try:
            email_body = self._generate_email(job, resume_text)
            success = self._send_email(job.hr_email, job, email_body)
            if success:
                return True, email_body
            return False, "Email sending failed"
        except Exception as e:
            logger.error(f"Followup error: {e}")
            return False, str(e)

    def _generate_email(self, job, resume_text):
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                system="You are a professional job applicant writing a follow up email to HR after submitting a job application. Write naturally and professionally. Use the actual name provided, no placeholders.",
                messages=[{
                    "role": "user",
                    "content": f"""Write a short professional follow up email.

MY NAME: {self.user.full_name}
MY EMAIL: {self.user.email}
MY PHONE: {self.user.phone}
MY LINKEDIN: {self.user.linkedin_url}
JOB TITLE: {job.title}
COMPANY: {job.company}
HR NAME: {job.hr_name if job.hr_name else "Hiring Manager"}
MY RESUME SUMMARY: {resume_text[:1000]}
JOB DESCRIPTION: {job.description[:800]}

Write 3 short paragraphs:
1. Say I just applied and am very excited about the role
2. Mention 2 specific skills from my resume that match this job
3. Thank them and invite them to reach out

Keep it under 200 words. Sound human and genuine."""
                }]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Email generation error: {e}")
            return f"Dear Hiring Manager,\n\nI recently applied for the {job.title} position at {job.company} and wanted to follow up to express my strong interest.\n\nMy background in AI and data analysis aligns well with this role and I would love to contribute to your team.\n\nThank you for your consideration.\n\nBest regards,\n{self.user.full_name}\n{self.user.email}"

    def _send_email(self, to_email, job, body):
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")
        if not smtp_user or not smtp_pass:
            logger.warning("SMTP not configured, cannot send followup")
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Follow Up — {job.title} Application — {self.user.full_name}"
            msg["From"] = smtp_user
            msg["To"] = to_email
            html = f"<html><body style='font-family:Arial,sans-serif;padding:20px;max-width:600px;'><p>{body.replace(chr(10), '<br>')}</p><br><p style='color:#6b7280;font-size:12px;'>{self.user.full_name}<br>{self.user.email}<br>{self.user.phone}<br>{self.user.linkedin_url}</p></body></html>"
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, msg.as_string())
            logger.info(f"Followup sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False