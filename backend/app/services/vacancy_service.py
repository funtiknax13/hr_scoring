from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.vacancy import FetchSession, Vacancy, VacancySnapshot
from app.sources.registry import SOURCES


def run_search(
    source_name: str,
    query: str,
    city: str | None,
    max_pages: int,
    db: Session,
) -> FetchSession:
    source = SOURCES[source_name]
    rows = source.search(query, city, max_pages)  # raises RuntimeError on failure

    now = datetime.now(timezone.utc)
    session = FetchSession(source=source_name, query=query, city=city, count=len(rows))
    db.add(session)
    db.flush()

    for row in rows:
        vacancy = (
            db.query(Vacancy)
            .filter(Vacancy.source == source_name, Vacancy.external_id == row.external_id)
            .first()
        )
        if vacancy is None:
            vacancy = Vacancy(
                source=source_name,
                external_id=row.external_id,
                title=row.title,
                location=row.location,
                url=row.url,
                first_seen=now,
                last_seen=now,
            )
            db.add(vacancy)
            db.flush()
        else:
            vacancy.last_seen = now
            vacancy.title = row.title
            vacancy.url = row.url

        db.add(VacancySnapshot(
            session_id=session.id,
            vacancy_id=vacancy.id,
            salary_from=row.salary_from,
            salary_to=row.salary_to,
            currency=row.currency,
        ))

    db.commit()
    db.refresh(session)
    return session
