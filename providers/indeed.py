import time
import urllib.parse
from typing import List, Optional
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from models.job import Job
from providers.base import Provider


class IndeedProvider(Provider):
    BASE_URL = "https://www.indeed.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    @property
    def name(self) -> str:
        return "indeed"

    def search(
        self, keyword: str, location: str, max_results: int = 30
    ) -> List[Job]:
        jobs: List[Job] = []
        seen_urls: set = set()
        start = 0
        limit = 10

        while len(jobs) < max_results:
            params = urllib.parse.urlencode({
                "q": keyword,
                "l": location,
                "start": start,
                "limit": limit,
            })
            url = f"{self.BASE_URL}/jobs?{params}"

            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"  [!] Error fetching Indeed page {start // limit + 1}: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            page_jobs = self._parse_jobs(soup, seen_urls)

            if not page_jobs:
                break

            jobs.extend(page_jobs)
            start += limit

            time.sleep(1.5)

        return jobs[:max_results]

    def _parse_jobs(self, soup: BeautifulSoup, seen_urls: set) -> List[Job]:
        jobs: List[Job] = []
        cards = self._find_job_cards(soup)

        for card in cards:
            job = self._extract_job(card)
            if job and job.url not in seen_urls:
                seen_urls.add(job.url)
                jobs.append(job)

        return jobs

    def _find_job_cards(self, soup: BeautifulSoup) -> list:
        cards = []

        for selector in [
            '[data-testid="job-card"]',
            ".job_seen_beacon",
            ".job_card",
            ".jobsearch-JobCard",
            ".card.tapItem",
            ".result",
            'div[id^="job_"]',
            "li.css-5lfm1z",
            "li[data-testid]",  # very general but last resort
        ]:
            cards = soup.select(selector)
            if cards:
                break

        if not cards:
            cards = soup.find_all("div", class_=lambda c: c and "job" in c.lower())

        return cards

    def _extract_job(self, card) -> Optional[Job]:
        try:
            title = self._extract_text(card, [
                '[data-testid="job-card-title"]',
                "h2.jobTitle a",
                "h2.jobTitle span",
                ".jobTitle",
                '[id^="jobTitle"]',
                "a[data-jk]",
                "h2 a",
                ".title a",
                ".jobtitle",
                '[data-testid*="title"]',
                "span[title]",
            ])

            if not title:
                return None

            url = self._extract_url(card)
            if not url:
                return None

            company = self._extract_text(card, [
                '[data-testid="job-card-company"]',
                '[data-testid*="company"]',
                ".companyName",
                ".company",
                '[class*="company"]',
                "span[data-company-name]",
            ]) or ""

            location = self._extract_text(card, [
                '[data-testid="job-card-location"]',
                '[data-testid*="location"]',
                ".companyLocation",
                '[class*="location"]',
                ".location",
            ]) or ""

            snippet = self._extract_text(card, [
                ".job-snippet",
                ".summary",
                '[class*="summary"]',
                '[class*="snippet"]',
            ]) or ""

            salary = self._extract_text(card, [
                '[data-testid="job-card-salary"]',
                '[data-testid*="salary"]',
                ".salary-snippet",
                '[class*="salary"]',
                ".metadata.salary",
            ]) or ""

            date_raw = self._extract_text(card, [
                '[data-testid="job-card-date"]',
                '[data-testid*="date"]',
                ".date",
                '[class*="date"]',
                ".result-link-bar span",
            ]) or ""

            return Job(
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                url=url,
                source="indeed",
                snippet=snippet.strip()[:300],
                salary=salary.strip(),
                date_posted=date_raw.strip(),
            )
        except Exception:
            return None

    def _extract_text(self, card, selectors: list) -> str:
        for selector in selectors:
            elem = card.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        return ""

    def _extract_url(self, card) -> Optional[str]:
        for selector in [
            "h2.jobTitle a",
            "a[data-jk]",
            "a.jobtitle",
            "a.title",
            "a[href*='jk=']",
            "a[href*='?jk=']",
            "a[href*='/rc/clk']",
            "a[href*='viewjob']",
            "a",
        ]:
            link = card.select_one(selector)
            if link and link.get("href"):
                href = link["href"]
                if href.startswith("http"):
                    return href
                return f"{self.BASE_URL}{href}"
        return None
