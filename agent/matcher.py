import os
import json
import logging
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self, user):
        self.user = user
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.resume_text = self._load_resume()

    def _load_resume(self):
        path = self.user.resume_path
        if not path or not os.path.exists(path):
            return f"Name: {self.user.full_name}\nTarget Roles: {self.user.target_roles}\nLevel: {self.user.experience_level}"
        try:
            if path.endswith(".pdf"):
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            elif path.endswith(".docx"):
                from docx import Document
                doc = Document(path)
                return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            logger.error(f"Resume read error: {e}")
        return f"Name: {self.user.full_name}\nTarget: {self.user.target_roles}"

    def compute_match(self, job_description):
        if not job_description.strip():
            return 45.0, "No description available — skipped"
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                system="You are an ATS matching engine. Respond ONLY with valid JSON, no markdown.",
                messages=[{
                    "role": "user",
                    "content": f"""Compare this resume to the job description.

RESUME:
{self.resume_text[:2500]}

JOB DESCRIPTION:
{job_description[:2000]}

Respond ONLY with this JSON:
{{"match_score": <number 0-100>, "match_reason": "<one sentence>"}}"""
                }]
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            return float(data.get("match_score", 50)), data.get("match_reason", "")
        except Exception as e:
            logger.error(f"Match error: {e}")
            return 50.0, "Fallback score"