import os
import json
import logging
from datetime import datetime
from anthropic import Anthropic
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

class ResumeTailor:
    def __init__(self, user):
        self.user = user
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        os.makedirs("resumes\\tailored", exist_ok=True)

    def tailor(self, job):
        sections = self._get_tailored_content(job)
        return self._build_docx(job, sections)

    def _get_tailored_content(self, job):
        resume_text = self._read_resume()
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system="You are an expert resume writer. Respond ONLY with valid JSON, no markdown.",
                messages=[{
                    "role": "user",
                    "content": f"""Tailor this resume for the job below.

RESUME: {resume_text[:2500]}
JOB TITLE: {job.title}
COMPANY: {job.company}
JOB DESCRIPTION: {job.description[:2000]}

Respond ONLY with this JSON:
{{
  "summary": "<2-3 sentence summary tailored to this job>",
  "skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "experience": [{{"title": "<role>", "company": "<company>", "duration": "<duration>", "bullets": ["<bullet1>", "<bullet2>"]}}],
  "education": [{{"degree": "<degree>", "school": "<school>", "year": "<year>"}}],
  "projects": [{{"name": "<project>", "description": "<1-2 sentences>"}}]
}}"""
                }]
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.error(f"Tailor error: {e}")
            return {
                "summary": f"Motivated {self.user.target_roles} professional.",
                "skills": ["Python", "AI", "ML", "Data Analysis", "SQL"],
                "experience": [], "education": [], "projects": []
            }

    def _build_docx(self, job, sections):
        doc = Document()
        for section in doc.sections:
            section.top_margin = Pt(36)
            section.bottom_margin = Pt(36)
            section.left_margin = Pt(54)
            section.right_margin = Pt(54)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(self.user.full_name)
        run.bold = True
        run.font.size = Pt(20)

        contact = " | ".join(filter(None, [self.user.email, self.user.phone, self.user.linkedin_url]))
        p = doc.add_paragraph(contact)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        self._heading(doc, "Professional Summary")
        doc.add_paragraph(sections.get("summary", ""))

        skills = sections.get("skills", [])
        if skills:
            self._heading(doc, "Technical Skills")
            doc.add_paragraph(" | ".join(skills))

        experience = sections.get("experience", [])
        if experience:
            self._heading(doc, "Experience")
            for exp in experience:
                p = doc.add_paragraph()
                run = p.add_run(f"{exp.get('title','')} — {exp.get('company','')}")
                run.bold = True
                doc.add_paragraph(exp.get("duration", ""))
                for b in exp.get("bullets", []):
                    doc.add_paragraph(b, style="List Bullet")

        education = sections.get("education", [])
        if education:
            self._heading(doc, "Education")
            for edu in education:
                p = doc.add_paragraph()
                run = p.add_run(f"{edu.get('degree','')} — {edu.get('school','')} — {edu.get('year','')}")
                run.bold = True

        projects = sections.get("projects", [])
        if projects:
            self._heading(doc, "Projects")
            for proj in projects:
                p = doc.add_paragraph()
                run = p.add_run(proj.get("name", "") + ": ")
                run.bold = True
                p.add_run(proj.get("description", ""))

        if job.description:
            p = doc.add_paragraph()
            run = p.add_run(job.description)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            run.font.size = Pt(1)

        safe = lambda s: "".join(c for c in s if c.isalnum() or c in " _-")[:25].strip()
        filename = f"{safe(job.company)}_{safe(job.title)}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.docx".replace(" ", "_")
        path = os.path.join("resumes\\tailored", filename)
        doc.save(path)
        return path

    def _heading(self, doc, text):
        p = doc.add_paragraph()
        run = p.add_run(text.upper())
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x1a, 0x56, 0xdb)

    def _read_resume(self):
        path = self.user.resume_path
        if not path or not os.path.exists(path):
            return f"Name: {self.user.full_name}, Target: {self.user.target_roles}"
        try:
            if path.endswith(".pdf"):
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            elif path.endswith(".docx"):
                from docx import Document
                d = Document(path)
                return "\n".join(p.text for p in d.paragraphs)
        except Exception as e:
            logger.error(f"Resume read error: {e}")
        return ""