from beanie import Document, Indexed
from pydantic import Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    RESTAURANT_SUGGESTION = "restaurant_suggestion"
    SYSTEM = "system"


class ChatMessage(Document):
    group_id: str
    user_id: str
    user_name: str
    message_type: MessageType = MessageType.TEXT
    content: str
    restaurant_data: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "chat_messages"


class GroupStatus(str, Enum):
    ACTIVE = "active"
    PLANNING = "planning"
    DECIDED = "decided"
    ARCHIVED = "archived"


class Group(Document):
    name: str
    description: Optional[str] = None
    created_by: str
    invite_code: str
    status: GroupStatus = GroupStatus.ACTIVE
    member_ids: List[str] = Field(default_factory=list)
    max_members: int = 10
    
    last_message_at: Optional[datetime] = None
    message_count: int = 0
    
    selected_restaurant: Optional[dict] = None
    decision_made_at: Optional[datetime] = None
    
    aggregated_recommendation_keywords: List[str] = Field(default_factory=list)
    last_keywords_update: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "groups"
        use_state_management = True
    
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)