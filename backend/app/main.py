from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.admin import create_admin
from app.config import settings
from app.routers import auth, scoring, vacancies

app = FastAPI(title="HR Scoring API", version="0.1.0")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vacancies.router)
app.include_router(scoring.router)

create_admin(app)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
