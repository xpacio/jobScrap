from dataclasses import dataclass, field
from typing import List


@dataclass
class SearchConfig:
    keywords: List[str] = field(default_factory=lambda: [
        "Linux administrator",
        "SysAdmin",
        "System Administrator",
        "Infrastructure Engineer",
        "DevOps",
        "PostgreSQL DBA",
        "Administrador de sistemas",
        "Bash scripting Linux",
        "Azure administration",
        "Coordinador de infraestructura",
    ])
    location: str = "remote"
    max_results_per_keyword: int = 30
    days_back: int = 14


@dataclass
class AppConfig:
    search: SearchConfig = field(default_factory=SearchConfig)
    providers: List[str] = field(default_factory=lambda: ["remoteok", "weworkremotely", "computrabajo", "trabajoorg"])
    db_path: str = "jobs.db"
