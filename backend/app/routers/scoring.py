import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.database import SessionLocal
from app.models.scoring import (
    JobStatus, ResultStatus,
    ScoringCandidate, ScoringJob, ScoringResult, ScoringVacancy,
)
from app.models.user import User
from app.schemas.scoring import CandidateResultOut, ScoringJobDetailOut, ScoringJobOut
from app.services.scoring_engine import (
    PROMPT_VERSIONS,
    build_rubric, compute_total, extract_profile,
    get_client, read_file_bytes, score_candidate, sha256_hex,
)

router = APIRouter(prefix="/api/scoring", tags=["scoring"])

SUPPORTED = {".md", ".txt", ".pdf", ".docx", ".html", ".htm"}


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

@router.post("/jobs", response_model=ScoringJobOut, status_code=201)
async def create_job(
    background_tasks: BackgroundTasks,
    vacancy_file: Annotated[UploadFile, File(description="Файл вакансии")],
    resume_files: Annotated[list[UploadFile], File(description="Файлы резюме")],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Валидация форматов
    all_files = [vacancy_file] + resume_files
    for f in all_files:
        ext = "." + (f.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in SUPPORTED:
            raise HTTPException(400, f"Неподдерживаемый формат: {f.filename}")

    # Читаем вакансию
    vacancy_content = await vacancy_file.read()
    vacancy_text = read_file_bytes(vacancy_content, vacancy_file.filename or "vacancy.txt")
    vacancy_hash = sha256_hex(vacancy_text)

    # Находим или создаём вакансию
    vacancy = db.query(ScoringVacancy).filter(ScoringVacancy.text_hash == vacancy_hash).first()
    if not vacancy:
        vacancy = ScoringVacancy(
            text_hash=vacancy_hash,
            text=vacancy_text,
            filename=vacancy_file.filename or "vacancy.txt",
        )
        db.add(vacancy)
        db.flush()

    # Создаём задание
    job = ScoringJob(
        vacancy_id=vacancy.id,
        status=JobStatus.pending,
        model_name=__import__("app.config", fromlist=["settings"]).settings.scoring_model,
        prompt_versions=json.dumps(PROMPT_VERSIONS),
        created_by=current_user.id,
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

        # Проверяем: уже есть done-результат для этой пары?
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
            # Добавляем skipped-строку чтобы показать в этом job
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
        # Все уже скорированы
        job.status = JobStatus.done
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    db.refresh(job)
    return _job_to_out(job, db)


@router.get("/jobs", response_model=list[ScoringJobOut])
def list_jobs(db: Session = Depends(get_db), _=Depends(get_current_user)):
    jobs = db.query(ScoringJob).order_by(ScoringJob.created_at.desc()).limit(50).all()
    return [_job_to_out(j, db) for j in jobs]


@router.get("/jobs/{job_id}", response_model=ScoringJobDetailOut)
def get_job(job_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
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
