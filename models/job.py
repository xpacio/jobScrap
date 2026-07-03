from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    snippet: str = ""
    salary: str = ""
    date_posted: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if not isinstance(other, Job):
            return False
        return self.url == other.url
