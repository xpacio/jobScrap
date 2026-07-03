import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from models.job import Job
from providers.base import Provider


class ComputrabajoProvider(Provider):
    BASE_URL = "https://mx.computrabajo.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    KEYWORDS = [
        "sistemas", "informatica", "tecnologia", "infraestructura",
        "devops", "linux", "soporte", "programador",
    ]

    def __init__(self):
        self._all_jobs: List[Job] = []
        self._loaded = False

    @property
    def name(self) -> str:
        return "computrabajo"

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
        seen: Dict[str, Job] = {}

        for kw in self.KEYWORDS:
            url = f"{self.BASE_URL}/trabajo-de-{kw}"
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                resp.raise_for_status()
            except requests.RequestException:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            for article in soup.find_all(
                "article", class_=lambda c: c and "box_offer" in str(c)
            ):
                title_link = article.select_one("h2 a")
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                href = title_link.get("href", "")
                full_url = (
                    f"{self.BASE_URL}{href}" if href.startswith("/") else href
                )
                full_url = full_url.split("#")[0]

                if full_url in seen:
                    continue

                company_el = article.select_one(
                    "a[offer-grid-article-company-url]"
                ) or article.select_one("p.dFlex a.fc_base")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_ps = article.select("p.fs16.fc_base.mt5")
                location = "Mexico"
                for lp in loc_ps:
                    if "dFlex" not in (lp.get("class") or []):
                        span = lp.select_one("span.mr10")
                        if span:
                            location = span.get_text(strip=True)
                            break

                date_el = article.select_one("p.fs13.fc_aux.mt15")
                date_raw = date_el.get_text(strip=True) if date_el else ""

                salary_el = article.select_one("div.fs13.mt15 span.dIB.mr10")
                salary = salary_el.get_text(strip=True) if salary_el else ""

                text = article.get_text().lower()
                is_remote = any(
                    w in text
                    for w in [
                        "remoto", "home office", "homeoffice",
                        "desde casa", "100% remoto", "trabajo remoto", "remota",
                    ]
                )
                is_hibrido = any(w in text for w in ["hibrido", "híbrido", "mixto"])

                seen[full_url] = Job(
                    title=title,
                    company=company,
                    location=location,
                    url=full_url,
                    source="computrabajo",
                    salary=salary,
                    date_posted=date_raw,
                    remote=is_remote or is_hibrido,
                )

        return list(seen.values())
