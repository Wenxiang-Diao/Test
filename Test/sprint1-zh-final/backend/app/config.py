from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://comp9900:comp9900@localhost:5433/sleep_monitor"
    jwt_secret: str = "comp9900-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
