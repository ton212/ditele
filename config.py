"""Configuration management for the API."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database configuration - can be set directly or constructed from components
    database_url: Optional[str] = None
    
    # Individual database components (used if database_url is not set)
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "ditelemetry"
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def get_database_url(self) -> str:
        """Get database URL, either from environment or constructed from components."""
        if self.database_url:
            return self.database_url
        
        # Construct database URL from components
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow reading from environment variables with different naming conventions
        env_prefix = ""


settings = Settings()

