from typing import Dict, Any, List
from datetime import datetime
from ..models.user import User
from ..models.group_preferences import GroupPreferences


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
        extracted_keywords: Dict[str, List[str]],
        recommendation_keywords: List[str],
        confidence: float = 0.8
    ) -> GroupPreferences:
        """
        Update user's group preferences based on LLM keyword extraction
        
        Args:
            group_id: The group ID
            user_firebase_id: The user's firebase ID
            extracted_keywords: Dictionary of categorized keywords from LLM analysis
            recommendation_keywords: Flattened keywords for API recommendations
            confidence: Confidence score from analysis
        """
        group_prefs = await GroupPreferences.find_one(
            GroupPreferences.group_id == group_id,
            GroupPreferences.firebase_uid == user_firebase_id
        )
        
        if not group_prefs:
            # Create if doesn't exist
            group_prefs = await self.create_default_group_preferences(group_id, user_firebase_id)
        
        # Update with LLM keyword insights
        await self._update_keywords_from_llm(group_prefs, extracted_keywords, recommendation_keywords, confidence)
        return group_prefs
    
    async def _update_keywords_from_llm(
        self, 
        group_prefs: GroupPreferences, 
        extracted_keywords: Dict[str, List[str]], 
        recommendation_keywords: List[str],
        confidence: float = 0.8
    ):
        """Update user preferences with new LLM-extracted keywords"""
        
        # Merge new keywords with existing ones
        current_keywords = group_prefs.llm_keywords.copy()
        
        # For each keyword category, merge with existing keywords
        for category, new_words in extracted_keywords.items():
            if new_words:  # Only process non-empty categories
                existing_words = current_keywords.get(category, [])
                
                # Merge and deduplicate, preserving order
                combined = existing_words.copy()
                for word in new_words:
                    if word not in combined:
                        combined.append(word)
                
                # Limit each category to prevent explosion (top 20 per category)
                current_keywords[category] = combined[-20:]  # Keep most recent 20
        
        # Update timestamps
        current_keywords["last_updated"] = datetime.utcnow().isoformat()
        
        # Update the model
        group_prefs.llm_keywords = current_keywords
        group_prefs.recommendation_keywords = recommendation_keywords[-30:]  # Keep top 30 recommendation keywords
        group_prefs.is_llm_updated = True
        group_prefs.last_updated_by = "llm"
        group_prefs.llm_confidence_score = confidence
        group_prefs.last_llm_update = datetime.utcnow()
        
        # Count new keywords learned
        total_new_keywords = sum(len(words) for words in extracted_keywords.values() if words)
        group_prefs.preferences_learned_count += total_new_keywords
        
        await group_prefs.save()
    
    async def _update_from_llm(self, group_prefs: GroupPreferences, new_preferences: Dict[str, Any], confidence: float = 0.8):
        group_prefs.preferences.update(new_preferences)
        group_prefs.is_llm_updated = True
        group_prefs.last_updated_by = "llm"
        group_prefs.llm_confidence_score = confidence
        group_prefs.last_llm_update = datetime.utcnow()
        group_prefs.preferences_learned_count += len(new_preferences)
        await group_prefs.save()
    
    async def get_group_aggregated_preferences(self, group_id: str) -> Dict[str, Any]:
        """
        Aggregate all members' keyword-based preferences for restaurant recommendation
        """
        all_group_prefs = await GroupPreferences.find(
            GroupPreferences.group_id == group_id
        ).to_list()
        
        if not all_group_prefs:
            return {
                "total_members": 0,
                "aggregated_keywords": [],
                "keyword_frequency": {},
                "legacy_preferences": {},
                "llm_confidence": 0.0,
                "has_llm_data": False
            }
        
        # New aggregation logic based on keywords
        aggregated = {
            "total_members": len(all_group_prefs),
            "aggregated_keywords": [],
            "keyword_frequency": {},  # keyword -> count
            "category_keywords": {},  # category -> [keywords]
            "legacy_preferences": {},  # For backward compatibility
            "llm_confidence": 0.0,
            "has_llm_data": False,
            "members_with_llm_data": 0
        }
        
        # Aggregate keyword data
        all_keywords = {}  # keyword -> frequency
        category_aggregated = {}  # category -> {keyword -> count}
        confidence_scores = []
        members_with_llm = 0
        
        for prefs in all_group_prefs:
            # Process LLM keywords if available
            if prefs.llm_keywords and isinstance(prefs.llm_keywords, dict):
                members_with_llm += 1
                aggregated["has_llm_data"] = True
                
                for category, keywords in prefs.llm_keywords.items():
                    if category == "last_updated":  # Skip metadata
                        continue
                        
                    if isinstance(keywords, list):
                        # Initialize category aggregation if needed
                        if category not in category_aggregated:
                            category_aggregated[category] = {}
                        
                        # Count keywords in this category
                        for keyword in keywords:
                            if keyword and len(keyword.strip()) > 2:  # Valid keywords only
                                keyword = keyword.strip().lower()
                                
                                # Global frequency
                                all_keywords[keyword] = all_keywords.get(keyword, 0) + 1
                                
                                # Category frequency
                                category_aggregated[category][keyword] = category_aggregated[category].get(keyword, 0) + 1
            
            # Track confidence scores
            if prefs.llm_confidence_score:
                confidence_scores.append(prefs.llm_confidence_score)
            
            # Legacy preferences for backward compatibility
            if prefs.preferences:
                for key, value in prefs.preferences.items():
                    if key not in aggregated["legacy_preferences"]:
                        aggregated["legacy_preferences"][key] = []
                    if isinstance(value, list):
                        aggregated["legacy_preferences"][key].extend(value)
                    else:
                        aggregated["legacy_preferences"][key].append(value)
        
        # Finalize aggregation
        aggregated["keyword_frequency"] = dict(sorted(
            all_keywords.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        # Get top keywords overall (limit to top 30 for API efficiency)
        aggregated["aggregated_keywords"] = list(aggregated["keyword_frequency"].keys())[:30]
        
        # Organize by category with frequency
        for category, keyword_freq in category_aggregated.items():
            sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
            aggregated["category_keywords"][category] = [kw for kw, freq in sorted_keywords[:10]]  # Top 10 per category
        
        # Calculate confidence
        aggregated["llm_confidence"] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        aggregated["members_with_llm_data"] = members_with_llm
        
        return aggregated
    
    async def get_llm_aggregated_recommendation_keywords(self, group_id: str, context: str = "") -> List[str]:
        """
        Use LLM to intelligently aggregate and prioritize keywords for restaurant recommendations
        
        Args:
            group_id: The group ID
            context: Additional context (location, time, etc.)
            
        Returns:
            List of prioritized keywords for Foursquare API
        """
        # Get aggregated preferences
        group_prefs = await self.get_group_aggregated_preferences(group_id)
        
        if not group_prefs.get("has_llm_data"):
            # Fallback to legacy preferences or basic keywords
            return self._fallback_keywords_from_legacy(group_prefs.get("legacy_preferences", {}))
        
        # Prepare data for LLM processing
        all_keywords = group_prefs.get("aggregated_keywords", [])
        category_keywords = group_prefs.get("category_keywords", {})
        keyword_frequency = group_prefs.get("keyword_frequency", {})
        total_members = group_prefs.get("total_members", 1)
        
        if not all_keywords:
            return []
        
        # Create LLM prompt for keyword aggregation
        from ...llm_service.langgraph_analyzer import langgraph_analyzer
        
        llm_prompt = f"""
        You are tasked with creating optimal restaurant search keywords for a group dining recommendation.
        
        Group Information:
        - Total members: {total_members}
        - Members with preferences: {group_prefs.get('members_with_llm_data', 0)}
        - Context: {context if context else 'General dining'}
        
        Available Keywords by Category:
        {self._format_keywords_for_llm(category_keywords)}
        
        Keyword Frequency (how many members mentioned each):
        {self._format_frequency_for_llm(keyword_frequency, total_members)}
        
        Task:
        1. Analyze all keywords and their frequency/importance
        2. Prioritize keywords that are mentioned by multiple members
        3. Balance different preference categories (cuisine, taste, price, dietary, etc.)
        4. Generate 5-15 optimal search terms for restaurant discovery
        5. Ensure keywords are practical for restaurant search APIs
        6. Consider dietary restrictions as high priority
        7. Combine similar keywords (e.g., "spicy" and "hot" -> "spicy")
        
        Return ONLY a comma-separated list of keywords, no explanations.
        Example: spicy, thai, budget, vegetarian, casual, quick, authentic
        """
        
        try:
            # Use the existing LLM from langgraph analyzer
            from langchain.schema import HumanMessage
            response = await langgraph_analyzer.llm.ainvoke([HumanMessage(content=llm_prompt)])
            
            # Parse response
            keywords_text = response.content.strip()
            final_keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            
            # Limit and clean keywords
            final_keywords = [kw for kw in final_keywords if len(kw) > 2 and len(kw) < 25][:15]
            
            # Update group-level aggregated keywords
            await self._update_group_recommendation_keywords(group_id, final_keywords)
            
            return final_keywords
            
        except Exception as e:
            # Fallback to frequency-based aggregation
            return self._fallback_frequency_aggregation(keyword_frequency, category_keywords)
    
    def _format_keywords_for_llm(self, category_keywords: Dict[str, List[str]]) -> str:
        """Format category keywords for LLM prompt"""
        formatted = []
        for category, keywords in category_keywords.items():
            if keywords:
                formatted.append(f"{category}: {', '.join(keywords[:8])}")  # Limit to 8 per category for readability
        return '\n'.join(formatted) if formatted else "No categorized keywords available"
    
    def _format_frequency_for_llm(self, keyword_frequency: Dict[str, int], total_members: int) -> str:
        """Format keyword frequency for LLM prompt"""
        if not keyword_frequency:
            return "No frequency data available"
        
        formatted = []
        for keyword, count in list(keyword_frequency.items())[:20]:  # Top 20 keywords
            percentage = int((count / total_members) * 100) if total_members > 0 else 0
            formatted.append(f"{keyword}: {count}/{total_members} members ({percentage}%)")
        
        return '\n'.join(formatted)
    
    def _fallback_keywords_from_legacy(self, legacy_preferences: Dict[str, Any]) -> List[str]:
        """Fallback method using legacy preferences"""
        keywords = []
        
        # Extract from legacy structure
        if "preferred_cuisines" in legacy_preferences:
            keywords.extend(legacy_preferences["preferred_cuisines"][:5])
        
        if "dietary_restrictions" in legacy_preferences:
            keywords.extend(legacy_preferences["dietary_restrictions"][:5])
        
        # Add generic keywords if nothing found
        if not keywords:
            keywords = ["restaurant", "good", "recommended"]
        
        return keywords[:10]
    
    def _fallback_frequency_aggregation(self, keyword_frequency: Dict[str, int], category_keywords: Dict[str, List[str]]) -> List[str]:
        """Fallback method using frequency-based selection"""
        # Start with most frequent keywords
        frequent_keywords = list(keyword_frequency.keys())[:10]
        
        # Add top keywords from important categories
        priority_categories = ["cuisine_keywords", "dietary_keywords", "taste_keywords", "food_keywords"]
        for category in priority_categories:
            if category in category_keywords:
                frequent_keywords.extend(category_keywords[category][:3])
        
        # Remove duplicates and limit
        seen = set()
        final_keywords = []
        for kw in frequent_keywords:
            if kw.lower() not in seen and len(kw) > 2:
                seen.add(kw.lower())
                final_keywords.append(kw)
                if len(final_keywords) >= 12:
                    break
        
        return final_keywords
    
    async def _update_group_recommendation_keywords(self, group_id: str, keywords: List[str]):
        """Update the group model with final recommendation keywords"""
        from ..models.group import Group
        
        group = await Group.find_one(Group.id == group_id)
        if group:
            group.aggregated_recommendation_keywords = keywords
            group.last_keywords_update = datetime.utcnow()
            await group.save()
    
    async def track_user_interaction(self, group_id: str, user_firebase_id: str):
        """Track that user interacted in group (for LLM learning)"""
        group_prefs = await GroupPreferences.find_one(
            GroupPreferences.group_id == group_id,
            GroupPreferences.firebase_uid == user_firebase_id
        )
        
        if group_prefs:
            await self._increment_interaction(group_prefs)


# Global service instance
group_preference_service = GroupPreferencesService()