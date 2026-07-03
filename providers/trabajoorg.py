from typing import List

import requests
from bs4 import BeautifulSoup

from models.job import Job
from providers.base import Provider


class TrabajoOrgProvider(Provider):
    BASE_URL = "https://mx.trabajo.org"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    BROAD_QUERY = "sistemas+informatica+tecnologia+infraestructura+devops+linux"

    def __init__(self):
        self._all_jobs: List[Job] = []
        self._loaded = False

    @property
    def name(self) -> str:
        return "trabajoorg"

    def search(
        self, keyword: str, location: str, max_results: int = 30
    ) -> List[Job]:
        if not self._loaded:
            self._all_jobs = self._fetch_all()
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

    def _fetch_all(self) -> List[Job]:
        url = f"{self.BASE_URL}/jobs?q={self.BROAD_QUERY}"

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []
        seen: set = set()

        for card in soup.select("li.nf-job"):
            title_link = card.select_one("h3 a")
            if not title_link:
                continue

            title = title_link.get_text(strip=True)
            href = title_link.get("href", "")
            full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            if full_url in seen:
                continue
            seen.add(full_url)

            company_el = card.select_one("span i.lnr-briefcase")
            company = ""
            if company_el:
                company = company_el.parent.get_text(strip=True)
            if not company:
                img = card.select_one("img.img-logo")
                company = img.get("alt", "") if img else ""

            location_el = card.select_one("span i.lnr-map-marker")
            location = location_el.parent.get_text(strip=True) if location_el else "Mexico"

            date_el = card.select_one("p.text-muted small")
            date_raw = date_el.get_text(strip=True) if date_el else ""

            text = card.get_text().lower()
            is_remote = any(
                w in text
                for w in ["remoto", "home office", "homeoffice", "desde casa"]
            )

            jobs.append(Job(
                title=title,
                company=company,
                location=location,
                url=full_url,
                source="trabajoorg",
                date_posted=date_raw,
                remote=is_remote,
            ))

        return jobs
