from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "mongodb+srv://kanishk:gamora12@cluster0.gmynbk3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name: str = "dinemate_db"
    
    # Foursquare API
    foursquare_api_key: str
    foursquare_base_url: str = "https://places-api.foursquare.com"
    
    # OpenAI API
    openai_api_key: str
    
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