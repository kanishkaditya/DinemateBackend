"""
Restaurant API Schemas

Pydantic schemas for restaurant-related API requests and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class SortOrder(str, Enum):
    """Sort order options for restaurant searches."""
    RELEVANCE = "RELEVANCE"
    DISTANCE = "DISTANCE"
    POPULARITY = "POPULARITY"
    RATING = "RATING"
    PRICE_LOW_TO_HIGH = "PRICE_LOW_TO_HIGH"
    PRICE_HIGH_TO_LOW = "PRICE_HIGH_TO_LOW"


class LocationRequest(BaseModel):
    """Location coordinates for search requests."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class RestaurantSearchRequest(BaseModel):
    """Request schema for restaurant search."""
    location: LocationRequest
    radius: int = Field(1000, ge=100, le=10000, description="Search radius in meters")
    limit: int = Field(20, ge=1, le=50, description="Maximum number of results")
    
    # Search query
    query: Optional[str] = Field(None, description="Search query (e.g., 'pizza', 'italian restaurant')")
    
    # Filters
    cuisines: Optional[List[str]] = Field(None, description="Preferred cuisines")
    price_range: Optional[List[int]] = Field(None, description="Price levels (1-4)")
    dietary_restrictions: Optional[List[str]] = Field(None, description="Dietary restrictions")
    features: Optional[List[str]] = Field(None, description="Required features")
    
    # Search options
    open_now: bool = Field(False, description="Only show restaurants open now")
    sort: SortOrder = Field(SortOrder.RELEVANCE, description="Sort order")
    
    @validator('price_range')
    def validate_price_range(cls, v):
        if v is not None:
            for price in v:
                if price not in [1, 2, 3, 4]:
                    raise ValueError('Price levels must be between 1 and 4')
        return v


class RestaurantLocationResponse(BaseModel):
    """Location information in API responses."""
    latitude: float
    longitude: float
    address: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    postcode: Optional[str] = None
    country: str
    formatted_address: Optional[str] = None
    distance: Optional[int] = Field(None, description="Distance from search point in meters")


class RestaurantCategoryResponse(BaseModel):
    """Category information in API responses."""
    id: str = Field(..., description="Foursquare category ID")
    name: str
    icon_url: Optional[str] = None


class RestaurantHoursResponse(BaseModel):
    """Operating hours information."""
    day: int = Field(..., description="Day of week (0=Sunday, 6=Saturday)")
    start: str = Field(..., description="Opening time in HHMM format")
    end: str = Field(..., description="Closing time in HHMM format")


class RestaurantPhotoResponse(BaseModel):
    """Restaurant photo information."""
    id: str
    url: str = Field(..., description="Full photo URL")
    width: Optional[int] = None
    height: Optional[int] = None


class RestaurantReviewResponse(BaseModel):
    """Restaurant review/tip information."""
    id: str
    text: str
    created_at: datetime
    helpful_count: Optional[int] = 0


class RestaurantStatsResponse(BaseModel):
    """Restaurant statistics."""
    total_photos: int = 0
    total_reviews: int = 0
    total_ratings: int = 0


class RestaurantSummaryResponse(BaseModel):
    """Summary restaurant information for search results."""
    fsq_id: str = Field(..., description="Foursquare place ID")
    name: str
    location: RestaurantLocationResponse
    primary_category: Optional[str] = None
    cuisines: List[str] = Field(default_factory=list)
    rating: Optional[float] = Field(None, ge=0, le=10)
    price: Optional[int] = Field(None, ge=1, le=4)
    popularity: Optional[float] = Field(None, ge=0, le=1)
    main_photo_url: Optional[str] = None
    is_open_now: Optional[bool] = None
    recommendation_score: Optional[float] = Field(None, ge=0, le=1)


class RestaurantDetailResponse(BaseModel):
    """Detailed restaurant information."""
    fsq_id: str = Field(..., description="Foursquare place ID")
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    
    location: RestaurantLocationResponse
    categories: List[RestaurantCategoryResponse] = Field(default_factory=list)
    cuisines: List[str] = Field(default_factory=list)
    
    rating: Optional[float] = Field(None, ge=0, le=10)
    price: Optional[int] = Field(None, ge=1, le=4)
    popularity: Optional[float] = Field(None, ge=0, le=1)
    
    hours: List[RestaurantHoursResponse] = Field(default_factory=list)
    is_open_now: Optional[bool] = None
    
    photos: List[RestaurantPhotoResponse] = Field(default_factory=list)
    reviews: List[RestaurantReviewResponse] = Field(default_factory=list)
    
    features: List[str] = Field(default_factory=list)
    dietary_options: List[str] = Field(default_factory=list)
    social_media: Dict[str, str] = Field(default_factory=dict)
    
    stats: Optional[RestaurantStatsResponse] = None
    menu_url: Optional[str] = None
    has_menu: bool = False
    
    recommendation_score: Optional[float] = Field(None, ge=0, le=1)
    created_at: datetime
    updated_at: datetime


class RestaurantSearchResponse(BaseModel):
    """Response schema for restaurant search."""
    results: List[RestaurantSummaryResponse]
    total: int = Field(..., description="Total number of results")
    search_params: Dict[str, Any] = Field(..., description="Search parameters used")
    location: LocationRequest = Field(..., description="Search location")
    radius: int = Field(..., description="Search radius in meters")


class GroupRecommendationRequest(BaseModel):
    """Request schema for group-based restaurant recommendations."""
    group_id: str = Field(..., description="Group ID to get preferences for")
    location: LocationRequest
    radius: int = Field(1000, ge=100, le=10000, description="Search radius in meters")
    limit: int = Field(20, ge=1, le=50, description="Maximum number of results")
    
    # Override options
    override_cuisines: Optional[List[str]] = Field(None, description="Override group cuisine preferences")
    override_price_range: Optional[List[int]] = Field(None, description="Override group price preferences")
    open_now: bool = Field(False, description="Only show restaurants open now")
    sort: SortOrder = Field(SortOrder.RELEVANCE, description="Sort order")


class GroupRecommendationResponse(BaseModel):
    """Response schema for group-based recommendations."""
    results: List[RestaurantSummaryResponse]
    total: int
    group_id: str
    group_preferences: Dict[str, Any] = Field(..., description="Group preferences used")
    search_params: Dict[str, Any] = Field(..., description="Search parameters used")
    location: LocationRequest
    radius: int



class PopularRestaurantsRequest(BaseModel):
    """Request for popular restaurants in an area."""
    location: LocationRequest
    radius: int = Field(2000, ge=100, le=10000, description="Search radius in meters")
    limit: int = Field(20, ge=1, le=50, description="Maximum number of results")
    time_period: str = Field("week", description="Time period for popularity calculation")


class NearbyRestaurantsRequest(BaseModel):
    """Simple request for nearby restaurants."""
    location: LocationRequest
    radius: int = Field(1000, ge=100, le=5000, description="Search radius in meters")
    limit: int = Field(20, ge=1, le=30, description="Maximum number of results")


class RestaurantPhotosResponse(BaseModel):
    """Response for restaurant photos endpoint."""
    fsq_id: str
    photos: List[RestaurantPhotoResponse]
    total: int


class RestaurantReviewsResponse(BaseModel):
    """Response for restaurant reviews endpoint."""
    fsq_id: str
    reviews: List[RestaurantReviewResponse]
    total: int


class RestaurantStatusResponse(BaseModel):
    """Status information for restaurant data."""
    fsq_id: str
    last_updated: datetime
    data_freshness: str = Field(..., description="How fresh the data is (e.g., 'fresh', 'stale', 'expired')")
    needs_sync: bool = Field(..., description="Whether data needs to be synced with Foursquare")


class BulkRestaurantRequest(BaseModel):
    """Request for bulk restaurant operations."""
    fsq_ids: List[str] = Field(..., description="List of Foursquare place IDs")
    include_photos: bool = Field(False, description="Include photo data")
    include_reviews: bool = Field(False, description="Include review data")


class BulkRestaurantResponse(BaseModel):
    """Response for bulk restaurant operations."""
    restaurants: List[RestaurantDetailResponse]
    total: int
    errors: List[Dict[str, str]] = Field(default_factory=list, description="Errors for failed requests")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None