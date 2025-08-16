from typing import Dict, Any, List
from datetime import datetime
from models.user import User
from models.group_preferences import GroupPreferences


class GroupPreferencesService:
    def __init__(self):
        pass
    
    async def create_default_group_preferences(self, group_id: str, user_firebase_id: str) -> GroupPreferences:
        """
        Create group preferences for a user when they join a group
        Uses their default preferences as starting point
        """
        user = await User.find_one(User.firebase_id == user_firebase_id)
        if not user:
            raise ValueError("User not found")
        
        # Check if preferences already exist
        existing = await GroupPreferences.find_one(
            GroupPreferences.group_id == group_id,
            GroupPreferences.firebase_uid == user_firebase_id
        )
        if existing:
            return existing
        
        # Create new group preferences with user's defaults
        group_prefs = GroupPreferences(
            group_id=group_id,
            user_id=str(user.id),
            firebase_uid=user.firebase_id,
            preferences=user.preferences.copy(),  # Start with user defaults
            last_updated_by="user"
        )
        
        await group_prefs.save()
        return group_prefs
    
    async def update_preferences_from_llm(
        self,
        group_id: str,
        user_firebase_id: str,
        new_preferences: Dict[str, Any],
        confidence: float = 0.8
    ) -> GroupPreferences:
        """
        Update user's group preferences based on LLM analysis
        """
        group_prefs = await GroupPreferences.find_one(
            GroupPreferences.group_id == group_id,
            GroupPreferences.firebase_uid == user_firebase_id
        )
        
        if not group_prefs:
            # Create if doesn't exist
            group_prefs = await self.create_default_group_preferences(group_id, user_firebase_id)
        
        # Update with LLM insights (moved from model)
        await self._update_from_llm(group_prefs, new_preferences, confidence)
        return group_prefs
    
    async def _update_from_llm(self, group_prefs: GroupPreferences, new_preferences: Dict[str, Any], confidence: float = 0.8):
        """Update preferences based on LLM analysis (moved from model)"""
        group_prefs.preferences.update(new_preferences)
        group_prefs.is_llm_updated = True
        group_prefs.last_updated_by = "llm"
        group_prefs.llm_confidence_score = confidence
        group_prefs.last_llm_update = datetime.utcnow()
        group_prefs.preferences_learned_count += len(new_preferences)
        await group_prefs.save()
    
    def _get_dietary_restrictions(self, prefs: GroupPreferences) -> list:
        """Extract dietary restrictions (moved from model)"""
        return prefs.preferences.get("dietary_restrictions", [])
    
    def _get_cuisine_preferences(self, prefs: GroupPreferences) -> dict:
        """Get cuisine preferences with scores (moved from model)"""
        return {
            "preferred": prefs.preferences.get("preferred_cuisines", []),
            "disliked": prefs.preferences.get("disliked_cuisines", [])
        }
    
    def _get_budget_range(self, prefs: GroupPreferences) -> dict:
        """Get budget preferences (moved from model)"""
        return prefs.preferences.get("price_range", {"min": 1, "max": 4})
    
    async def _increment_interaction(self, group_prefs: GroupPreferences):
        """Track user interaction in group (moved from model)"""
        group_prefs.total_interactions += 1
        await group_prefs.save()
    
    async def get_group_aggregated_preferences(self, group_id: str) -> Dict[str, Any]:
        """
        Aggregate all members' preferences for restaurant recommendation
        """
        all_group_prefs = await GroupPreferences.find(
            GroupPreferences.group_id == group_id
        ).to_list()
        
        if not all_group_prefs:
            return {}
        
        # Aggregate logic
        aggregated = {
            "total_members": len(all_group_prefs),
            "dietary_restrictions": [],
            "preferred_cuisines": {},
            "budget_range": {"min": 1, "max": 4},
            "ambiance_preferences": {},
            "accessibility_needs": [],
            "llm_confidence": 0.0
        }
        
        # Collect all dietary restrictions (union)
        all_dietary = set()
        cuisine_votes = {}
        budget_mins = []
        budget_maxs = []
        confidence_scores = []
        
        for prefs in all_group_prefs:
            # Dietary restrictions (any member's restriction applies to group)
            dietary = self._get_dietary_restrictions(prefs)
            all_dietary.update(dietary)
            
            # Cuisine preferences (voting system)
            cuisine_prefs = self._get_cuisine_preferences(prefs)
            for cuisine in cuisine_prefs.get("preferred", []):
                cuisine_votes[cuisine] = cuisine_votes.get(cuisine, 0) + 1
            
            # Budget range (intersection - most restrictive)
            budget = self._get_budget_range(prefs)
            budget_mins.append(budget.get("min", 1))
            budget_maxs.append(budget.get("max", 4))
            
            # Track LLM confidence
            if prefs.llm_confidence_score:
                confidence_scores.append(prefs.llm_confidence_score)
        
        # Finalize aggregation
        aggregated["dietary_restrictions"] = list(all_dietary)
        aggregated["preferred_cuisines"] = dict(sorted(
            cuisine_votes.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        aggregated["budget_range"] = {
            "min": max(budget_mins) if budget_mins else 1,
            "max": min(budget_maxs) if budget_maxs else 4
        }
        aggregated["llm_confidence"] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return aggregated
    
    async def track_user_interaction(self, group_id: str, user_firebase_id: str):
        """Track that user interacted in group (for LLM learning)"""
        group_prefs = await GroupPreferences.find_one(
            GroupPreferences.group_id == group_id,
            GroupPreferences.firebase_uid == user_firebase_id
        )
        
        if group_prefs:
            await self._increment_interaction(group_prefs)