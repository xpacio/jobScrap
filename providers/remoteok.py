import json
from typing import Dict, List, Optional

import requests

from models.job import Job
from providers.base import Provider


class RemoteOKProvider(Provider):
    API_URL = "https://remoteok.com/api"
    BASE_URL = "https://remoteok.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self):
        self._all_jobs_cache: List[Dict] = []
        self._cache_loaded = False

    @property
    def name(self) -> str:
        return "remoteok"

    def search(
        self, keyword: str, location: str, max_results: int = 30
    ) -> List[Job]:
        if not self._cache_loaded:
            self._load_all_jobs()

        kw_lower = keyword.lower()
        words = [w for w in kw_lower.split() if len(w) > 2]
        matched: List[Job] = []

        for raw in self._all_jobs_cache:
            if len(matched) >= max_results:
                break

            title = raw.get("position", "") or ""
            company = raw.get("company", "") or ""
            tags_text = " ".join(raw.get("tags", []) or [])
            searchable = f"{title} {company} {tags_text}".lower()

            if kw_lower in searchable or any(w in searchable for w in words):
                job = self._raw_to_job(raw)
                if job:
                    matched.append(job)

        return matched

    def _load_all_jobs(self):
        try:
            resp = requests.get(self.API_URL, headers=self.HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            self._all_jobs_cache = data[1:] if isinstance(data, list) and len(data) > 1 else []
            self._cache_loaded = True
        except (requests.RequestException, json.JSONDecodeError, IndexError) as e:
            print(f"  [!] Error fetching RemoteOK API: {e}")
            self._all_jobs_cache = []
            self._cache_loaded = True

    def _raw_to_job(self, raw: Dict) -> Optional[Job]:
        try:
            slug = raw.get("slug", "")
            if not slug:
                return None

            title = raw.get("position", "Unknown Position")
            company = raw.get("company", "")
            tags = raw.get("tags", []) or []
            tags_str = ", ".join(tags[:5])
            location = raw.get("location", "Remote") or "Remote"
            epoch = raw.get("epoch", 0)
            date_str = ""
            if epoch:
                import datetime
                dt = datetime.datetime.fromtimestamp(epoch)
                date_str = dt.strftime("%Y-%m-%d")

            salary_min = raw.get("salary_min")
            salary_max = raw.get("salary_max")
            salary = ""
            if salary_min and salary_max:
                salary = f"${salary_min} - ${salary_max}"
            elif salary_min:
                salary = f"${salary_min}+"
            elif salary_max:
                salary = f"hasta ${salary_max}"

            is_remote = "remote" in location.lower() or location.lower() == "anywhere"

            return Job(
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                url=f"{self.BASE_URL}/remote-jobs/{slug}",
                source="remoteok",
                snippet=tags_str,
                salary=salary,
                date_posted=date_str,
                remote=is_remote,
            )
        except Exception:
            return None
