from datetime import datetime, timezone

from croniter import croniter

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.schedule import LogStatus, ScheduledSearch, ScheduledSearchLog
from app.services.vacancy_service import run_search


def _is_due(cron_expr: str, last_run: datetime | None, now: datetime) -> bool:
    if last_run is None:
        return True
    cron = croniter(cron_expr, last_run)
    return cron.get_next(datetime) <= now


@celery_app.task(name="app.tasks.check_and_dispatch")
def check_and_dispatch() -> None:
    """Запускается каждую минуту. Находит просроченные расписания и ставит задачи."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        searches = (
            db.query(ScheduledSearch)
            .filter(ScheduledSearch.is_active == True)
            .all()
        )
        for search in searches:
            if _is_due(search.cron, search.last_run_at, now):
                run_scheduled_search.delay(search.id)
    finally:
        db.close()


@celery_app.task(name="app.tasks.run_scheduled_search")
def run_scheduled_search(search_id: int) -> None:
    """Выполняет одну запланированную выгрузку и пишет лог."""
    db = SessionLocal()
    log = None
    try:
        search = db.query(ScheduledSearch).filter(ScheduledSearch.id == search_id).first()
        if not search or not search.is_active:
            return

        now = datetime.now(timezone.utc)

        log = ScheduledSearchLog(
            search_id=search_id,
            started_at=now,
            status=LogStatus.running,
        )
        db.add(log)
        search.last_run_at = now
        db.commit()
        db.refresh(log)

        fetch_session = run_search(search.source, search.query, search.city, search.max_pages, db)

        log.finished_at = datetime.now(timezone.utc)
        log.status = LogStatus.done
        log.vacancies_found = fetch_session.count
        log.fetch_session_id = fetch_session.id
        db.commit()

    except Exception as e:
        db.rollback()
        if log and log.id:
            db = SessionLocal()
            try:
                log_row = db.query(ScheduledSearchLog).filter(ScheduledSearchLog.id == log.id).first()
                if log_row:
                    log_row.finished_at = datetime.now(timezone.utc)
                    log_row.status = LogStatus.error
                    log_row.error = str(e)
                    db.commit()
            finally:
                db.close()
    finally:
        try:
            db.close()
        except Exception:
            pass
