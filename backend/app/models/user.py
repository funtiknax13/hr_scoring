import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Role(str, enum.Enum):
    admin = "admin"
    hr = "hr"
    analyst = "analyst"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.hr)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
