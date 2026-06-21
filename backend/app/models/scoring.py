import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class ResultStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"   # уже был результат для этой пары vacancy+candidate
    error = "error"


class ScoringVacancy(Base):
    __tablename__ = "scoring_vacancies"

    id = Column(Integer, primary_key=True)
    text_hash = Column(String(64), unique=True, nullable=False, index=True)
    text = Column(Text, nullable=False)
    title = Column(String, nullable=True)     # заполняется LLM в фазе 0
    filename = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("ScoringJob", back_populates="vacancy")
    results = relationship("ScoringResult", back_populates="vacancy")


class ScoringCandidate(Base):
    __tablename__ = "scoring_candidates"

    id = Column(Integer, primary_key=True)
    text_hash = Column(String(64), unique=True, nullable=False, index=True)
    resume_text = Column(Text, nullable=False)
    name = Column(String, nullable=True)      # заполняется LLM в фазе 1
    filename = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    results = relationship("ScoringResult", back_populates="candidate")


class ScoringJob(Base):
    __tablename__ = "scoring_jobs"

    id = Column(Integer, primary_key=True)
    vacancy_id = Column(Integer, ForeignKey("scoring_vacancies.id"), nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.pending)
    rubric_json = Column(Text, nullable=True)
    model_name = Column(String, nullable=False)
    prompt_versions = Column(String, nullable=False)  # JSON: {"rubric":"v1",...}
    error_message = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    is_eval = Column(Boolean, nullable=False, default=False)
    expected_scores = Column(Text, nullable=True)  # JSON: {"anna_85.md": 85, ...}
    eval_tau = Column(Float, nullable=True)

    vacancy = relationship("ScoringVacancy", back_populates="jobs")
    results = relationship("ScoringResult", back_populates="job")


class ScoringResult(Base):
    __tablename__ = "scoring_results"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("scoring_jobs.id"), nullable=False)
    vacancy_id = Column(Integer, ForeignKey("scoring_vacancies.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("scoring_candidates.id"), nullable=False)
    status = Column(Enum(ResultStatus), nullable=False, default=ResultStatus.pending)
    total_score = Column(Float, nullable=True)
    overall_confidence = Column(Float, nullable=True)
    manipulation_attempt = Column(Boolean, nullable=True)
    profile_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("ScoringJob", back_populates="results")
    vacancy = relationship("ScoringVacancy", back_populates="results")
    candidate = relationship("ScoringCandidate", back_populates="results")
