from pydantic import BaseModel

from app.models.user import Role


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    role: Role

    model_config = {"from_attributes": True}
