from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # "development" or "production"
    DATABASE_URL: str = "sqlite+aiosqlite:///./compliance.db"
    REDIS_URL: str | None = None
    LOG_LEVEL: str = "INFO"

    # AI Providers
    LLM_PROVIDER: str = "mock"  # "openai", "gemini", or "mock"
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
