from abc import ABC, abstractmethod
from typing import List

from models.job import Job


class Provider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def search(self, keyword: str, location: str, max_results: int) -> List[Job]:
        pass
