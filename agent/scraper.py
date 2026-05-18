import logging
import time
import random
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

class JobScraper:
    def __init__(self, user):
        self.user = user
        self.roles = user.target_roles_list()
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def scrape_all(self):
        all_jobs = []
        for fn in [self._scrape_remoteok, self._scrape_indeed]:
            try:
                jobs = fn()
                all_jobs.extend(jobs)
                logger.info(f"{fn.__name__}: {len(jobs)} jobs found")
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                logger.error(f"{fn.__name__} failed: {e}")
        return all_jobs

    def _scrape_remoteok(self):
        jobs = []
        try:
            resp = self.session.get("https://remoteok.com/api", timeout=15)
            data = resp.json()
            keywords = ["ai", "ml", "machine learning", "data", "nlp", "llm", "analyst"]
            for item in data[1:]:
                if not isinstance(item, dict):
                    continue
                tags = [t.lower() for t in item.get("tags", [])]
                title = item.get("position", "").lower()
                if any(k in tags or k in title for k in keywords):
                    jobs.append({
                        "title": item.get("position", ""),
                        "company": item.get("company", "Unknown"),
                        "location": "Remote",
                        "description": item.get("description", ""),
                        "url": item.get("url", ""),
                        "source": "remoteok",
                    })
                if len(jobs) >= 20:
                    break
        except Exception as e:
            logger.error(f"RemoteOK error: {e}")
        return jobs

    def _scrape_indeed(self):
        jobs = []
        for role in self.roles[:2]:
            try:
                query = quote_plus(f"{role} entry level remote")
                url = f"https://www.indeed.com/jobs?q={query}&l=Remote&limit=10"
                resp = self.session.get(url, timeout=15)
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("div.job_seen_beacon")
                for card in cards[:8]:
                    title_el = card.select_one("h2.jobTitle")
                    company_el = card.select_one(".companyName")
                    link_el = card.select_one("h2.jobTitle a")
                    if not title_el:
                        continue
                    href = link_el.get("href", "") if link_el else ""
                    job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href
                    jobs.append({
                        "title": title_el.get_text(strip=True),
                        "company": company_el.get_text(strip=True) if company_el else "Unknown",
                        "location": "Remote",
                        "description": "",
                        "url": job_url,
                        "source": "indeed",
                    })
                time.sleep(random.uniform(2, 3))
            except Exception as e:
                logger.error(f"Indeed error for {role}: {e}")
        return jobs

    def scrape_hr_contact(self, job_url):
        hr_name = ""
        hr_email = ""
        hr_title = ""
        try:
            resp = self.session.get(job_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)

            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if email_match:
                hr_email = email_match.group(0)

            hr_keywords = ["hiring manager", "recruiter", "talent acquisition", "hr manager", "posted by", "contact"]
            lines = text.split(".")
            for line in lines:
                line_lower = line.lower()
                if any(k in line_lower for k in hr_keywords):
                    words = line.strip().split()
                    for i, word in enumerate(words):
                        if any(k in word.lower() for k in ["recruiter", "manager", "hiring"]):
                            if i + 2 < len(words):
                                possible_name = words[i+1] + " " + words[i+2]
                                if possible_name[0].isupper():
                                    hr_name = possible_name
                                    break

            title_keywords = ["recruiter", "hiring manager", "talent", "hr", "people ops"]
            for kw in title_keywords:
                if kw in text.lower():
                    hr_title = kw.title()
                    break

        except Exception as e:
            logger.error(f"HR scrape error: {e}")

        return hr_name, hr_email, hr_title