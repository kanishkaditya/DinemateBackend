# Import all models to ensure they are registered with SQLAlchemy
from models.user import User
from models.group_preferences import GroupPreferences

# Export all models
__all__ = [
    "User",
    "GroupPreferences", 
]