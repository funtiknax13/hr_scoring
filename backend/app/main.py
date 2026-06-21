from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.admin import create_admin
from app.config import settings
from app.routers import auth, scoring, vacancies

app = FastAPI(title="HR Scoring API", version="0.1.0")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.include_router(auth.router)
app.include_router(vacancies.router)
app.include_router(scoring.router)

create_admin(app)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
