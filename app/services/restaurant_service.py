"""
Restaurant Service

Orchestration layer for restaurant operations, integrating Foursquare API
with local database storage and group preferences.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from .foursquare_service import foursquare_service

logger = logging.getLogger(__name__)


class RestaurantService:
    """Service for restaurant operations and recommendations."""
    
    def __init__(self):
        self.foursquare = foursquare_service
    
    
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
        Get restaurant recommendations based on group's extracted Foursquare preferences.
        
        Args:
            group_id: ID of the group
            location_name: Location name (e.g., "San Francisco", "downtown")
            latitude: Location latitude (optional if location_name provided)
            longitude: Location longitude (optional if location_name provided)
            query: Search query (e.g., "pizza", "italian restaurant")
            radius: Search radius in meters
            limit: Maximum number of results
            
        Returns:
            Dict containing restaurant results and preferences used
        """
        try:
            # Validate location parameters
            if not location_name and not (latitude and longitude):
                raise ValueError("Either location_name or both latitude/longitude must be provided")
            
            # Get aggregated Foursquare preferences for the group
            foursquare_params = await self._get_aggregated_group_foursquare_params(group_id)
            
            # Build search parameters with user input taking precedence
            search_params = {}
            
            # Location (user input takes precedence)
            if location_name:
                search_params["near"] = location_name
            elif latitude is not None and longitude is not None:
                search_params["ll"] = f"{latitude},{longitude}"
                search_params["radius"] = radius
            elif foursquare_params.get("near"):
                search_params["near"] = foursquare_params["near"]
            
            # Query (user input takes precedence)
            if query:
                search_params["query"] = query
            elif foursquare_params.get("query"):
                search_params["query"] = foursquare_params["query"]
            
            # Categories from group preferences
            if foursquare_params.get("fsq_category_ids"):
                search_params["fsq_category_ids"] = foursquare_params["fsq_category_ids"]
            
            # Price range from group preferences
            if foursquare_params.get("min_price"):
                search_params["min_price"] = foursquare_params["min_price"]
            if foursquare_params.get("max_price"):
                search_params["max_price"] = foursquare_params["max_price"]
            
            # Timing preferences
            if foursquare_params.get("open_now"):
                search_params["open_now"] = True
            
            # Sort preferences
            if foursquare_params.get("sort"):
                search_params["sort"] = foursquare_params["sort"]
            else:
                search_params["sort"] = "relevance"  # Default
            
            # Set limit
            search_params["limit"] = limit

            print(search_params)
            
            # Call Foursquare API directly with extracted parameters
            foursquare_results = await self._search_foursquare_direct(search_params)
            
            # Return raw Foursquare response
            return foursquare_results
            
        except Exception as e:
            logger.error(f"Error getting group recommendations: {str(e)}")
            raise
    
    
    
    async def get_nearby_restaurants(
        self, 
        latitude: float, 
        longitude: float, 
        radius: int = 1000, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get nearby restaurants using direct Foursquare API call.
        """
        try:
            search_params = {
                "ll": f"{latitude},{longitude}",
                "radius": radius,
                "limit": limit
            }
            
            return await self._search_foursquare_direct(search_params)
            
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
    
    async def _get_aggregated_group_foursquare_params(self, group_id: str) -> Dict[str, Any]:
        """Get Foursquare API parameters from the single group preferences document."""
        try:
            from ..models.group_preferences import GroupPreferences
            
            # Get the single group preferences document
            group_prefs = await GroupPreferences.find_one(GroupPreferences.group_id == group_id)
            
            if not group_prefs:
                logger.info(f"No group preferences found for group {group_id}")
                return {}
            
            # Get the already-aggregated parameters
            params = group_prefs.get_aggregated_foursquare_params()
            
            logger.info(f"Retrieved group Foursquare parameters for group {group_id}: {len(params)} parameters")
            return params
            
        except Exception as e:
            logger.error(f"Error getting group Foursquare parameters: {str(e)}")
            return {}
    
    async def _search_foursquare_direct(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Call Foursquare API directly with provided parameters."""
        try:
            import httpx
            from ..config import settings
            
            headers = {
                "Authorization": f"Bearer {settings.foursquare_api_key}",
                "X-Places-Api-Version": "2025-06-17",
                "Accept": "application/json"
            }

            # del search_params['min_price']
            # del search_params['query']
            # del search_params['ll']
            # del search_params['max_price']
            # search_params['max_price']=2
            
            
            print(search_params)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.foursquare_base_url}/places/search",
                    params=search_params,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error calling Foursquare API directly: {str(e)}")
            # Return empty results if API fails
            return {"results": [], "context": {}}


# Global service instance
restaurant_service = RestaurantService()