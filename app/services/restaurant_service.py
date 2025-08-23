"""
Restaurant Service

Orchestration layer for restaurant operations, integrating Foursquare API
with local database storage and group preferences.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from hashlib import md5
import json

from ..models.restaurant import (
    Restaurant, RestaurantLocation, RestaurantCategory, 
    RestaurantHours, RestaurantPhoto, RestaurantReview,
    RestaurantStats, RestaurantSearchCache
)
from ..models.group_preferences import GroupPreferences
from .foursquare_service import (
    foursquare_service, SearchParams, Location
)
from .group_preference_service import group_preference_service
from ..schemas.restaurant import (
    RestaurantSearchRequest, RestaurantSummaryResponse,
    RestaurantDetailResponse, GroupRecommendationRequest,
    RestaurantLocationResponse, RestaurantCategoryResponse
)

logger = logging.getLogger(__name__)


class RestaurantService:
    """Service for restaurant operations and recommendations."""
    
    def __init__(self):
        self.foursquare = foursquare_service
        self.cache_duration = timedelta(hours=6)  # Cache search results for 6 hours
    
    async def search_restaurants(
        self, 
        request: RestaurantSearchRequest
    ) -> Dict[str, Any]:
        """
        Search for restaurants based on location and filters directly from Foursquare API.
        
        Args:
            request: Search request parameters
            
        Returns:
            Raw Foursquare search results
        """
        try:
            foursquare_results = await self.foursquare.search_restaurants_by_preferences(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                query=request.query,
                cuisines=request.cuisines,
                price_range=request.price_range,
                dietary_restrictions=request.dietary_restrictions,
                radius=request.radius,
                limit=request.limit
            )
            
            return foursquare_results
            
        except Exception as e:
            logger.error(f"Error searching restaurants: {str(e)}")
            raise
    
    async def get_restaurant_details(self, fsq_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific restaurant directly from Foursquare API.
        
        Args:
            fsq_id: Foursquare place ID
            
        Returns:
            Raw Foursquare restaurant data or None if not found
        """
        try:
            foursquare_data = await self.foursquare.get_restaurant_details(fsq_id)
            return foursquare_data
            
        except Exception as e:
            logger.error(f"Error getting restaurant details for {fsq_id}: {str(e)}")
            raise
    
    async def get_group_recommendations(
        self,
        group_id: str,
        location_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        query: Optional[str] = None,
        radius: int = 1000,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get restaurant recommendations based on group preferences.
        
        Args:
            group_id: ID of the group
            location_name: Location name (e.g., "San Francisco", "downtown")
            latitude: Location latitude (optional if location_name provided)
            longitude: Location longitude (optional if location_name provided)
            query: Search query (e.g., "pizza", "italian restaurant")
            radius: Search radius in meters
            limit: Maximum number of results
            
        Returns:
            Dict containing restaurant results and group preferences used
        """
        try:
            # Validate location parameters
            if not location_name and not (latitude and longitude):
                raise ValueError("Either location_name or both latitude/longitude must be provided")
            
            # Get aggregated group preferences
            group_prefs = await group_preference_service.get_group_aggregated_preferences(group_id)
            
            if not group_prefs or not group_prefs.get("preferred_cuisines"):
                logger.warning(f"No preferences found for group: {group_id}, returning nearby restaurants")
                # Fall back to nearby search with location name or coordinates
                if location_name:
                    foursquare_results = await self.foursquare.search_restaurants_by_preferences(
                        location_name=location_name,
                        query=query,
                        radius=radius,
                        limit=limit
                    )
                else:
                    foursquare_results = await self.foursquare.search_restaurants_by_preferences(
                        latitude=latitude,
                        longitude=longitude,
                        query=query,
                        radius=radius,
                        limit=limit
                    )
                
                restaurants = await self._process_foursquare_results(foursquare_results)
                formatted_results = [await self._format_restaurant_summary(r) for r in restaurants]
                
                return {
                    "results": [r.dict() for r in formatted_results],
                    "total": len(formatted_results),
                    "group_id": group_id,
                    "group_preferences": {},
                    "message": "No group preferences found, showing nearby restaurants"
                }
            
            # Extract preferences
            cuisines = list(group_prefs.get("preferred_cuisines", {}).keys())[:5]  # Top 5 cuisines
            dietary_restrictions = group_prefs.get("dietary_restrictions", [])
            price_range = None
            
            if group_prefs.get("price_range"):
                min_price = group_prefs["price_range"].get("min", 1)
                max_price = group_prefs["price_range"].get("max", 4)
                price_range = list(range(min_price, max_price + 1))
            
            # Search restaurants using group preferences
            foursquare_results = await self.foursquare.search_restaurants_by_preferences(
                location_name=location_name,
                latitude=latitude,
                longitude=longitude,
                cuisines=cuisines,
                price_range=price_range,
                dietary_restrictions=dietary_restrictions,
                query=query,
                radius=radius,
                limit=limit
            )
            
            # Process results
            restaurants = await self._process_foursquare_results(foursquare_results)
            
            # Format response
            formatted_results = [
                await self._format_restaurant_summary(restaurant)
                for restaurant in restaurants
            ]
            
            # Apply group-specific scoring based on preferences
            scored_results = self._apply_simple_group_scoring(formatted_results, group_prefs)
            
            # Sort by recommendation score
            scored_results.sort(key=lambda x: x.get("recommendation_score", 0), reverse=True)
            
            return {
                "results": [r.dict() for r in scored_results],
                "total": len(scored_results),
                "group_id": group_id,
                "group_preferences": {
                    "preferred_cuisines": cuisines,
                    "dietary_restrictions": dietary_restrictions,
                    "price_range": price_range,
                    "total_members": group_prefs.get("total_members", 0)
                },
                "message": f"Recommendations based on {group_prefs.get('total_members', 0)} member preferences"
            }
            
        except Exception as e:
            logger.error(f"Error getting group recommendations: {str(e)}")
            raise
    
    async def get_legacy_group_recommendations(
        self, 
        request: GroupRecommendationRequest
    ) -> Tuple[List[RestaurantSummaryResponse], Dict[str, Any]]:
        """
        Get restaurant recommendations based on group preferences.
        
        Args:
            request: Group recommendation request
            
        Returns:
            Tuple of (restaurant results, group preferences used)
        """
        try:
            # Get group preferences
            group_prefs = await group_preference_service.get_group_preferences(request.group_id)
            
            if not group_prefs:
                logger.warning(f"No preferences found for group: {request.group_id}")
                # Fall back to basic search
                search_request = RestaurantSearchRequest(
                    location=request.location,
                    radius=request.radius,
                    limit=request.limit,
                    open_now=request.open_now,
                    sort=request.sort
                )
                results, _ = await self.search_restaurants(search_request)
                return results, {}
            
            # Build search request from group preferences
            search_request = self._build_search_from_preferences(request, group_prefs)
            
            # Search restaurants
            results, _ = await self.search_restaurants(search_request)
            
            # Apply group-specific scoring
            scored_results = await self._apply_group_scoring(results, group_prefs)
            
            # Sort by recommendation score
            scored_results.sort(key=lambda x: x.recommendation_score or 0, reverse=True)
            
            preferences_summary = {
                "cuisines": group_prefs.preferred_cuisines,
                "price_range": [group_prefs.min_price_range, group_prefs.max_price_range],
                "dietary_restrictions": group_prefs.dietary_restrictions,
                "disliked_cuisines": group_prefs.disliked_cuisines,
                "member_count": len(group_prefs.member_preferences)
            }
            
            return scored_results, preferences_summary
            
        except Exception as e:
            logger.error(f"Error getting group recommendations: {str(e)}")
            raise
    
    async def get_location_based_group_recommendations(
        self, 
        group_id: str, 
        latitude: float, 
        longitude: float, 
        radius: int = 2000
    ) -> Dict[str, Any]:
        """
        Get restaurant recommendations using group_id and current location coordinates.
        Uses actual user location instead of extracting from chat messages.
        
        Args:
            group_id: ID of the group
            latitude: Current user latitude
            longitude: Current user longitude  
            radius: Search radius in meters
            
        Returns:
            Dict containing restaurant results with full context
        """
        try:
            # TODO: For now using dummy group preferences, implement actual preferences later
            dummy_group_prefs = {
                "total_members": 3,
                "has_llm_data": False,
                "members_with_llm_data": 0,
                "aggregated_keywords": ["food", "good", "restaurant"],
                "keyword_frequency": {"food": 2, "good": 1},
                "legacy_preferences": {},
                "llm_confidence": 0.5
            }
            
            # Extract search context from recent conversations
            search_context = await self._extract_search_context_from_chat(group_id)
            
            # For now, just use basic search query from chat if available
            search_query = search_context.get("search_query", "restaurant")
            
            # Search restaurants using provided coordinates
            foursquare_results = await self.foursquare.search_restaurants_by_preferences(
                latitude=latitude,
                longitude=longitude,
                query=search_query,
                radius=radius,
                limit=25,
                cuisines=None,
                price_range=None,
                dietary_restrictions=None
            )
            
            logger.info(f"Searched near location ({latitude}, {longitude}) with query: {search_query}")
            return foursquare_results
            
        except Exception as e:
            logger.error(f"Error getting location-based group recommendations: {str(e)}")
            raise
    
    async def get_nearby_restaurants(
        self, 
        latitude: float, 
        longitude: float, 
        radius: int = 1000, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get nearby restaurants directly from Foursquare API.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            radius: Search radius in meters
            limit: Maximum number of results
            
        Returns:
            Raw Foursquare search results
        """
        try:
            foursquare_results = await self.foursquare.search_restaurants_by_preferences(
                latitude=latitude,
                longitude=longitude,
                radius=radius,
                limit=limit
            )
            
            return foursquare_results
            
        except Exception as e:
            logger.error(f"Error getting nearby restaurants: {str(e)}")
            raise
    
    async def get_restaurant_photos(self, fsq_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get photos for a restaurant directly from Foursquare API."""
        try:
            return await self.foursquare.get_restaurant_photos(fsq_id, limit)
            
        except Exception as e:
            logger.error(f"Error getting restaurant photos: {str(e)}")
            return {"results": []}
    
    async def get_restaurant_reviews(self, fsq_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get reviews for a restaurant directly from Foursquare API."""
        try:
            return await self.foursquare.get_restaurant_reviews(fsq_id, limit)
            
        except Exception as e:
            logger.error(f"Error getting restaurant reviews: {str(e)}")
            return {"results": []}
    
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            foursquare_healthy = await self.foursquare.health_check()
            
            return {
                "foursquare_api": foursquare_healthy,
                "overall": foursquare_healthy
            }
            
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}")
            return {
                "foursquare_api": False,
                "overall": False,
                "error": str(e)
            }
    async def _extract_search_context_from_chat(self, group_id: str) -> Dict[str, Any]:
        """Extract search context and intent from recent chat messages."""
        try:
            from ..models.group import ChatMessage
            
            # Get recent messages (last 2 hours for immediate context)
            cutoff_time = datetime.utcnow() - timedelta(hours=2)
            recent_messages = await ChatMessage.find(
                ChatMessage.group_id == group_id,
                ChatMessage.created_at >= cutoff_time,
                ChatMessage.message_type == "text"
            ).limit(10).to_list()
            
            # Look for food/restaurant related terms
            food_keywords = ["pizza", "chinese", "italian", "mexican", "indian", "japanese", "thai", "sushi", "burger", "coffee"]
            
            # Get the most recent food mention
            for message in reversed(recent_messages):
                content = message.content.lower()
                for word in food_keywords:
                    if word in content:
                        return {"search_query": word, "context_strength": 0.8}
            
            return {"search_query": "restaurant", "context_strength": 0.3}
            
        except Exception as e:
            logger.warning(f"Error extracting search context: {str(e)}")
            return {"search_query": "restaurant", "context_strength": 0.1}


# Global service instance
restaurant_service = RestaurantService()