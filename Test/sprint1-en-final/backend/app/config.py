from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://comp9900:comp9900@localhost:5434/sleep_monitor_en"
    jwt_secret: str = "comp9900-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:5174", "http://127.0.0.1:5174"]

    class Config:
        env_file = ".env"


settings = Settings()
