"""
Foursquare API Service

Handles interactions with Foursquare Places API for restaurant data.
"""

import httpx
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class Location:
    """Location coordinates."""
    latitude: float
    longitude: float


@dataclass
class SearchParams:
    """Search parameters for restaurant queries."""
    # Location options (use one of these)
    location: Optional[Location] = None  # lat/lng coordinates
    near: Optional[str] = None  # location name (e.g., "San Francisco", "downtown")
    
    # Search parameters
    query: Optional[str] = None  # search term (e.g., "pizza", "McDonald's")
    radius: int = 1000  # meters
    limit: int = 20
    categories: Optional[List[str]] = None
    price_range: Optional[List[int]] = None  # 1-4 scale
    open_now: bool = False
    sort: str = "RELEVANCE"  # RELEVANCE, DISTANCE, POPULARITY


class FoursquareService:
    """Service for interacting with Foursquare Places API."""
    
    def __init__(self):
        self.api_key = settings.foursquare_api_key
        if not self.api_key:
            logger.warning("FOURSQUARE_API_KEY not found in environment variables")
        
        self.base_url = f"{settings.foursquare_base_url}/places"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Places-Api-Version": "2025-06-17",
            "Accept": "application/json"
        }
    
    async def search_restaurants(self, params: SearchParams) -> Dict:
        """
        Search for restaurants using Foursquare Places API.
        
        Args:
            params: Search parameters including location, filters, etc.
            
        Returns:
            Dict containing search results from Foursquare API
        """
        if not self.api_key:
            raise ValueError("Foursquare API key not configured")
        
        # Build query parameters
        query_params = {
        }
        
        # Add location parameters (use one of: ll, near)
        if params.location:
            query_params["ll"] = f"{params.location.latitude},{params.location.longitude}"
            query_params["radius"] = params.radius
        elif params.near:
            query_params["near"] = params.near
            if params.radius != 1000:  # Only add radius if it's not default
                query_params["radius"] = params.radius
        else:
            raise ValueError("Either location coordinates or near parameter must be provided")
        
        # Add search query if provided
        if params.query:
            query_params["query"] = params.query
        
        if params.price_range:
            query_params["price"] = ",".join(map(str, params.price_range))
        
        if params.open_now:
            query_params["open_now"] = "true"
        
        # Add required fields
        # query_params["fields"] = (
        #     "fsq_id,name,location,categories,price,rating,popularity,"
        #     "hours,website,tel,description,features,distance"
        # )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params=query_params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Foursquare API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Foursquare API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in restaurant search: {str(e)}")
            raise
    
    async def get_restaurant_details(self, fsq_id: str) -> Dict:
        """
        Get detailed information about a specific restaurant.
        
        Args:
            fsq_id: Foursquare place ID
            
        Returns:
            Dict containing detailed restaurant information
        """
        if not self.api_key:
            raise ValueError("Foursquare API key not configured")
        
        query_params = {
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/{fsq_id}",
                    params=query_params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Foursquare API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Foursquare API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting restaurant details: {str(e)}")
            raise
    
    async def search_restaurants_by_preferences(
        self,
        location_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        cuisines: Optional[List[str]] = None,
        price_range: Optional[List[int]] = None,
        dietary_restrictions: Optional[List[str]] = None,
        query: Optional[str] = None,
        radius: int = 1000,
        limit: int = 20
    ) -> Dict:
        """
        Search for restaurants based on group preferences.
        
        Args:
            location_name: Location name (e.g., "San Francisco", "downtown")
            latitude: Location latitude (optional if location_name provided)
            longitude: Location longitude (optional if location_name provided)
            cuisines: List of preferred cuisines
            price_range: Preferred price range (1-4)
            dietary_restrictions: List of dietary restrictions
            query: Search query (e.g., "pizza", "italian restaurant")
            radius: Search radius in meters
            limit: Maximum number of results
            
        Returns:
            Dict containing filtered search results
        """
        # Determine location method
        location = None
        near = None
        
        if location_name:
            near = location_name
        elif latitude is not None and longitude is not None:
            location = Location(latitude=latitude, longitude=longitude)
        else:
            raise ValueError("Either location_name or both latitude/longitude must be provided")
        
        # Map cuisines to categories if provided
        categories = None
        if cuisines:
            categories = self._map_cuisines_to_categories(cuisines)
        
        params = SearchParams(
            location=location,
            near=near,
            query=query,
            radius=radius,
            limit=limit,
            categories=categories,
            price_range=price_range,
            sort="RELEVANCE"
        )
        
        results = await self.search_restaurants(params)
        print(results)
        
        # Additional filtering for dietary restrictions
        # if dietary_restrictions and results.get("results"):
        #     results["results"] = self._filter_by_dietary_restrictions(
        #         results["results"], 
        #         dietary_restrictions
        #     )
        
        return results
    
    def _map_categories_to_ids(self, categories: List[str]) -> List[str]:
        """Map category names to Foursquare category IDs."""
        category_mapping = {
            "restaurant": "13065",
            "fast_food": "13145",
            "cafe": "13032",
            "bar": "13003",
            "italian": "13236",
            "chinese": "13099",
            "mexican": "13303",
            "indian": "13199",
            "japanese": "13263",
            "thai": "13352",
            "american": "13064",
            "pizza": "13064",
            "sushi": "13338"
        }
        
        return [category_mapping.get(cat.lower()) for cat in categories 
                if category_mapping.get(cat.lower())]
    
    def _map_cuisines_to_categories(self, cuisines: List[str]) -> List[str]:
        """Map cuisine preferences to Foursquare categories."""
        cuisine_mapping = {
            "italian": ["italian", "pizza"],
            "chinese": ["chinese"],
            "mexican": ["mexican"],
            "indian": ["indian"],
            "japanese": ["japanese", "sushi"],
            "thai": ["thai"],
            "american": ["american"],
            "fast_food": ["fast_food"],
            "cafe": ["cafe"]
        }
        
        categories = []
        for cuisine in cuisines:
            cuisine_categories = cuisine_mapping.get(cuisine.lower(), [])
            categories.extend(cuisine_categories)
        
        return list(set(categories))  # Remove duplicates
    
    def _filter_by_dietary_restrictions(
        self, 
        restaurants: List[Dict], 
        restrictions: List[str]
    ) -> List[Dict]:
        """Filter restaurants based on dietary restrictions."""
        restriction_keywords = {
            "vegetarian": ["vegetarian", "vegan", "veggie"],
            "vegan": ["vegan"],
            "gluten_free": ["gluten", "celiac"],
            "halal": ["halal"],
            "kosher": ["kosher"]
        }
        
        filtered_restaurants = []
        
        for restaurant in restaurants:
            name = restaurant.get("name", "").lower()
            categories = [cat.get("name", "").lower() 
                         for cat in restaurant.get("categories", [])]
            description = restaurant.get("description", "").lower()
            
            # Check if restaurant matches any dietary restrictions
            matches_restriction = False
            for restriction in restrictions:
                keywords = restriction_keywords.get(restriction.lower(), [])
                for keyword in keywords:
                    if (keyword in name or 
                        any(keyword in cat for cat in categories) or
                        keyword in description):
                        matches_restriction = True
                        break
                if matches_restriction:
                    break
            
            # Include restaurants that either match restrictions or don't have clear dietary info
            if matches_restriction or len(restrictions) == 0:
                filtered_restaurants.append(restaurant)
        
        return filtered_restaurants
    
    async def health_check(self) -> bool:
        """Check if Foursquare API is accessible."""
        if not self.api_key:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"ll": "40.7128,-74.0060", "limit": 1},
                    headers=self.headers,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False


    async def autocomplete_location(self, text: str, types: str = "geo", limit: int = 10) -> Dict:
        """
        Get location autocomplete suggestions.
        
        Args:
            text: Partial location name to search
            types: Types of results (geo, place, address, etc.)
            limit: Maximum number of suggestions
            
        Returns:
            Dict containing autocomplete suggestions
        """
        if not self.api_key:
            raise ValueError("Foursquare API key not configured")
        
        # Use the autocomplete endpoint
        autocomplete_url = f"{settings.foursquare_base_url}/autocomplete"
        
        query_params = {
            "text": text,
            "types": types,
            "limit": limit
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    autocomplete_url,
                    params=query_params,
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Foursquare autocomplete API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Foursquare autocomplete API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in location autocomplete: {str(e)}")
            raise


# Global service instance
foursquare_service = FoursquareService()