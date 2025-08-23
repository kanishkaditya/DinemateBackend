from beanie import Document, Indexed
from pydantic import Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4


class User(Document):
    
    firebase_id: Indexed(str, unique=True)
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    full_name: str
    is_active: bool = True
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "users"
        use_state_management = True
    
    async def get_group_preferences(self, group_id: UUID):
        from models.group_preferences import GroupPreferences
        return await GroupPreferences.find_one(
            GroupPreferences.group_id == group_id,
            GroupPreferences.user_id == self.id
        )
    
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)