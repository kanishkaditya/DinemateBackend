from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
import asyncio


class Database:
    client: AsyncIOMotorClient = None
    

db = Database()


async def get_database() -> AsyncIOMotorClient:
    """Get database client"""
    return db.client


async def connect_to_mongo():
    """Create database connection"""
    db.client = AsyncIOMotorClient(settings.database_url)
    
    # Import all models here to register them with Beanie
    from models.user import User
    from models.group_preferences import GroupPreferences
    from models.group import Group, ChatMessage

    
    # Initialize Beanie with the models
    await init_beanie(
        database=db.client[settings.database_name],
        document_models=[User, GroupPreferences, Group, ChatMessage]
    )


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()


# For FastAPI lifespan events
async def startup_db_client():
    """Startup event for database"""
    await connect_to_mongo()


async def shutdown_db_client():
    """Shutdown event for database"""
    await close_mongo_connection()