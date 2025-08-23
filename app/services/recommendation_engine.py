"""
Advanced Recommendation Engine

ML-based restaurant recommendation system that considers group dynamics,
individual preferences, contextual factors, and historical patterns.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import json

from ..models.restaurant import Restaurant
from ..models.group_preferences import GroupPreferences
from ..models.user import User
from ..schemas.restaurant import RestaurantSummaryResponse
from shared.location_utils import LocationUtils

logger = logging.getLogger(__name__)


@dataclass
class RecommendationContext:
    """Context for generating recommendations."""
    group_id: str
    user_location: Tuple[float, float]  # (lat, lng)
    search_radius: int
    time_of_day: str  # breakfast, lunch, dinner, late_night
    day_of_week: str
    weather: Optional[str] = None
    budget_preference: Optional[str] = None
    occasion: Optional[str] = None  # casual, celebration, business
    group_size: Optional[int] = None
    urgency: str = "normal"  # low, normal, high


@dataclass
class UserPreferenceProfile:
    """Individual user preference profile."""
    user_id: str
    cuisine_preferences: Dict[str, float]  # cuisine -> preference score
    price_sensitivity: float  # 0-1 scale
    adventure_level: float  # willingness to try new things
    dietary_restrictions: List[str]
    location_preferences: Dict[str, float]  # area -> preference score
    time_preferences: Dict[str, float]  # time_slot -> preference score
    social_influence: float  # how much they influence group decisions


class AdvancedRecommendationEngine:
    """Advanced ML-based recommendation engine."""
    
    def __init__(self):
        self.location_utils = LocationUtils()
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.scaler = StandardScaler()
        
        # Weights for different scoring factors
        self.weights = {
            "group_preference_match": 0.25,
            "individual_satisfaction": 0.20,
            "location_convenience": 0.15,
            "contextual_appropriateness": 0.15,
            "quality_indicators": 0.15,
            "novelty_factor": 0.10
        }
    
    async def generate_recommendations(
        self,
        context: RecommendationContext,
        candidate_restaurants: List[Restaurant],
        group_preferences: GroupPreferences,
        user_profiles: List[UserPreferenceProfile]
    ) -> List[Tuple[Restaurant, float]]:
        """
        Generate scored recommendations for a group.
        
        Args:
            context: Recommendation context
            candidate_restaurants: List of potential restaurants
            group_preferences: Group preference data
            user_profiles: Individual user profiles
            
        Returns:
            List of (restaurant, score) tuples sorted by score
        """
        try:
            if not candidate_restaurants:
                return []
            
            scored_restaurants = []
            
            for restaurant in candidate_restaurants:
                score = await self._calculate_comprehensive_score(
                    restaurant, context, group_preferences, user_profiles
                )
                scored_restaurants.append((restaurant, score))
            
            # Sort by score (descending)
            scored_restaurants.sort(key=lambda x: x[1], reverse=True)
            
            # Apply diversity filtering to avoid too similar recommendations
            diverse_recommendations = self._apply_diversity_filter(scored_restaurants[:50])
            
            logger.info(f"Generated {len(diverse_recommendations)} recommendations for group {context.group_id}")
            
            return diverse_recommendations[:20]  # Return top 20
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    async def _calculate_comprehensive_score(
        self,
        restaurant: Restaurant,
        context: RecommendationContext,
        group_preferences: GroupPreferences,
        user_profiles: List[UserPreferenceProfile]
    ) -> float:
        """Calculate comprehensive recommendation score."""
        
        scores = {}
        
        # 1. Group preference matching
        scores["group_preference_match"] = self._score_group_preference_match(
            restaurant, group_preferences
        )
        
        # 2. Individual satisfaction prediction
        scores["individual_satisfaction"] = self._score_individual_satisfaction(
            restaurant, user_profiles
        )
        
        # 3. Location convenience
        scores["location_convenience"] = self._score_location_convenience(
            restaurant, context
        )
        
        # 4. Contextual appropriateness
        scores["contextual_appropriateness"] = self._score_contextual_fit(
            restaurant, context
        )
        
        # 5. Quality indicators
        scores["quality_indicators"] = self._score_quality_indicators(restaurant)
        
        # 6. Novelty factor
        scores["novelty_factor"] = await self._score_novelty_factor(
            restaurant, context.group_id
        )
        
        # Calculate weighted final score
        final_score = sum(
            scores[factor] * self.weights[factor]
            for factor in scores
        )
        
        # Apply contextual boosts/penalties
        final_score = self._apply_contextual_adjustments(
            final_score, restaurant, context
        )
        
        return min(1.0, max(0.0, final_score))
    
    def _score_group_preference_match(
        self,
        restaurant: Restaurant,
        group_preferences: GroupPreferences
    ) -> float:
        """Score how well restaurant matches group preferences."""
        score = 0.0
        factors = 0
        
        # Cuisine preference matching
        if group_preferences.preferred_cuisines:
            cuisine_match = 0.0
            for cuisine in restaurant.cuisine_types:
                if cuisine.lower() in [c.lower() for c in group_preferences.preferred_cuisines]:
                    cuisine_match = 1.0
                    break
            score += cuisine_match
            factors += 1
        
        # Price range matching
        if (restaurant.price and 
            group_preferences.min_price_range and 
            group_preferences.max_price_range):
            
            if group_preferences.min_price_range <= restaurant.price <= group_preferences.max_price_range:
                price_match = 1.0
            else:
                # Gradual penalty for being outside range
                distance = min(
                    abs(restaurant.price - group_preferences.min_price_range),
                    abs(restaurant.price - group_preferences.max_price_range)
                )
                price_match = max(0.0, 1.0 - (distance * 0.3))
            
            score += price_match
            factors += 1
        
        # Dietary restrictions compliance
        if group_preferences.dietary_restrictions:
            compliance_score = 0.0
            for restriction in group_preferences.dietary_restrictions:
                if restaurant.has_dietary_option(restriction):
                    compliance_score += 1.0
            
            if group_preferences.dietary_restrictions:
                compliance_score /= len(group_preferences.dietary_restrictions)
            
            score += compliance_score
            factors += 1
        
        # Disliked cuisines penalty
        if group_preferences.disliked_cuisines:
            penalty = 0.0
            for cuisine in restaurant.cuisine_types:
                if cuisine.lower() in [c.lower() for c in group_preferences.disliked_cuisines]:
                    penalty = 0.5  # Strong penalty for disliked cuisines
                    break
            score -= penalty
        
        return score / max(1, factors) if factors > 0 else 0.5
    
    def _score_individual_satisfaction(
        self,
        restaurant: Restaurant,
        user_profiles: List[UserPreferenceProfile]
    ) -> float:
        """Predict individual user satisfaction and group harmony."""
        if not user_profiles:
            return 0.5
        
        individual_scores = []
        
        for profile in user_profiles:
            user_score = 0.0
            
            # Cuisine preference
            cuisine_score = 0.0
            for cuisine in restaurant.cuisine_types:
                cuisine_score = max(
                    cuisine_score,
                    profile.cuisine_preferences.get(cuisine.lower(), 0.0)
                )
            user_score += cuisine_score * 0.4
            
            # Price sensitivity
            if restaurant.price:
                price_comfort = 1.0 - abs(restaurant.price / 4.0 - profile.price_sensitivity)
                user_score += max(0.0, price_comfort) * 0.3
            
            # Dietary restrictions compliance
            dietary_score = 1.0
            for restriction in profile.dietary_restrictions:
                if not restaurant.has_dietary_option(restriction):
                    dietary_score = 0.0
                    break
            user_score += dietary_score * 0.3
            
            individual_scores.append(user_score)
        
        # Calculate group satisfaction metrics
        avg_satisfaction = np.mean(individual_scores)
        satisfaction_variance = np.var(individual_scores)
        
        # Penalize high variance (group disagreement)
        harmony_bonus = max(0.0, 1.0 - satisfaction_variance)
        
        return (avg_satisfaction + harmony_bonus * 0.3) / 1.3
    
    def _score_location_convenience(
        self,
        restaurant: Restaurant,
        context: RecommendationContext
    ) -> float:
        """Score location convenience and accessibility."""
        # Distance scoring
        distance = restaurant.distance or self.location_utils.haversine_distance(
            context.user_location[0], context.user_location[1],
            restaurant.location.latitude, restaurant.location.longitude,
            "meters"
        )
        
        # Distance scoring (closer is better, with diminishing returns)
        if distance <= 500:  # Very close
            distance_score = 1.0
        elif distance <= 1000:  # Close
            distance_score = 0.9
        elif distance <= 2000:  # Moderate
            distance_score = 0.7
        elif distance <= 5000:  # Far but reasonable
            distance_score = 0.5
        else:  # Very far
            distance_score = 0.2
        
        return distance_score
    
    def _score_contextual_fit(
        self,
        restaurant: Restaurant,
        context: RecommendationContext
    ) -> float:
        """Score how well restaurant fits the context."""
        score = 0.5  # Base score
        
        # Time of day appropriateness
        time_appropriateness = {
            "breakfast": {
                "cafe": 0.9, "american": 0.8, "french": 0.7
            },
            "lunch": {
                "fast_food": 0.9, "american": 0.8, "italian": 0.8, "asian": 0.8
            },
            "dinner": {
                "fine_dining": 0.9, "italian": 0.9, "french": 0.9, "indian": 0.8
            },
            "late_night": {
                "fast_food": 0.9, "american": 0.8, "pizza": 0.9
            }
        }
        
        time_score = 0.5
        if context.time_of_day in time_appropriateness:
            for cuisine in restaurant.cuisine_types:
                cuisine_lower = cuisine.lower()
                for key, value in time_appropriateness[context.time_of_day].items():
                    if key in cuisine_lower:
                        time_score = max(time_score, value)
        
        score = (score + time_score) / 2
        
        # Occasion appropriateness
        if context.occasion == "celebration" and restaurant.price and restaurant.price >= 3:
            score += 0.2
        elif context.occasion == "casual" and restaurant.price and restaurant.price <= 2:
            score += 0.1
        elif context.occasion == "business" and restaurant.rating and restaurant.rating >= 7:
            score += 0.15
        
        # Group size considerations
        if context.group_size:
            if context.group_size <= 2:
                # Small groups - intimate places are good
                if "intimate" in (restaurant.features or []):
                    score += 0.1
            elif context.group_size >= 6:
                # Large groups - need accommodating places
                if "large_groups" in (restaurant.features or []):
                    score += 0.2
                else:
                    score -= 0.1  # Penalty for potential capacity issues
        
        return min(1.0, score)
    
    def _score_quality_indicators(self, restaurant: Restaurant) -> float:
        """Score based on quality indicators."""
        score = 0.0
        factors = 0
        
        # Rating score
        if restaurant.rating:
            score += restaurant.rating / 10.0
            factors += 1
        
        # Popularity score
        if restaurant.popularity:
            score += restaurant.popularity
            factors += 1
        
        # Photo availability (indicates active management)
        if restaurant.photos:
            score += 0.8
            factors += 1
        
        # Review availability
        if restaurant.reviews:
            score += 0.7
            factors += 1
        
        # Feature richness
        if restaurant.features:
            feature_score = min(1.0, len(restaurant.features) * 0.1)
            score += feature_score
            factors += 1
        
        return score / max(1, factors)
    
    async def _score_novelty_factor(self, restaurant: Restaurant, group_id: str) -> float:
        """Score novelty/exploration factor."""
        # This would typically check visit history from database
        # For now, return a baseline novelty score
        
        # Favor less common cuisines slightly
        uncommon_cuisines = ["ethiopian", "peruvian", "moroccan", "korean", "vietnamese"]
        
        novelty_score = 0.5
        
        for cuisine in restaurant.cuisine_types:
            if cuisine.lower() in uncommon_cuisines:
                novelty_score = 0.8
                break
        
        # New restaurants (within last 6 months) get novelty boost
        if restaurant.created_at and restaurant.created_at > datetime.utcnow() - timedelta(days=180):
            novelty_score += 0.2
        
        return min(1.0, novelty_score)
    
    def _apply_contextual_adjustments(
        self,
        base_score: float,
        restaurant: Restaurant,
        context: RecommendationContext
    ) -> float:
        """Apply final contextual adjustments."""
        adjusted_score = base_score
        
        # Urgency adjustments
        if context.urgency == "high":
            # Favor restaurants with shorter wait times (approximate by popularity)
            if restaurant.popularity and restaurant.popularity < 0.7:
                adjusted_score += 0.1
        
        # Weather considerations (if available)
        if context.weather:
            if context.weather == "rainy" and "outdoor_seating" in (restaurant.features or []):
                adjusted_score -= 0.1
            elif context.weather == "sunny" and "outdoor_seating" in (restaurant.features or []):
                adjusted_score += 0.1
        
        # Budget constraints
        if context.budget_preference == "budget" and restaurant.price and restaurant.price > 2:
            adjusted_score -= 0.2
        elif context.budget_preference == "luxury" and restaurant.price and restaurant.price < 3:
            adjusted_score -= 0.1
        
        return adjusted_score
    
    def _apply_diversity_filter(
        self,
        scored_restaurants: List[Tuple[Restaurant, float]]
    ) -> List[Tuple[Restaurant, float]]:
        """Apply diversity filtering to avoid similar recommendations."""
        if len(scored_restaurants) <= 10:
            return scored_restaurants
        
        diverse_list = []
        used_cuisines = set()
        used_price_ranges = set()
        
        # First pass: pick top scorer from each cuisine/price combo
        for restaurant, score in scored_restaurants:
            cuisine_key = tuple(sorted(restaurant.cuisine_types[:2]))  # Primary cuisines
            price_key = restaurant.price or 0
            
            combo_key = (cuisine_key, price_key)
            
            if combo_key not in used_cuisines or len(diverse_list) < 5:
                diverse_list.append((restaurant, score))
                used_cuisines.add(combo_key)
                
                if len(diverse_list) >= 15:
                    break
        
        # Second pass: fill remaining slots with highest scores
        remaining_slots = 20 - len(diverse_list)
        added_ids = {r[0].fsq_id for r in diverse_list}
        
        for restaurant, score in scored_restaurants:
            if restaurant.fsq_id not in added_ids and remaining_slots > 0:
                diverse_list.append((restaurant, score))
                remaining_slots -= 1
        
        # Re-sort the diverse list by score
        diverse_list.sort(key=lambda x: x[1], reverse=True)
        
        return diverse_list
    
    def build_user_profile(
        self,
        user_id: str,
        user_messages: List[Dict[str, Any]],
        user_restaurant_history: List[Dict[str, Any]]
    ) -> UserPreferenceProfile:
        """Build a user preference profile from their data."""
        
        # Initialize profile with defaults
        profile = UserPreferenceProfile(
            user_id=user_id,
            cuisine_preferences={},
            price_sensitivity=0.5,
            adventure_level=0.5,
            dietary_restrictions=[],
            location_preferences={},
            time_preferences={},
            social_influence=0.5
        )
        
        # Analyze messages for preferences
        if user_messages:
            cuisine_mentions = {}
            positive_sentiment_count = 0
            total_messages = len(user_messages)
            
            for message in user_messages:
                analysis = message.get("analysis", {})
                
                # Extract cuisine preferences
                preferences = analysis.get("preferences", {})
                for cuisine in preferences.get("cuisines", []):
                    cuisine_mentions[cuisine] = cuisine_mentions.get(cuisine, 0) + 1
                
                # Analyze sentiment for adventure level
                sentiment = analysis.get("sentiment", {})
                if sentiment.get("enthusiasm_level") == "high":
                    positive_sentiment_count += 1
            
            # Build cuisine preference scores
            for cuisine, count in cuisine_mentions.items():
                profile.cuisine_preferences[cuisine] = min(1.0, count / total_messages * 2)
            
            # Adventure level from enthusiasm
            if total_messages > 0:
                profile.adventure_level = min(1.0, positive_sentiment_count / total_messages * 1.5)
        
        # Analyze restaurant history
        if user_restaurant_history:
            price_history = []
            for visit in user_restaurant_history:
                if visit.get("price"):
                    price_history.append(visit["price"])
            
            if price_history:
                # Price sensitivity from average spending
                avg_price = np.mean(price_history)
                profile.price_sensitivity = min(1.0, avg_price / 4.0)
        
        return profile


# Global recommendation engine instance
recommendation_engine = AdvancedRecommendationEngine()