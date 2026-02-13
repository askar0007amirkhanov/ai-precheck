from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    DATABASE_URL: str
    REDIS_URL: str | None = None
    LOG_LEVEL: str = "INFO"
    
    # AI Providers
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
