from datetime import datetime

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    city: str | None = None
    max_pages: int = Field(default=5, ge=1, le=20)


class SnapshotOut(BaseModel):
    salary_from: int | None
    salary_to: int | None
    currency: str | None
    fetched_at: datetime

    model_config = {"from_attributes": True}


class VacancyOut(BaseModel):
    id: int
    source: str
    external_id: str
    title: str
    location: str | None
    url: str | None
    first_seen: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


class VacancyWithSnapshot(VacancyOut):
    latest: SnapshotOut | None = None


class SessionOut(BaseModel):
    id: int
    source: str
    query: str
    city: str | None
    count: int
    fetched_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailOut(SessionOut):
    vacancies: list[VacancyWithSnapshot] = []
