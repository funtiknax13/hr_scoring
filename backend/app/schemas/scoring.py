from datetime import datetime

from pydantic import BaseModel

from app.models.scoring import JobStatus, ResultStatus


class ScoringVacancyOut(BaseModel):
    id: int
    title: str | None
    filename: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateResultOut(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str | None
    candidate_filename: str
    status: ResultStatus
    total_score: float | None
    overall_confidence: float | None
    manipulation_attempt: bool | None
    result_json: str | None
    profile_json: str | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoringJobOut(BaseModel):
    id: int
    vacancy_id: int
    vacancy_title: str | None
    vacancy_filename: str
    status: JobStatus
    model_name: str
    prompt_versions: str
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None
    total_candidates: int = 0
    done_candidates: int = 0
    skipped_candidates: int = 0
    is_eval: bool = False
    expected_scores: str | None = None
    eval_tau: float | None = None

    model_config = {"from_attributes": True}


class ScoringJobDetailOut(ScoringJobOut):
    rubric_json: str | None
    results: list[CandidateResultOut] = []
