from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import Optional, List

from ...services.restaurant_service import restaurant_service
from ...models.user import User
from ...schemas.restaurant import (
    RestaurantSearchRequest, RestaurantSearchResponse,
    RestaurantDetailResponse, RestaurantSummaryResponse,
    GroupRecommendationRequest, GroupRecommendationResponse,
    NearbyRestaurantsRequest, LocationRequest,
    ErrorResponse
)

# Create router
router = APIRouter(tags=["restaurants"])


@router.get("/locations/autocomplete")
async def autocomplete_locations(
    text: str = Query(..., description="Partial location name to search for"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions")
):
    """Get location autocomplete suggestions for place names."""
    try:
        from ...services.foursquare_service import foursquare_service
        
        results = await foursquare_service.autocomplete_location(text=text, limit=limit)
        
        # Format results for easier consumption
        suggestions = []
        for result in results.get("results", []):
            suggestions.append({
                "name": result.get("text", {}).get("primary", ""),
                "secondary": result.get("text", {}).get("secondary", ""),
                "type": result.get("type", ""),
                "coordinates": result.get("geo", {})
            })
        
        return {
            "suggestions": suggestions,
            "total": len(suggestions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Location autocomplete failed: {str(e)}")


@router.get("/groups/{group_id}/recommendations")
async def get_group_recommendations(
    group_id: str,
    latitude: float = Query(..., description="Current latitude"),
    longitude: float = Query(..., description="Current longitude"),
    radius: int = Query(2000, ge=500, le=10000, description="Search radius in meters")
):
    """Get restaurant recommendations based on current location and group preferences."""
    try:
        results = await restaurant_service.get_group_recommendations(
            group_id=group_id,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Group recommendations failed: {str(e)}")


@router.post("/search")
async def search_restaurants(request: RestaurantSearchRequest):
    """Search for restaurants based on location and filters."""
    try:
        results = await restaurant_service.search_restaurants(request)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/nearby")
async def get_nearby_restaurants(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
    radius: int = Query(1000, ge=100, le=5000, description="Search radius in meters"),
    limit: int = Query(20, ge=1, le=50, description="Number of results to return")
):
    """Get nearby restaurants."""
    try:
        results = await restaurant_service.get_nearby_restaurants(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            limit=limit
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nearby search failed: {str(e)}")


@router.get("/{fsq_id}")
async def get_restaurant_details(fsq_id: str = Path(..., description="Foursquare place ID")):
    """Get detailed information about a specific restaurant from Foursquare API."""
    try:
        restaurant = await restaurant_service.get_restaurant_details(fsq_id)
        
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        
        return restaurant
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get restaurant details: {str(e)}")


@router.get("/health")
async def health_check():
    """Check restaurant service health."""
    try:
        health_status = await restaurant_service.health_check()
        
        if health_status["overall"]:
            return health_status
        else:
            raise HTTPException(status_code=503, detail=health_status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")