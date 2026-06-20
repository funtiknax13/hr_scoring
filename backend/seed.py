"""
Создаёт admin-пользователя если его нет.
Логин и пароль берутся из ADMIN_USERNAME / ADMIN_PASSWORD в .env.
Запускается автоматически из start.sh при старте контейнера.
"""

import bcrypt

from app.config import settings
from app.database import SessionLocal
from app.models.user import Role, User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.admin_username).first()
        if existing:
            print(f"Seed: пользователь '{settings.admin_username}' уже существует, пропускаем")
            return
        db.add(User(
            username=settings.admin_username,
            hashed_password=hash_password(settings.admin_password),
            role=Role.admin,
        ))
        db.commit()
        print(f"Seed: создан admin '{settings.admin_username}'")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
