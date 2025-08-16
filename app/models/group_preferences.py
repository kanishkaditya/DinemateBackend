from beanie import Document, Indexed
from pydantic import Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID


class GroupPreferences(Document):
    # Composite key tracking
    group_id: Indexed(typ=str)
    user_id: Indexed(str) 
    firebase_uid: Indexed(str)  # For easy client lookups
    
    # User's preferences specific to this group
    preferences: Dict[str, Any] = Field(default_factory=dict)
    # Example structure:
    # {
    #   "dietary_restrictions": ["vegetarian"],
    #   "preferred_cuisines": ["italian", "thai"],
    #   "budget_preference": "moderate",
    #   "mood_preferences": ["quick", "casual"],
    #   "location_preferences": {"max_distance": 5, "preferred_areas": ["downtown"]},
    #   "time_preferences": {"preferred_times": ["lunch", "early_dinner"]},
    #   "group_dynamics": {"comfortable_with": ["colleagues", "loud_places"]}
    # }
    
    # Tracking metadata
    is_llm_updated: bool = False
    last_updated_by: str = "user"  # "user" | "llm" | "aggregation"
    llm_confidence_score: Optional[float] = None  # How confident LLM is in preferences
    
    # Learning metadata
    total_interactions: int = 0  # Number of times this user interacted in group
    preferences_learned_count: int = 0  # How many preferences LLM has learned
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_llm_update: Optional[datetime] = None
    
    class Settings:
        collection = "group_preferences"
        use_state_management = True
        indexes = [
            [("group_id", 1), ("user_id", 1)],  # Compound unique index
            "group_id",
            "user_id", 
            "firebase_uid"
        ]
    
    def __repr__(self):
        return f"<GroupPreferences(group_id={self.group_id}, user_id={self.user_id})>"
    
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)
