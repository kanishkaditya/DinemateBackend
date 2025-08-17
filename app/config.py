from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = ""
    database_name: str = "dinemate_db"
    
    # Foursquare API
    foursquare_api_key: str
    foursquare_base_url: str = "https://api.foursquare.com/v3"
    
    # Application
    app_name: str = "DineMate"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()