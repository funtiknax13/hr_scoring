import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class LogStatus(str, enum.Enum):
    running = "running"
    done = "done"
    error = "error"


class ScheduledSearch(Base):
    __tablename__ = "scheduled_searches"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)       # hh / sj
    query = Column(String, nullable=False)
    city = Column(String, nullable=True)
    max_pages = Column(Integer, default=3, nullable=False)
    cron = Column(String, nullable=False)          # напр. "0 9 * * *"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_run_at = Column(DateTime(timezone=True), nullable=True)

    logs = relationship("ScheduledSearchLog", back_populates="search",
                        order_by="ScheduledSearchLog.started_at.desc()")


class ScheduledSearchLog(Base):
    __tablename__ = "scheduled_search_logs"

    id = Column(Integer, primary_key=True)
    search_id = Column(Integer, ForeignKey("scheduled_searches.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(LogStatus), nullable=False, default=LogStatus.running)
    vacancies_found = Column(Integer, nullable=True)
    error = Column(String, nullable=True)
    fetch_session_id = Column(Integer, ForeignKey("fetch_sessions.id"), nullable=True)

    search = relationship("ScheduledSearch", back_populates="logs")
    fetch_session = relationship("FetchSession")
