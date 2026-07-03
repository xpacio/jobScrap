import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from models.job import Job
from providers.base import Provider


class HirelineProvider(Provider):
    BASE_URL = "https://hireline.io"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    CATEGORIES = [
        "php", "devops", "sysadmin", "linux", "python",
        "backend", "infraestructura", "sistemas",
    ]

    def __init__(self):
        self._all_jobs: List[Job] = []
        self._loaded = False

    @property
    def name(self) -> str:
        return "hireline"

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
            searchable = f"{job.title} {job.company} {job.snippet}".lower()
            if kw_lower in searchable or any(w in searchable for w in words):
                matched.append(job)
        return matched

    def _fetch_all_categories(self) -> List[Job]:
        seen: Dict[str, Job] = {}

        for cat in self.CATEGORIES:
            url = f"{self.BASE_URL}/mx/empleos-de-{cat}"
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                resp.raise_for_status()
            except requests.RequestException:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            for card in soup.select("a.hl-vacancy-card"):
                href = card.get("href", "")
                if not href or href in seen:
                    continue

                title_el = card.select_one(".vacancy-title")
                if not title_el:
                    continue
                title_text = title_el.get_text(strip=True)

                company = self._extract_company(title_text)
                title = self._clean_title(title_text)

                salary_el = card.select_one(".vacancy-subtitle")
                salary = salary_el.get_text(strip=True) if salary_el else ""

                loc_el = card.select_one(".vacancy-location")
                location = loc_el.get_text(strip=True) if loc_el else ""
                remote = "remoto" in location.lower()

                date_el = card.select_one(".updated-text")
                date_posted = date_el.get_text(strip=True) if date_el else ""

                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                city = ""
                for ft in card.select(".footer-text"):
                    t = ft.get_text(strip=True)
                    if "empleado" in t.lower() or "becario" in t.lower() or "freelance" in t.lower() or "tiempo" in t.lower():
                        continue
                    if t and not any(x in t.lower() for x in ("$", "mxn", "sueldo")):
                        city = t

                location = location or city

                seen[full_url] = Job(
                    title=title,
                    company=company,
                    location=location,
                    url=full_url,
                    source="hireline",
                    snippet="",
                    salary=salary,
                    date_posted=date_posted,
                    remote=remote,
                )

        return list(seen.values())

    def _extract_company(self, title: str) -> str:
        parts = title.rsplit(" en ", 1)
        return parts[1].strip() if len(parts) > 1 else ""

    def _clean_title(self, title: str) -> str:
        title = re.sub(r'\s+en\s+\S+(\s+\S+)?$', '', title)
        return title.strip()
