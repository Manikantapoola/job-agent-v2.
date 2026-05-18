import os
import logging

logger = logging.getLogger(__name__)

class JobApplier:
    def __init__(self, user):
        self.user = user

    def apply(self, job, resume_path):
        url = job.url or ""
        source = job.source or ""
        if "linkedin.com" in url or source == "linkedin":
            return self._apply_linkedin(job, resume_path)
        else:
            return self._apply_generic(job, resume_path)

    def _apply_linkedin(self, job, resume_path):
        try:
            from playwright.sync_api import sync_playwright
            email = os.environ.get("LINKEDIN_EMAIL", "")
            password = os.environ.get("LINKEDIN_PASSWORD", "")
            if not email or not password:
                return False, "LinkedIn credentials not set in .env"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://www.linkedin.com/login", timeout=30000)
                page.fill("#username", email)
                page.fill("#password", password)
                page.click("button[type=submit]")
                page.wait_for_load_state("networkidle", timeout=15000)
                page.goto(job.url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)
                easy_apply = page.locator("button:has-text('Easy Apply')").first
                if not easy_apply.is_visible(timeout=5000):
                    browser.close()
                    return False, "No Easy Apply button found"
                easy_apply.click()
                page.wait_for_timeout(2000)
                phone = page.locator("input[id*='phone'], input[name*='phone']").first
                if phone.is_visible(timeout=2000):
                    phone.fill(self.user.phone or "")
                file_input = page.locator("input[type='file']").first
                if file_input.is_visible(timeout=3000):
                    file_input.set_input_files(resume_path)
                for _ in range(8):
                    next_btn = page.locator("button:has-text('Next'), button:has-text('Submit application'), button:has-text('Review')").last
                    if not next_btn.is_visible(timeout=3000):
                        break
                    text = next_btn.inner_text()
                    next_btn.click()
                    page.wait_for_timeout(1500)
                    if "Submit" in text:
                        browser.close()
                        return True, "Applied via LinkedIn Easy Apply"
                browser.close()
                return False, "Could not complete LinkedIn flow"
        except Exception as e:
            return False, f"LinkedIn error: {str(e)[:200]}"

    def _apply_generic(self, job, resume_path):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(job.url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)
                for selector in ["button:has-text('Apply Now')", "button:has-text('Apply')", "a:has-text('Apply Now')"]:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        page.wait_for_load_state("networkidle", timeout=8000)
                        break
                self._fill_fields(page, resume_path)
                browser.close()
                return True, "Applied via generic flow"
        except Exception as e:
            return False, f"Generic error: {str(e)[:200]}"

    def _fill_fields(self, page, resume_path):
        fields = {
            "input[name*='first']": self.user.full_name.split()[0] if self.user.full_name else "",
            "input[name*='last']": self.user.full_name.split()[-1] if self.user.full_name else "",
            "input[type='email']": self.user.email or "",
            "input[type='tel']": self.user.phone or "",
            "input[name*='linkedin']": self.user.linkedin_url or "",
            "input[name*='github']": self.user.github_url or "",
        }
        for selector, value in fields.items():
            if not value:
                continue
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1500):
                    el.fill(value)
            except Exception:
                pass
        if resume_path and os.path.exists(resume_path):
            try:
                file_input = page.locator("input[type='file']").first
                if file_input.is_visible(timeout=3000):
                    file_input.set_input_files(resume_path)
            except Exception:
                pass