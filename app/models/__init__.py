# Import all models to ensure they are registered with Beanie
from .user import User
from .group_preferences import GroupPreferences
from .group import Group, ChatMessage

# Export all models
__all__ = [
    "User",
    "GroupPreferences",
    "Group", 
    "ChatMessage",
]