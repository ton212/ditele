"""Configuration management for the API."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database configuration
    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/ditelemetry"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

