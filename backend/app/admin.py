import bcrypt
from typing import Any

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from wtforms import PasswordField

from app.config import settings
from app.database import SessionLocal, engine
from app.models.user import Role, User


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


def create_admin(app: Any) -> None:
    auth_backend = AdminAuth(secret_key=settings.secret_key)
    admin = Admin(app, engine, title="HR Scoring — Admin", authentication_backend=auth_backend)
    admin.add_view(UserAdmin)
