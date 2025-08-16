from beanie import Document, Indexed
from pydantic import Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4


class User(Document):
    
    firebase_id: Indexed(str, unique=True)
    # User profile from Firebase/client
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    full_name: str
    
    # Status fields
    is_active: bool = True
    
    # Generic preferences (from onboarding)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    # Example structure:
    # {
    #   "dietary_restrictions": ["vegetarian", "gluten_free"],
    #   "preferred_cuisines": ["italian", "mexican"],
    #   "price_range": {"min": 1, "max": 3},
    #   "ambiance": ["casual", "outdoor"],
    #   "spice_tolerance": "medium"
    # }
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "users"
        use_state_management = True
    
    def __repr__(self):
        return f"<User(firebase_uid={self.firebase_uid}, username={self.username})>"
    
    # Helper methods
    # async def get_groups(self):
    #     """Get user's groups"""
    #     from models.group import GroupMember, Group
    #     memberships = await GroupMember.find(GroupMember.user_id == self.id).to_list()
    #     group_ids = [membership.group_id for membership in memberships]
    #     return await Group.find(Group.id.in_(group_ids)).to_list()
    
    async def get_group_preferences(self, group_id: UUID):
        """Get user's preferences for a specific group"""
        from models.group_preferences import GroupPreferences
        return await GroupPreferences.find_one(
            GroupPreferences.group_id == group_id,
            GroupPreferences.user_id == self.id
        )
    
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)