from beanie import Document, Indexed
from pydantic import Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class GroupPreferences(Document):
    group_id: Indexed(typ=str, unique=True)  # ONE document per group
    
    # Aggregated Foursquare parameters from all group members
    extracted_queries: List[str] = Field(default_factory=list)            # All unique queries from members
    extracted_categories: List[str] = Field(default_factory=list)         # All unique category IDs  
    price_preferences: Dict[str, int] = Field(default_factory=dict)       # Consensus price range
    location_preferences: List[str] = Field(default_factory=list)         # Common locations
    timing_preferences: Dict[str, Any] = Field(default_factory=dict)      # Group timing patterns
    sort_preferences: List[str] = Field(default_factory=list)             # Preferred sorting
    
    # Member contribution tracking
    member_contributions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # firebase_uid -> their preferences
    member_count: int = 0
    
    # Preference popularity/frequency
    query_frequency: Dict[str, int] = Field(default_factory=dict)         # query -> count of members who prefer it  
    category_frequency: Dict[str, int] = Field(default_factory=dict)      # category -> count
    
    # LLM learning metadata
    is_llm_updated: bool = False
    last_updated_by: str = "group_initialization"
    llm_confidence_score: Optional[float] = None
    total_group_interactions: int = 0
    preferences_learned_count: int = 0
    foursquare_param_count: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_llm_update: Optional[datetime] = None
    
    class Settings:
        collection = "group_preferences"
        use_state_management = True
        indexes = [
            "group_id"  # Only group_id index since one doc per group
        ]
    
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)
    
    def add_member_preferences(self, firebase_uid: str, user_preferences: Dict[str, Any]) -> None:
        """Add/update a member's preferences to the group preferences."""
        
        # Store this member's individual contribution
        self.member_contributions[firebase_uid] = user_preferences.copy()
        self.member_count = len(self.member_contributions)
        
        # Extract and aggregate preferences
        self._aggregate_member_preferences()
        
        # Update metadata  
        self.last_updated_by = f"member_join_{firebase_uid}"
        
    def remove_member_preferences(self, firebase_uid: str) -> None:
        """Remove a member's preferences when they leave the group."""
        if firebase_uid in self.member_contributions:
            del self.member_contributions[firebase_uid]
            self.member_count = len(self.member_contributions)
            
            # Re-aggregate without this member
            self._aggregate_member_preferences()
            
            self.last_updated_by = f"member_leave_{firebase_uid}"
    
    def update_from_llm_message(self, firebase_uid: str, analysis_result: Dict[str, Any]) -> None:
        """Update group preferences from LLM analysis of a message."""
        if not analysis_result.get("api_ready", False):
            return
        
        foursquare_params = analysis_result.get("foursquare_parameters", {})
        
        # Update the sending member's learned preferences
        if firebase_uid in self.member_contributions:
            member_prefs = self.member_contributions[firebase_uid]
        else:
            member_prefs = {"learned_from_chat": {}}
            self.member_contributions[firebase_uid] = member_prefs
        
        # Add learned preferences to this member's profile
        if "learned_from_chat" not in member_prefs:
            member_prefs["learned_from_chat"] = {}
            
        learned = member_prefs["learned_from_chat"]
        
        # Update learned preferences
        if foursquare_params.get("query"):
            if "queries" not in learned:
                learned["queries"] = []
            if foursquare_params["query"] not in learned["queries"]:
                learned["queries"].append(foursquare_params["query"])
        
        if foursquare_params.get("fsq_category_ids"):
            if "categories" not in learned:
                learned["categories"] = []
            for cat_id in foursquare_params["fsq_category_ids"]:
                if cat_id not in learned["categories"]:
                    learned["categories"].append(cat_id)
        
        if foursquare_params.get("min_price") or foursquare_params.get("max_price"):
            learned["price_range"] = {
                "min": foursquare_params.get("min_price"),
                "max": foursquare_params.get("max_price")
            }
        
        # Re-aggregate all member preferences
        self._aggregate_member_preferences()
        
        # Update metadata
        self.is_llm_updated = True
        self.last_llm_update = datetime.utcnow()
        self.llm_confidence_score = analysis_result.get("overall_relevance", 0.0)
        self.total_group_interactions += 1
        self.last_updated_by = f"llm_message_{firebase_uid}"
    
    def _aggregate_member_preferences(self) -> None:
        """Re-aggregate all member preferences into group preferences."""
        # Reset aggregated data
        self.extracted_queries = []
        self.extracted_categories = []
        self.price_preferences = {}
        self.query_frequency = {}
        self.category_frequency = {}
        
        all_queries = []
        all_categories = []
        price_ranges = []
        
        # Collect all member preferences
        for firebase_uid, member_prefs in self.member_contributions.items():
            
            # Collect from initial user preferences
            if "preferred_cuisines" in member_prefs:
                all_queries.extend(member_prefs["preferred_cuisines"])
                
            if "dietary_restrictions" in member_prefs:
                all_queries.extend(member_prefs["dietary_restrictions"])
                
            if "spice_tolerance" in member_prefs and member_prefs["spice_tolerance"] != "medium":
                all_queries.append(member_prefs["spice_tolerance"])
                
            if "dining_style" in member_prefs:
                all_queries.extend(member_prefs["dining_style"])
            
            # Handle budget preferences
            budget = member_prefs.get("budget_preference", "")
            if budget == "budget":
                price_ranges.append({"min": 1, "max": 2})
            elif budget == "moderate":
                price_ranges.append({"min": 2, "max": 3})
            elif budget == "upscale":
                price_ranges.append({"min": 3, "max": 4})
            
            # Collect from LLM learned preferences
            learned = member_prefs.get("learned_from_chat", {})
            if "queries" in learned:
                all_queries.extend(learned["queries"])
            if "categories" in learned:
                all_categories.extend(learned["categories"])
            if "price_range" in learned:
                price_ranges.append(learned["price_range"])
        
        # Create frequency counts
        for query in all_queries:
            self.query_frequency[query] = self.query_frequency.get(query, 0) + 1
        
        for category in all_categories:
            self.category_frequency[category] = self.category_frequency.get(category, 0) + 1
        
        # Set group preferences to most popular items
        self.extracted_queries = list(set(all_queries))  # Unique queries
        self.extracted_categories = list(set(all_categories))  # Unique categories
        
        # Calculate consensus price range
        if price_ranges:
            min_prices = [p.get("min") for p in price_ranges if p.get("min")]
            max_prices = [p.get("max") for p in price_ranges if p.get("max")]
            
            if min_prices:
                # Use most common min price, or average
                min_consensus = max(set(min_prices), key=min_prices.count)
                self.price_preferences["min_price"] = min_consensus
            
            if max_prices:
                # Use most common max price, or average  
                max_consensus = max(set(max_prices), key=max_prices.count)
                self.price_preferences["max_price"] = max_consensus
        
        # Update parameter count
        self.foursquare_param_count = len([
            v for v in [
                self.extracted_queries,
                self.extracted_categories,
                self.price_preferences.get("min_price"),
                self.price_preferences.get("max_price")
            ] if v
        ])
    
    def get_aggregated_foursquare_params(self) -> Dict[str, Any]:
        """Get aggregated Foursquare API parameters for search."""
        params = {}
        
        # Use most recent query if available
        if self.extracted_queries:
            params["query"] = self.extracted_queries[-1]  # Most recent
        
        # Use all extracted categories
        if self.extracted_categories:
            params["fsq_category_ids"] = ",".join(self.extracted_categories[:5])  # Limit to 5
        
        # Use price range
        if self.price_preferences:
            if "min_price" in self.price_preferences:
                params["min_price"] = self.price_preferences["min_price"]
            if "max_price" in self.price_preferences:
                params["max_price"] = self.price_preferences["max_price"]
        
        # Use most recent location preference
        if self.location_preferences:
            params["near"] = self.location_preferences[-1]  # Most recent
        
        # Use timing preferences
        if self.timing_preferences.get("open_now"):
            params["open_now"] = True
        
        # Use most common sort preference
        if self.sort_preferences:
            # Use most recent sort preference
            params["sort"] = self.sort_preferences[-1]
        
        return params
