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

    @property
    def name(self) -> str:
        return "trabajoorg"

    def search(
        self, keyword: str, location: str, max_results: int = 30
    ) -> List[Job]:
        kw = keyword.replace(" ", "+")
        url = f"{self.BASE_URL}/jobs?q={kw}"

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [!] Error fetching Trabajo.org: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs: List[Job] = []
        seen: set = set()

        for card in soup.select("li.nf-job"):
            if len(jobs) >= max_results:
                break

            title_link = card.select_one("h3 a")
            if not title_link:
                continue

            title = title_link.get_text(strip=True)
            href = title_link.get("href", "")
            full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            if full_url in seen:
                continue
            seen.add(full_url)

            company_el = card.select_one(
                'span i.lnr-briefcase'
            )
            company = ""
            if company_el:
                company = company_el.parent.get_text(strip=True)
            if not company:
                img = card.select_one("img.img-logo")
                company = img.get("alt", "") if img else ""

            location_el = card.select_one(
                'span i.lnr-map-marker'
            )
            location = location_el.parent.get_text(strip=True) if location_el else "México"

            date_el = card.select_one("p.text-muted small")
            date_raw = date_el.get_text(strip=True) if date_el else ""

            text = card.get_text().lower()
            is_remote = any(
                w in text
                for w in ["remoto", "home office", "homeoffice", "desde casa"]
            )

            jobs.append(
                Job(
                    title=title,
                    company=company,
                    location=location,
                    url=full_url,
                    source="trabajoorg",
                    date_posted=date_raw,
                    remote=is_remote,
                )
            )

        return jobs
