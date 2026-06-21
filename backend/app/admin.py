import bcrypt
from typing import Any

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from wtforms import PasswordField

from app.config import settings
from app.database import SessionLocal, engine
from app.models.user import Role, User
from app.models.vacancy import FetchSession, Vacancy, VacancySnapshot
from app.models.scoring import ScoringVacancy, ScoringCandidate, ScoringJob, ScoringResult


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        db = SessionLocal()
        try:
            user = (
                db.query(User)
                .filter(User.username == username, User.role == Role.admin)
                .first()
            )
            if not user:
                return False
            if not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
                return False
            request.session["admin_logged_in"] = True
            return True
        finally:
            db.close()

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return "admin_logged_in" in request.session


class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"

    column_list = ["id", "username", "role", "created_at"]
    column_searchable_list = ["username"]
    column_sortable_list = ["id", "username", "role", "created_at"]

    # Переопределяем hashed_password как поле ввода пароля, created_at скрываем
    form_excluded_columns = ["created_at"]
    form_overrides = {"hashed_password": PasswordField}
    column_labels = {"hashed_password": "Пароль"}

    async def on_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        pwd = data.get("hashed_password", "")
        if pwd:
            # Хэшируем введённый пароль перед сохранением
            data["hashed_password"] = bcrypt.hashpw(
                pwd.encode(), bcrypt.gensalt()
            ).decode()
        elif is_created:
            raise ValueError("Пароль обязателен при создании пользователя")
        else:
            # При редактировании без смены пароля — сохраняем старый хэш
            data["hashed_password"] = model.hashed_password


class FetchSessionAdmin(ModelView, model=FetchSession):
    name = "Сессия выгрузки"
    name_plural = "Сессии выгрузок"
    icon = "fa-solid fa-download"
    column_list = ["id", "source", "query", "city", "count", "fetched_at"]
    column_sortable_list = ["id", "source", "fetched_at", "count"]
    column_searchable_list = ["query", "source"]
    can_create = False
    can_edit = False


class VacancyAdmin(ModelView, model=Vacancy):
    name = "Вакансия"
    name_plural = "Вакансии"
    icon = "fa-solid fa-briefcase"
    column_list = ["id", "source", "external_id", "title", "location", "first_seen", "last_seen"]
    column_sortable_list = ["id", "source", "title", "first_seen", "last_seen"]
    column_searchable_list = ["title", "location", "external_id"]
    can_create = False
    can_edit = False


class VacancySnapshotAdmin(ModelView, model=VacancySnapshot):
    name = "Снимок зарплаты"
    name_plural = "Снимки зарплат"
    icon = "fa-solid fa-chart-line"
    column_list = ["id", "vacancy_id", "session_id", "salary_from", "salary_to", "currency"]
    column_sortable_list = ["id", "salary_from", "salary_to"]
    can_create = False
    can_edit = False


class ScoringVacancyAdmin(ModelView, model=ScoringVacancy):
    name = "Вакансия (скоринг)"
    name_plural = "Вакансии (скоринг)"
    icon = "fa-solid fa-file-lines"
    column_list = ["id", "title", "filename", "created_at"]
    column_searchable_list = ["title", "filename"]
    column_sortable_list = ["id", "title", "created_at"]
    can_create = False


class ScoringCandidateAdmin(ModelView, model=ScoringCandidate):
    name = "Кандидат"
    name_plural = "Кандидаты"
    icon = "fa-solid fa-user-tie"
    column_list = ["id", "name", "filename", "created_at"]
    column_searchable_list = ["name", "filename"]
    column_sortable_list = ["id", "name", "created_at"]
    can_create = False
    form_excluded_columns = ["resume_text", "text_hash"]


class ScoringJobAdmin(ModelView, model=ScoringJob):
    name = "Задание скоринга"
    name_plural = "Задания скоринга"
    icon = "fa-solid fa-brain"
    column_list = ["id", "vacancy_id", "status", "model_name", "created_at", "finished_at"]
    column_sortable_list = ["id", "status", "created_at"]
    can_create = False
    can_edit = False


class ScoringResultAdmin(ModelView, model=ScoringResult):
    name = "Результат скоринга"
    name_plural = "Результаты скоринга"
    icon = "fa-solid fa-star-half-stroke"
    column_list = ["id", "job_id", "candidate_id", "status", "total_score", "overall_confidence", "manipulation_attempt"]
    column_sortable_list = ["id", "total_score", "overall_confidence", "status"]
    can_create = False
    can_edit = False


def create_admin(app: Any) -> None:
    auth_backend = AdminAuth(secret_key=settings.secret_key)
    admin = Admin(app, engine, title="HR Scoring — Admin", authentication_backend=auth_backend)
    admin.add_view(UserAdmin)
    admin.add_view(FetchSessionAdmin)
    admin.add_view(VacancyAdmin)
    admin.add_view(VacancySnapshotAdmin)
    admin.add_view(ScoringVacancyAdmin)
    admin.add_view(ScoringCandidateAdmin)
    admin.add_view(ScoringJobAdmin)
    admin.add_view(ScoringResultAdmin)
