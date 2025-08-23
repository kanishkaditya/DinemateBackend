from beanie import Document, Indexed
from pydantic import Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class GroupPreferences(Document):
    group_id: Indexed(typ=str)
    user_id: Indexed(str) 
    firebase_uid: Indexed(str)
    
    preferences: Dict[str, Any] = Field(default_factory=dict)
    llm_keywords: Dict[str, Any] = Field(default_factory=dict)
    recommendation_keywords: List[str] = Field(default_factory=list)
    
    is_llm_updated: bool = False
    last_updated_by: str = "user"
    llm_confidence_score: Optional[float] = None
    total_interactions: int = 0
    preferences_learned_count: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_llm_update: Optional[datetime] = None
    
    class Settings:
        collection = "group_preferences"
        use_state_management = True
        indexes = [
            [("group_id", 1), ("user_id", 1)],
            "group_id",
            "user_id", 
            "firebase_uid"
        ]
    
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)
