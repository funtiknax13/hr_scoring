import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.permissions import Permission
from app.database import SessionLocal
from app.models.scoring import (
    JobStatus, ResultStatus,
    ScoringCandidate, ScoringJob, ScoringResult, ScoringVacancy,
)
from app.models.user import User
from app.schemas.scoring import (
    CandidateResultOut, ScoringJobDetailOut, ScoringJobOut, ScoringVacancyOut,
)
from app.services.scoring_engine import (
    PROMPT_VERSIONS,
    build_rubric, compute_total, extract_profile,
    get_client, read_file_bytes, score_candidate, sha256_hex,
)

router = APIRouter(prefix="/api/scoring", tags=["scoring"])

SUPPORTED = {".md", ".txt", ".pdf", ".docx", ".html", ".htm"}


# ----------------------------- Вспомогательное ---------------------------------

def _parse_expected_score(filename: str) -> int | None:
    """Извлекает эталонный балл из имени файла: 'anna_85.md' → 85."""
    stem = Path(filename).stem
    m = re.search(r"_(\d+)$", stem)
    return int(m.group(1)) if m else None


def _kendall_tau(pairs: list[tuple[float, float]]) -> float:
    """Kendall's tau между ожидаемыми и реальными баллами."""
    n = len(pairs)
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            e_sign = pairs[i][0] - pairs[j][0]
            a_sign = pairs[i][1] - pairs[j][1]
            if e_sign * a_sign > 0:
                concordant += 1
            elif e_sign * a_sign < 0:
                discordant += 1
    total = n * (n - 1) // 2
    return round((concordant - discordant) / total, 3) if total > 0 else 0.0


# ----------------------------- Фоновая задача ----------------------------------

def _run_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(ScoringJob).filter(ScoringJob.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.running
        db.commit()

        vacancy = db.query(ScoringVacancy).filter(ScoringVacancy.id == job.vacancy_id).first()
        client = get_client()

        # Фаза 0: рубрика
        rubric = build_rubric(client, vacancy.text)
        job.rubric_json = rubric.model_dump_json()
        if not vacancy.title:
            vacancy.title = rubric.role_title
        db.commit()

        # Фазы 1+2: каждый кандидат
        pending = (
            db.query(ScoringResult)
            .filter(ScoringResult.job_id == job_id, ScoringResult.status == ResultStatus.pending)
            .all()
        )
        for result in pending:
            candidate = db.query(ScoringCandidate).filter(
                ScoringCandidate.id == result.candidate_id
            ).first()
            try:
                profile = extract_profile(client, candidate.resume_text)
                scoring = score_candidate(client, rubric, profile, candidate.resume_text)
                total_score, overall_confidence = compute_total(rubric, scoring)

                if not candidate.name or candidate.name == "Неизвестно":
                    candidate.name = profile.candidate_name

                result.status = ResultStatus.done
                result.total_score = total_score
                result.overall_confidence = overall_confidence
                result.manipulation_attempt = profile.manipulation_attempt
                result.profile_json = profile.model_dump_json()
                result.result_json = scoring.model_dump_json()
            except Exception as e:
                result.status = ResultStatus.error
                result.error = str(e)
            db.commit()

        # Eval: считаем Kendall's tau если режим тестирования
        if job.is_eval and job.expected_scores:
            expected = json.loads(job.expected_scores)
            all_results = (
                db.query(ScoringResult)
                .filter(ScoringResult.job_id == job_id)
                .all()
            )
            pairs: list[tuple[float, float]] = []
            for result in all_results:
                if result.total_score is None:
                    continue
                cand = db.query(ScoringCandidate).filter(
                    ScoringCandidate.id == result.candidate_id
                ).first()
                if cand and cand.filename in expected:
                    pairs.append((float(expected[cand.filename]), result.total_score))
            if len(pairs) >= 2:
                job.eval_tau = _kendall_tau(pairs)

        job.status = JobStatus.done
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        db.rollback()
        job = db.query(ScoringJob).filter(ScoringJob.id == job_id).first()
        if job:
            job.status = JobStatus.error
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


# ----------------------------- Эндпоинты --------------------------------------

@router.get("/vacancies", response_model=list[ScoringVacancyOut])
def list_vacancies(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.SCORING_VIEW)),
):
    return (
        db.query(ScoringVacancy)
        .order_by(ScoringVacancy.created_at.desc())
        .limit(100)
        .all()
    )


@router.post("/jobs", response_model=ScoringJobOut, status_code=201)
async def create_job(
    background_tasks: BackgroundTasks,
    resume_files: Annotated[list[UploadFile], File(description="Файлы резюме")],
    vacancy_file: Optional[UploadFile] = File(None, description="Файл вакансии"),
    vacancy_id: Optional[int] = Form(None, description="ID существующей вакансии"),
    is_eval: str = Form("false"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SCORING_RUN)),
):
    if not vacancy_file and not vacancy_id:
        raise HTTPException(400, "Укажите файл вакансии или выберите существующую вакансию")

    # Валидация форматов резюме
    for f in resume_files:
        ext = "." + (f.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in SUPPORTED:
            raise HTTPException(400, f"Неподдерживаемый формат: {f.filename}")

    # Находим или создаём вакансию
    if vacancy_file:
        ext = "." + (vacancy_file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in SUPPORTED:
            raise HTTPException(400, f"Неподдерживаемый формат: {vacancy_file.filename}")
        vacancy_content = await vacancy_file.read()
        vacancy_text = read_file_bytes(vacancy_content, vacancy_file.filename or "vacancy.txt")
        vacancy_hash = sha256_hex(vacancy_text)
        vacancy = db.query(ScoringVacancy).filter(ScoringVacancy.text_hash == vacancy_hash).first()
        if not vacancy:
            vacancy = ScoringVacancy(
                text_hash=vacancy_hash,
                text=vacancy_text,
                filename=vacancy_file.filename or "vacancy.txt",
            )
            db.add(vacancy)
            db.flush()
    else:
        vacancy = db.query(ScoringVacancy).filter(ScoringVacancy.id == vacancy_id).first()
        if not vacancy:
            raise HTTPException(404, "Вакансия не найдена")

    eval_mode = is_eval.lower() == "true"

    # Собираем эталонные баллы из имён файлов резюме
    expected_scores: dict[str, int] = {}
    if eval_mode:
        for rf in resume_files:
            score = _parse_expected_score(rf.filename or "")
            if score is not None:
                expected_scores[rf.filename or ""] = score

    # Создаём задание
    job = ScoringJob(
        vacancy_id=vacancy.id,
        status=JobStatus.pending,
        model_name=__import__("app.config", fromlist=["settings"]).settings.scoring_model,
        prompt_versions=json.dumps(PROMPT_VERSIONS),
        created_by=current_user.id,
        is_eval=eval_mode,
        expected_scores=json.dumps(expected_scores) if expected_scores else None,
    )
    db.add(job)
    db.flush()

    # Обрабатываем резюме с дедупом
    new_count = 0
    skipped_count = 0
    for rf in resume_files:
        content = await rf.read()
        try:
            resume_text = read_file_bytes(content, rf.filename or "resume.txt")
        except ValueError as e:
            raise HTTPException(400, str(e))

        resume_hash = sha256_hex(resume_text)

        candidate = db.query(ScoringCandidate).filter(
            ScoringCandidate.text_hash == resume_hash
        ).first()
        if not candidate:
            candidate = ScoringCandidate(
                text_hash=resume_hash,
                resume_text=resume_text,
                filename=rf.filename or "resume.txt",
            )
            db.add(candidate)
            db.flush()

        existing = (
            db.query(ScoringResult)
            .filter(
                ScoringResult.vacancy_id == vacancy.id,
                ScoringResult.candidate_id == candidate.id,
                ScoringResult.status == ResultStatus.done,
            )
            .first()
        )

        if existing:
            db.add(ScoringResult(
                job_id=job.id,
                vacancy_id=vacancy.id,
                candidate_id=candidate.id,
                status=ResultStatus.skipped,
                total_score=existing.total_score,
                overall_confidence=existing.overall_confidence,
                manipulation_attempt=existing.manipulation_attempt,
                profile_json=existing.profile_json,
                result_json=existing.result_json,
            ))
            skipped_count += 1
        else:
            db.add(ScoringResult(
                job_id=job.id,
                vacancy_id=vacancy.id,
                candidate_id=candidate.id,
                status=ResultStatus.pending,
            ))
            new_count += 1

    db.commit()

    if new_count > 0:
        background_tasks.add_task(_run_job, job.id)
    else:
        # Все уже скорированы — считаем eval сразу
        if eval_mode and expected_scores:
            all_results = db.query(ScoringResult).filter(ScoringResult.job_id == job.id).all()
            pairs: list[tuple[float, float]] = []
            for result in all_results:
                if result.total_score is None:
                    continue
                cand = db.query(ScoringCandidate).filter(
                    ScoringCandidate.id == result.candidate_id
                ).first()
                if cand and cand.filename in expected_scores:
                    pairs.append((float(expected_scores[cand.filename]), result.total_score))
            if len(pairs) >= 2:
                job.eval_tau = _kendall_tau(pairs)
        job.status = JobStatus.done
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    db.refresh(job)
    return _job_to_out(job, db)


@router.get("/jobs", response_model=list[ScoringJobOut])
def list_jobs(db: Session = Depends(get_db), _=Depends(require_permission(Permission.SCORING_VIEW))):
    jobs = db.query(ScoringJob).order_by(ScoringJob.created_at.desc()).limit(50).all()
    return [_job_to_out(j, db) for j in jobs]


@router.get("/jobs/{job_id}", response_model=ScoringJobDetailOut)
def get_job(job_id: int, db: Session = Depends(get_db), _=Depends(require_permission(Permission.SCORING_VIEW))):
    job = db.query(ScoringJob).filter(ScoringJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Задание не найдено")

    results = (
        db.query(ScoringResult)
        .filter(ScoringResult.job_id == job_id)
        .order_by(ScoringResult.total_score.desc().nulls_last())
        .all()
    )

    out = ScoringJobDetailOut(
        **_job_to_out(job, db).model_dump(),
        rubric_json=job.rubric_json,
        results=[_result_to_out(r) for r in results],
    )
    return out


# ----------------------------- Вспомогательные ---------------------------------

def _job_to_out(job: ScoringJob, db: Session) -> ScoringJobOut:
    results = db.query(ScoringResult).filter(ScoringResult.job_id == job.id).all()
    vacancy = db.query(ScoringVacancy).filter(ScoringVacancy.id == job.vacancy_id).first()
    return ScoringJobOut(
        id=job.id,
        vacancy_id=job.vacancy_id,
        vacancy_title=vacancy.title if vacancy else None,
        vacancy_filename=vacancy.filename if vacancy else "",
        status=job.status,
        model_name=job.model_name,
        prompt_versions=job.prompt_versions,
        error_message=job.error_message,
        created_at=job.created_at,
        finished_at=job.finished_at,
        total_candidates=len(results),
        done_candidates=sum(1 for r in results if r.status == ResultStatus.done),
        skipped_candidates=sum(1 for r in results if r.status == ResultStatus.skipped),
        is_eval=job.is_eval,
        expected_scores=job.expected_scores,
        eval_tau=job.eval_tau,
    )


def _result_to_out(result: ScoringResult) -> CandidateResultOut:
    candidate = result.candidate
    return CandidateResultOut(
        id=result.id,
        candidate_id=result.candidate_id,
        candidate_name=candidate.name if candidate else None,
        candidate_filename=candidate.filename if candidate else "",
        status=result.status,
        total_score=result.total_score,
        overall_confidence=result.overall_confidence,
        manipulation_attempt=result.manipulation_attempt,
        result_json=result.result_json,
        profile_json=result.profile_json,
        error=result.error,
        created_at=result.created_at,
    )
