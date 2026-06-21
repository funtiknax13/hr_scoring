from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VacancyRow:
    external_id: str
    title: str
    salary_from: int | None
    salary_to: int | None
    currency: str | None
    location: str
    url: str | None


class BaseSource(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, city: str | None, max_pages: int) -> list[VacancyRow]:
        """Ищет вакансии и возвращает унифицированный список."""
        ...
