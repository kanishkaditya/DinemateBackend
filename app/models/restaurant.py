"""
Restaurant Model

Database model for storing restaurant information from Foursquare API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from beanie import Document
from pydantic import Field


class RestaurantLocation(Document):
    """Restaurant location and address information."""
    
    latitude: float
    longitude: float
    address: Optional[str] = None
    locality: Optional[str] = None  # City
    region: Optional[str] = None    # State/Province
    postcode: Optional[str] = None
    country: str
    formatted_address: Optional[str] = None
    
    class Settings:
        collection = "restaurant_locations"


class RestaurantCategory(Document):
    """Restaurant category information."""
    
    fsq_category_id: str = Field(..., description="Foursquare category ID")
    name: str
    icon_url: Optional[str] = None
    
    class Settings:
        collection = "restaurant_categories"


class RestaurantHours(Document):
    """Restaurant operating hours."""
    
    day: int = Field(..., description="Day of week (0=Sunday, 6=Saturday)")
    start: str = Field(..., description="Opening time in HHMM format")
    end: str = Field(..., description="Closing time in HHMM format")
    
    class Settings:
        collection = "restaurant_hours"


class RestaurantPhoto(Document):
    """Restaurant photo information."""
    
    photo_id: str = Field(..., description="Foursquare photo ID")
    prefix: str = Field(..., description="Photo URL prefix")
    suffix: str = Field(..., description="Photo URL suffix")
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: Optional[datetime] = None
    
    class Settings:
        collection = "restaurant_photos"


class RestaurantReview(Document):
    """Restaurant review/tip information."""
    
    tip_id: str = Field(..., description="Foursquare tip ID")
    text: str
    created_at: datetime
    agree_count: Optional[int] = 0
    disagree_count: Optional[int] = 0
    
    class Settings:
        collection = "restaurant_reviews"


class RestaurantStats(Document):
    """Restaurant statistics and metrics."""
    
    total_photos: Optional[int] = 0
    total_tips: Optional[int] = 0
    total_ratings: Optional[int] = 0
    
    class Settings:
        collection = "restaurant_stats"


class Restaurant(Document):
    """Main restaurant document model."""
    
    # Foursquare identifiers
    fsq_id: str = Field(..., unique=True, description="Foursquare place ID")
    
    # Basic information
    name: str = Field(..., index=True)
    description: Optional[str] = None
    website: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    
    # Location
    location: RestaurantLocation
    distance: Optional[int] = Field(None, description="Distance from search point in meters")
    
    # Categories and cuisine
    categories: List[RestaurantCategory] = Field(default_factory=list)
    primary_category: Optional[str] = None  # Derived from categories
    cuisine_types: List[str] = Field(default_factory=list)  # Simplified cuisine tags
    
    # Ratings and pricing
    rating: Optional[float] = Field(None, ge=0, le=10)
    price: Optional[int] = Field(None, ge=1, le=4, description="Price level 1-4")
    popularity: Optional[float] = Field(None, ge=0, le=1)
    
    # Operating information
    hours: List[RestaurantHours] = Field(default_factory=list)
    is_open_now: Optional[bool] = None
    date_closed: Optional[datetime] = None  # If permanently closed
    
    # Media and reviews
    photos: List[RestaurantPhoto] = Field(default_factory=list)
    reviews: List[RestaurantReview] = Field(default_factory=list)
    main_photo_url: Optional[str] = None  # Cached main photo URL
    
    # Features and amenities
    features: List[str] = Field(default_factory=list)  # e.g., ["wifi", "outdoor_seating"]
    dietary_options: List[str] = Field(default_factory=list)  # e.g., ["vegetarian", "vegan"]
    
    # Social media and external links
    social_media: Dict[str, str] = Field(default_factory=dict)  # e.g., {"instagram": "url"}
    
    # Statistics
    stats: Optional[RestaurantStats] = None
    
    # Menu information (if available)
    menu_url: Optional[str] = None
    has_menu: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_synced_at: Optional[datetime] = None  # Last time synced with Foursquare
    
    # Search and recommendation metadata
    search_tags: List[str] = Field(default_factory=list)  # For improved search
    recommendation_score: Optional[float] = None  # Calculated recommendation score
    
    class Settings:
        collection = "restaurants"
        indexes = [
            "fsq_id",
            "name",
            "location.latitude",
            "location.longitude", 
            "primary_category",
            "rating",
            "price",
            "popularity",
            "cuisine_types",
            "created_at"
        ]
    
    def __str__(self) -> str:
        return f"Restaurant(name='{self.name}', fsq_id='{self.fsq_id}')"
    
    def get_full_address(self) -> str:
        """Get formatted full address."""
        if self.location.formatted_address:
            return self.location.formatted_address
        
        parts = []
        if self.location.address:
            parts.append(self.location.address)
        if self.location.locality:
            parts.append(self.location.locality)
        if self.location.region:
            parts.append(self.location.region)
        if self.location.postcode:
            parts.append(self.location.postcode)
        
        return ", ".join(parts) if parts else "Address not available"
    
    def get_primary_cuisine(self) -> Optional[str]:
        """Get the primary cuisine type."""
        return self.cuisine_types[0] if self.cuisine_types else None
    
    def has_dietary_option(self, dietary_restriction: str) -> bool:
        """Check if restaurant supports a specific dietary restriction."""
        return dietary_restriction.lower() in [opt.lower() for opt in self.dietary_options]
    
    def is_within_price_range(self, min_price: int, max_price: int) -> bool:
        """Check if restaurant is within specified price range."""
        if self.price is None:
            return True  # Include restaurants without price info
        return min_price <= self.price <= max_price
    
    def get_main_photo_url(self, size: str = "300x300") -> Optional[str]:
        """Get URL for main restaurant photo."""
        if self.main_photo_url:
            return self.main_photo_url
        
        if self.photos:
            photo = self.photos[0]
            return f"{photo.prefix}{size}{photo.suffix}"
        
        return None
    
    def calculate_recommendation_score(
        self, 
        user_preferences: Dict[str, Any],
        distance_weight: float = 0.3,
        rating_weight: float = 0.4, 
        popularity_weight: float = 0.3
    ) -> float:
        """Calculate recommendation score based on preferences and restaurant data."""
        score = 0.0
        
        # Distance score (closer is better)
        if self.distance is not None:
            # Normalize distance to 0-1 scale (max 2km)
            distance_score = max(0, 1 - (self.distance / 2000))
            score += distance_score * distance_weight
        
        # Rating score
        if self.rating is not None:
            # Normalize rating from 0-10 to 0-1 scale
            rating_score = self.rating / 10
            score += rating_score * rating_weight
        
        # Popularity score
        if self.popularity is not None:
            score += self.popularity * popularity_weight
        
        # Additional preference-based scoring could be added here
        # e.g., cuisine preferences, price preferences, dietary restrictions
        
        return min(1.0, score)  # Cap at 1.0
    
    async def update_from_foursquare_data(self, foursquare_data: Dict[str, Any]):
        """Update restaurant data from Foursquare API response."""
        # Update basic fields
        self.name = foursquare_data.get("name", self.name)
        self.description = foursquare_data.get("description")
        self.website = foursquare_data.get("website")
        self.tel = foursquare_data.get("tel")
        self.email = foursquare_data.get("email")
        
        # Update location
        if "location" in foursquare_data:
            loc_data = foursquare_data["location"]
            self.location.latitude = loc_data.get("lat", self.location.latitude)
            self.location.longitude = loc_data.get("lng", self.location.longitude)
            self.location.address = loc_data.get("address")
            self.location.locality = loc_data.get("locality")
            self.location.region = loc_data.get("region")
            self.location.postcode = loc_data.get("postcode")
            self.location.country = loc_data.get("country", self.location.country)
            self.location.formatted_address = loc_data.get("formatted_address")
        
        # Update other fields
        self.rating = foursquare_data.get("rating")
        self.price = foursquare_data.get("price")
        self.popularity = foursquare_data.get("popularity")
        self.distance = foursquare_data.get("distance")
        
        # Update categories
        if "categories" in foursquare_data:
            self.categories = []
            for cat_data in foursquare_data["categories"]:
                category = RestaurantCategory(
                    fsq_category_id=cat_data.get("id", ""),
                    name=cat_data.get("name", ""),
                    icon_url=cat_data.get("icon", {}).get("url")
                )
                self.categories.append(category)
            
            # Set primary category
            if self.categories:
                self.primary_category = self.categories[0].name
        
        # Update metadata
        self.updated_at = datetime.utcnow()
        self.last_synced_at = datetime.utcnow()
        
        await self.save()


class RestaurantSearchCache(Document):
    """Cache for restaurant search results to improve performance."""
    
    search_key: str = Field(..., unique=True, description="Hash of search parameters")
    location_lat: float
    location_lng: float
    radius: int
    filters: Dict[str, Any] = Field(default_factory=dict)
    
    restaurant_ids: List[str] = Field(default_factory=list)  # FSQ IDs
    total_results: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Cache expiration time")
    
    class Settings:
        collection = "restaurant_search_cache"
        indexes = [
            "search_key",
            "expires_at",
            "location_lat",
            "location_lng"
        ]