from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.permissions import Permission
from app.models.vacancy import FetchSession, Vacancy, VacancySnapshot
from app.schemas.vacancy import (
    SearchRequest,
    SessionDetailOut,
    SessionOut,
    SnapshotOut,
    VacancyWithSnapshot,
)
from app.services.vacancy_service import run_search

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])


def _run_search(source_name: str, body: SearchRequest, db: Session) -> SessionOut:
    try:
        session = run_search(source_name, body.query, body.city, body.max_pages, db)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return SessionOut.model_validate(session)


@router.post("/hh", response_model=SessionOut, summary="Выгрузить вакансии с HH")
def search_hh(
    body: SearchRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permission.VACANCY_FETCH)),
):
    return _run_search("hh", body, db)


@router.post("/sj", response_model=SessionOut, summary="Выгрузить вакансии с SuperJob")
def search_sj(
    body: SearchRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permission.VACANCY_FETCH)),
):
    return _run_search("sj", body, db)


@router.get("/sessions", response_model=list[SessionOut], summary="История выгрузок")
def list_sessions(
    source: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permission.VACANCY_VIEW)),
):
    q = db.query(FetchSession).order_by(FetchSession.fetched_at.desc())
    if source:
        q = q.filter(FetchSession.source == source)
    return [SessionOut.model_validate(s) for s in q.limit(100).all()]


@router.get("/sessions/{session_id}", response_model=SessionDetailOut, summary="Детали сессии выгрузки")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permission.VACANCY_VIEW)),
):
    session = db.query(FetchSession).filter(FetchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    snapshots = (
        db.query(VacancySnapshot)
        .filter(VacancySnapshot.session_id == session_id)
        .all()
    )

    vacancies = []
    for snap in snapshots:
        v = VacancyWithSnapshot.model_validate(snap.vacancy)
        v.latest = SnapshotOut(
            salary_from=snap.salary_from,
            salary_to=snap.salary_to,
            currency=snap.currency,
            fetched_at=session.fetched_at,
        )
        vacancies.append(v)

    out = SessionDetailOut.model_validate(session)
    out.vacancies = vacancies
    return out


@router.get("/{vacancy_id}/trend", response_model=list[SnapshotOut], summary="Тренд зарплаты по вакансии")
def vacancy_trend(
    vacancy_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission(Permission.VACANCY_VIEW)),
):
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    snapshots = (
        db.query(VacancySnapshot, FetchSession.fetched_at)
        .join(FetchSession, VacancySnapshot.session_id == FetchSession.id)
        .filter(VacancySnapshot.vacancy_id == vacancy_id)
        .order_by(FetchSession.fetched_at.asc())
        .all()
    )

    return [
        SnapshotOut(
            salary_from=snap.salary_from,
            salary_to=snap.salary_to,
            currency=snap.currency,
            fetched_at=fetched_at,
        )
        for snap, fetched_at in snapshots
    ]
