from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "AI Intelligence Pipeline"

    APP_ENV: str = "development"

    DATABASE_URL: str

    REDIS_URL: str = "redis://redis:6379/0"

    GITHUB_TOKEN: str = ""

    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""

    MAX_CONCURRENT_REQUESTS: int = 5

    REQUEST_TIMEOUT: int = 30

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()