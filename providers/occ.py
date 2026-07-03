import re
from typing import List

from playwright.sync_api import sync_playwright

from models.job import Job
from providers.base import Provider


class OCCProvider(Provider):
    BASE_URL = "https://www.occ.com.mx/empleos/trabajo-en-tecnologias-de-la-informacion-sistemas/"

    _BROWSER = None

    def __init__(self):
        self._all_jobs: List[Job] = []
        self._loaded = False

    @property
    def name(self) -> str:
        return "occ"

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
        jobs: List[Job] = []
        seen: set = set()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox"],
                )
                ctx = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                    locale="es-MX",
                )
                page = ctx.new_page()
                page.goto(self.BASE_URL, timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                cards = page.query_selector_all("div.card-job-offer")
                for card in cards:
                    j = self._extract_job(card)
                    if j and j.url not in seen:
                        seen.add(j.url)
                        jobs.append(j)

                browser.close()
        except Exception as e:
            print(f"  [!] Error en OCC: {e}")

        return jobs

    def _extract_job(self, card) -> Job | None:
        data_id = card.get_attribute("data-id") or ""
        if not data_id:
            return None

        url = f"https://www.occ.com.mx/empleos/{data_id}/"
        text = card.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) < 4:
            return None

        date_raw = lines[0]

        salary = ""
        salary_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("$") or "Sueldo" in line or "no mostrado" in line:
                salary = line
                salary_idx = i
                break

        title = ""
        if salary_idx >= 2:
            title = lines[salary_idx - 1]
        elif salary_idx == 1 and len(lines) > 2:
            title = lines[1]
        if not title:
            for line in lines[1:]:
                if not any(
                    b in line
                    for b in ["Recomendada", "Vista", "Ya estás", "postulado"]
                ):
                    title = line
                    break

        location = lines[-1]
        company = ""
        if len(lines) >= 2:
            company = lines[-2]
            benefit_indicators = [
                "Prestaciones", "prestaciones", "Seguro", "Plan de",
                "Capacitación", "Excelente", "Vales", "Fondo",
            ]
            while company and any(b in company for b in benefit_indicators):
                lines = lines[:-1]
                if len(lines) >= 2:
                    company = lines[-2]
                else:
                    company = ""
                    break

        text_lower = text.lower()
        is_remote = any(
            w in text_lower
            for w in ["híbrido", "hibrido", "desde casa", "home office", "remoto"]
        )

        is_hibrido = any(w in text_lower for w in ["híbrido", "hibrido"])

        return Job(
            title=title,
            company=company,
            location=location,
            url=url,
            source="occ",
            salary=salary,
            date_posted=date_raw,
            remote=is_remote or is_hibrido,
        )
