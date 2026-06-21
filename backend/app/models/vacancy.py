from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class FetchSession(Base):
    __tablename__ = "fetch_sessions"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)       # "hh" | "sj"
    query = Column(String, nullable=False)
    city = Column(String, nullable=True)
    count = Column(Integer, nullable=False, default=0)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    snapshots = relationship("VacancySnapshot", back_populates="session")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    location = Column(String, nullable=True)
    url = Column(String, nullable=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_vacancy_source_ext"),
    )

    snapshots = relationship("VacancySnapshot", back_populates="vacancy")


class VacancySnapshot(Base):
    __tablename__ = "vacancy_snapshots"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("fetch_sessions.id"), nullable=False)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=False)
    salary_from = Column(Integer, nullable=True)
    salary_to = Column(Integer, nullable=True)
    currency = Column(String, nullable=True)

    session = relationship("FetchSession", back_populates="snapshots")
    vacancy = relationship("Vacancy", back_populates="snapshots")
