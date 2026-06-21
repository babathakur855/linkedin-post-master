from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    backend_port: int = 8040
    frontend_url: str = "http://localhost:3040"
    database_url: str = "sqlite+aiosqlite:///./linkedin_posts.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
