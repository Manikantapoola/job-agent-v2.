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
        scrapers = [
            self._scrape_remoteok,
            self._scrape_arbeitnow,
            self._scrape_jobicy,
            self._scrape_remotive,
            self._scrape_himalayas,
            self._scrape_ziprecruiter,
            self._scrape_wellfound,
            self._scrape_themuse,
            self._scrape_adzuna,
        ]
        for fn in scrapers:
            try:
                jobs = fn()
                all_jobs.extend(jobs)
                logger.info(f"{fn.__name__}: {len(jobs)} jobs found")
                time.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.error(f"{fn.__name__} failed, skipping: {e}")
        return all_jobs

    def _scrape_remoteok(self):
        jobs = []
        try:
            resp = self.session.get("https://remoteok.com/api", timeout=15)
            data = resp.json()
            keywords = ["ai", "ml", "machine learning", "data", "nlp", "llm", "analyst", "product manager"]
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

    def _scrape_arbeitnow(self):
        jobs = []
        try:
            url = "https://www.arbeitnow.com/api/job-board-api?page=1"
            resp = self.session.get(url, timeout=15)
            data = resp.json()
            keywords = ["ai", "ml", "machine learning", "data", "analyst", "nlp", "llm", "product manager"]
            for item in data.get("data", [])[:40]:
                title = item.get("title", "").lower()
                tags = [t.lower() for t in item.get("tags", [])]
                desc = item.get("description", "")
                if any(k in title or k in tags for k in keywords):
                    jobs.append({
                        "title": item.get("title", ""),
                        "company": item.get("company_name", "Unknown"),
                        "location": item.get("location", "Remote"),
                        "description": desc,
                        "url": item.get("url", ""),
                        "source": "arbeitnow",
                    })
        except Exception as e:
            logger.error(f"Arbeitnow error: {e}")
        return jobs

    def _scrape_jobicy(self):
        jobs = []
        try:
            for industry in ["data-science", "product"]:
                url = f"https://jobicy.com/api/v2/remote-jobs?count=20&industry={industry}"
                resp = self.session.get(url, timeout=15)
                data = resp.json()
                for item in data.get("jobs", []):
                    jobs.append({
                        "title": item.get("jobTitle", ""),
                        "company": item.get("companyName", "Unknown"),
                        "location": "Remote",
                        "description": item.get("jobDescription", ""),
                        "url": item.get("url", ""),
                        "source": "jobicy",
                    })
                time.sleep(1)
        except Exception as e:
            logger.error(f"Jobicy error: {e}")
        return jobs

    def _scrape_remotive(self):
        jobs = []
        try:
            for category in ["data", "product"]:
                url = f"https://remotive.com/api/remote-jobs?category={category}&limit=20"
                resp = self.session.get(url, timeout=15)
                data = resp.json()
                for item in data.get("jobs", []):
                    jobs.append({
                        "title": item.get("title", ""),
                        "company": item.get("company_name", "Unknown"),
                        "location": "Remote",
                        "description": item.get("description", ""),
                        "url": item.get("url", ""),
                        "source": "remotive",
                    })
                time.sleep(1)
        except Exception as e:
            logger.error(f"Remotive error: {e}")
        return jobs

    def _scrape_himalayas(self):
        jobs = []
        try:
            keywords = ["ai", "data", "machine learning", "analyst", "product manager"]
            for kw in keywords[:3]:
                url = f"https://himalayas.app/jobs/api?q={quote_plus(kw)}&limit=15"
                resp = self.session.get(url, timeout=15)
                data = resp.json()
                for item in data.get("jobs", []):
                    jobs.append({
                        "title": item.get("title", ""),
                        "company": item.get("company", {}).get("name", "Unknown"),
                        "location": "Remote",
                        "description": item.get("description", ""),
                        "url": item.get("applicationLink", item.get("url", "")),
                        "source": "himalayas",
                    })
                time.sleep(1)
        except Exception as e:
            logger.error(f"Himalayas error: {e}")
        return jobs

    def _scrape_ziprecruiter(self):
        jobs = []
        try:
            for role in self.roles[:2]:
                query = quote_plus(role)
                url = f"https://api.ziprecruiter.com/jobs/v1?search={query}&location=USA&jobs_per_page=20&page=1"
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("jobs", []):
                        jobs.append({
                            "title": item.get("name", ""),
                            "company": item.get("hiring_company", {}).get("name", "Unknown"),
                            "location": item.get("location", "USA"),
                            "description": item.get("snippet", ""),
                            "url": item.get("job_url", ""),
                            "source": "ziprecruiter",
                        })
                time.sleep(1)
        except Exception as e:
            logger.error(f"ZipRecruiter error: {e}")
        return jobs

    def _scrape_wellfound(self):
        jobs = []
        try:
            keywords = ["machine-learning", "data-science", "artificial-intelligence"]
            for kw in keywords:
                url = f"https://wellfound.com/role/r/{kw}"
                resp = self.session.get(url, timeout=15)
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("a[href*='/jobs/']")
                for card in cards[:8]:
                    href = card.get("href", "")
                    full_url = f"https://wellfound.com{href}" if href.startswith("/") else href
                    title_el = card.select_one("h2, h3, span")
                    jobs.append({
                        "title": title_el.get_text(strip=True) if title_el else "AI Role",
                        "company": "Startup",
                        "location": "Remote",
                        "description": "",
                        "url": full_url,
                        "source": "wellfound",
                    })
                time.sleep(2)
        except Exception as e:
            logger.error(f"Wellfound error: {e}")
        return jobs

    def _scrape_themuse(self):
        jobs = []
        try:
            keywords = ["data analyst", "machine learning", "ai engineer", "product manager"]
            for kw in keywords[:2]:
                url = f"https://www.themuse.com/api/public/jobs?category=Data+Science&level=Entry+Level&page=1"
                resp = self.session.get(url, timeout=15)
                data = resp.json()
                for item in data.get("results", [])[:10]:
                    jobs.append({
                        "title": item.get("name", ""),
                        "company": item.get("company", {}).get("name", "Unknown"),
                        "location": "USA",
                        "description": item.get("contents", ""),
                        "url": item.get("refs", {}).get("landing_page", ""),
                        "source": "themuse",
                    })
                time.sleep(1)
        except Exception as e:
            logger.error(f"The Muse error: {e}")
        return jobs

    def _scrape_adzuna(self):
        jobs = []
        try:
            app_id = "test"
            app_key = "test"
            for role in self.roles[:2]:
                query = quote_plus(role)
                url = f"https://api.adzuna.com/v1/api/jobs/us/search/1?app_id={app_id}&app_key={app_key}&results_per_page=20&what={query}&content-type=application/json"
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        jobs.append({
                            "title": item.get("title", ""),
                            "company": item.get("company", {}).get("display_name", "Unknown"),
                            "location": item.get("location", {}).get("display_name", "USA"),
                            "description": item.get("description", ""),
                            "url": item.get("redirect_url", ""),
                            "source": "adzuna",
                        })
                time.sleep(1)
        except Exception as e:
            logger.error(f"Adzuna error: {e}")
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