# 🤖 Job Apply AI Agent

An autonomous AI agent that applies to jobs automatically every 3 hours without any manual input.

## What It Does

- Scrapes LinkedIn, Indeed, Glassdoor, RemoteOK, and Wellfound every 3 hours
- Uses Claude AI to score each job against my resume (only applies to 50%+ matches)
- Rewrites my resume using AI for each specific job
- Injects hidden ATS text to boost keyword match scores
- Uses Playwright browser automation to fill and submit applications
- Scrapes HR contact information from job pages
- Sends personalized follow up emails to HR using Claude AI
- Live dashboard showing every application with match score, resume preview, and HR contact

## Tech Stack

- Python, Flask, SQLAlchemy, SQLite
- Anthropic Claude API
- Playwright (browser automation)
- APScheduler (3-hour cycles)
- BeautifulSoup (web scraping)
- python-docx, pdfplumber (resume handling)

## Live Demo

Available on request. Contact me at manikantapoola.pm@email.com

## How To Run Locally

1. Clone the repo
2. Create virtual environment and activate it
3. Run pip install -r requirements.txt
4. Run playwright install chromium
5. Create .env file with your API keys
6. Run python app.py
7. Open [http://localhost:5000](http://localhost:5000/onboarding)
