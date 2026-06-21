from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 часов
    admin_username: str
    admin_password: str
    hh_token: str = ""
    hh_user_agent: str = "HR-Scoring-Tool/1.0 (user@example.com)"
    sj_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    scoring_model: str = "deepseek-chat"
    redis_url: str = "redis://redis:6379/0"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
