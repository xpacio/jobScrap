from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from models.job import Job
from providers.base import Provider


class WeWorkRemotelyProvider(Provider):
    BASE_URL = "https://weworkremotely.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    CATEGORIES = [
        "remote-devops-sysadmin-jobs",
        "remote-back-end-programming-jobs",
        "remote-full-stack-programming-jobs",
        "remote-system-administrator-jobs",
    ]

    def __init__(self):
        self._all_jobs: List[Job] = []
        self._loaded = False

    @property
    def name(self) -> str:
        return "weworkremotely"

    def search(
        self, keyword: str, location: str, max_results: int = 30
    ) -> List[Job]:
        if not self._loaded:
            self._all_jobs = self._fetch_all_categories()
            self._loaded = True

        kw_lower = keyword.lower()
        words = [w for w in kw_lower.split() if len(w) > 2]
        matched = []
        for job in self._all_jobs:
            if len(matched) >= max_results:
                break
            searchable = f"{job.title} {job.company}".lower()
            if kw_lower in searchable or any(w in searchable for w in words):
                matched.append(job)

        return matched

    def _fetch_all_categories(self) -> List[Job]:
        seen: Dict[str, Job] = {}

        for category in self.CATEGORIES:
            url = f"{self.BASE_URL}/categories/{category}"
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                resp.raise_for_status()
            except requests.RequestException:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.select('a[href*="/remote-jobs/"]'):
                href = link.get("href", "")
                if "find-your-plan" in href or not href:
                    continue

                title_el = link.select_one(".new-listing__header__title__text")
                if not title_el:
                    title_el = link.select_one("h3.new-listing__header__title")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                full_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href

                if full_url in seen:
                    continue

                company = (
                    link.select_one(".new-listing__company-name")
                )
                company = company.get_text(strip=True) if company else ""

                date_raw = (
                    link.select_one(".new-listing__header__icons__date")
                )
                date_raw = date_raw.get_text(strip=True) if date_raw else ""

                cat_els = link.select(".new-listing__categories__category")
                cat_texts = [c.get_text(strip=True) for c in cat_els]
                location = "Remote"
                for ct in cat_texts:
                    if "Anywhere" in ct or "World" in ct or "Remote" in ct:
                        location = ct
                    elif ct in ("Full-Time", "Part-Time", "Contract", "Freelance", "Featured"):
                        continue
                    elif "Anywhere" not in location and "Remote" not in location:
                        location = ct

                seen[full_url] = Job(
                    title=title,
                    company=company,
                    location=location,
                    url=full_url,
                    source="wwr",
                    snippet=" | ".join(cat_texts[:4]),
                    date_posted=date_raw,
                )

        return list(seen.values())
