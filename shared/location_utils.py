"""
Location Utilities

Shared utilities for location-based operations and calculations.
"""

import math
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass


@dataclass
class Coordinates:
    """Geographic coordinates."""
    latitude: float
    longitude: float
    
    def __post_init__(self):
        """Validate coordinates."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}. Must be between -90 and 90.")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}. Must be between -180 and 180.")


@dataclass
class BoundingBox:
    """Geographic bounding box."""
    north: float
    south: float
    east: float
    west: float


class LocationUtils:
    """Utility class for location-based calculations."""
    
    EARTH_RADIUS_KM = 6371.0
    EARTH_RADIUS_METERS = 6371000.0
    
    @staticmethod
    def haversine_distance(
        lat1: float, lon1: float, 
        lat2: float, lon2: float, 
        unit: str = "meters"
    ) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Args:
            lat1, lon1: Latitude and longitude of point 1
            lat2, lon2: Latitude and longitude of point 2
            unit: Unit of measurement ("meters", "kilometers", "miles")
            
        Returns:
            Distance between the two points
        """
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # Distance in kilometers
        distance_km = LocationUtils.EARTH_RADIUS_KM * c
        
        # Convert to requested unit
        if unit == "kilometers":
            return distance_km
        elif unit == "meters":
            return distance_km * 1000
        elif unit == "miles":
            return distance_km * 0.621371
        else:
            raise ValueError(f"Unsupported unit: {unit}")
    
    @staticmethod
    def calculate_bounding_box(
        center_lat: float, 
        center_lon: float, 
        radius_meters: int
    ) -> BoundingBox:
        """
        Calculate bounding box for a given center point and radius.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_meters: Radius in meters
            
        Returns:
            BoundingBox object with north, south, east, west coordinates
        """
        # Convert radius from meters to degrees (approximate)
        radius_km = radius_meters / 1000.0
        lat_delta = radius_km / 111.0  # Roughly 111 km per degree of latitude
        
        # Longitude delta varies with latitude
        lon_delta = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        
        return BoundingBox(
            north=center_lat + lat_delta,
            south=center_lat - lat_delta,
            east=center_lon + lon_delta,
            west=center_lon - lon_delta
        )
    
    @staticmethod
    def is_within_radius(
        center_lat: float, center_lon: float,
        point_lat: float, point_lon: float,
        radius_meters: int
    ) -> bool:
        """
        Check if a point is within a given radius of a center point.
        
        Args:
            center_lat, center_lon: Center point coordinates
            point_lat, point_lon: Point to check coordinates
            radius_meters: Radius in meters
            
        Returns:
            True if point is within radius, False otherwise
        """
        distance = LocationUtils.haversine_distance(
            center_lat, center_lon, point_lat, point_lon, "meters"
        )
        return distance <= radius_meters
    
    @staticmethod
    def get_midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> Coordinates:
        """
        Calculate the midpoint between two geographic coordinates.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Coordinates of the midpoint
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Calculate differences
        dlon = lon2_rad - lon1_rad
        
        # Calculate midpoint
        bx = math.cos(lat2_rad) * math.cos(dlon)
        by = math.cos(lat2_rad) * math.sin(dlon)
        
        mid_lat_rad = math.atan2(
            math.sin(lat1_rad) + math.sin(lat2_rad),
            math.sqrt((math.cos(lat1_rad) + bx) ** 2 + by ** 2)
        )
        mid_lon_rad = lon1_rad + math.atan2(by, math.cos(lat1_rad) + bx)
        
        # Convert back to degrees
        mid_lat = math.degrees(mid_lat_rad)
        mid_lon = math.degrees(mid_lon_rad)
        
        return Coordinates(latitude=mid_lat, longitude=mid_lon)
    
    @staticmethod
    def sort_by_distance(
        center_lat: float, center_lon: float,
        locations: List[Dict[str, Any]],
        lat_key: str = "latitude",
        lon_key: str = "longitude"
    ) -> List[Dict[str, Any]]:
        """
        Sort a list of locations by distance from a center point.
        
        Args:
            center_lat, center_lon: Center point coordinates
            locations: List of location dictionaries
            lat_key: Key name for latitude in location dictionaries
            lon_key: Key name for longitude in location dictionaries
            
        Returns:
            Sorted list of locations with distance added
        """
        # Calculate distances and add to each location
        for location in locations:
            distance = LocationUtils.haversine_distance(
                center_lat, center_lon,
                location[lat_key], location[lon_key],
                "meters"
            )
            location["distance"] = distance
        
        # Sort by distance
        return sorted(locations, key=lambda x: x["distance"])
    
    @staticmethod
    def filter_by_radius(
        center_lat: float, center_lon: float,
        locations: List[Dict[str, Any]],
        radius_meters: int,
        lat_key: str = "latitude",
        lon_key: str = "longitude"
    ) -> List[Dict[str, Any]]:
        """
        Filter locations to only include those within a given radius.
        
        Args:
            center_lat, center_lon: Center point coordinates
            locations: List of location dictionaries
            radius_meters: Radius in meters
            lat_key: Key name for latitude in location dictionaries
            lon_key: Key name for longitude in location dictionaries
            
        Returns:
            Filtered list of locations within radius
        """
        filtered_locations = []
        
        for location in locations:
            if LocationUtils.is_within_radius(
                center_lat, center_lon,
                location[lat_key], location[lon_key],
                radius_meters
            ):
                filtered_locations.append(location)
        
        return filtered_locations
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """
        Validate geographic coordinates.
        
        Args:
            latitude: Latitude value
            longitude: Longitude value
            
        Returns:
            True if coordinates are valid, False otherwise
        """
        try:
            Coordinates(latitude=latitude, longitude=longitude)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def normalize_longitude(longitude: float) -> float:
        """
        Normalize longitude to be within -180 to 180 degrees.
        
        Args:
            longitude: Longitude value
            
        Returns:
            Normalized longitude
        """
        while longitude > 180:
            longitude -= 360
        while longitude < -180:
            longitude += 360
        return longitude
    
    @staticmethod
    def get_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the bearing (direction) from point 1 to point 2.
        
        Args:
            lat1, lon1: Starting point coordinates
            lat2, lon2: Ending point coordinates
            
        Returns:
            Bearing in degrees (0-360, where 0 is north)
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        # Normalize to 0-360 degrees
        return (bearing_deg + 360) % 360
    
    @staticmethod
    def get_destination_point(
        lat: float, lon: float, 
        bearing_degrees: float, 
        distance_meters: float
    ) -> Coordinates:
        """
        Calculate destination point given start point, bearing, and distance.
        
        Args:
            lat, lon: Starting point coordinates
            bearing_degrees: Bearing in degrees
            distance_meters: Distance in meters
            
        Returns:
            Destination coordinates
        """
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing_degrees)
        distance_km = distance_meters / 1000.0
        
        # Calculate destination
        angular_distance = distance_km / LocationUtils.EARTH_RADIUS_KM
        
        dest_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(angular_distance) +
            math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
        )
        
        dest_lon_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
            math.cos(angular_distance) - math.sin(lat_rad) * math.sin(dest_lat_rad)
        )
        
        dest_lat = math.degrees(dest_lat_rad)
        dest_lon = math.degrees(dest_lon_rad)
        dest_lon = LocationUtils.normalize_longitude(dest_lon)
        
        return Coordinates(latitude=dest_lat, longitude=dest_lon)
    
    @staticmethod
    def create_grid_points(
        center_lat: float, center_lon: float,
        radius_meters: int, grid_size: int = 3
    ) -> List[Coordinates]:
        """
        Create a grid of points around a center location.
        
        Args:
            center_lat, center_lon: Center point coordinates
            radius_meters: Radius for the grid
            grid_size: Number of points per side (e.g., 3x3 grid)
            
        Returns:
            List of grid point coordinates
        """
        grid_points = []
        
        # Calculate step size
        step_distance = (radius_meters * 2) / (grid_size - 1)
        
        # Start from southwest corner
        start_bearing = 225  # Southwest
        start_distance = radius_meters * math.sqrt(2)  # Diagonal distance
        start_point = LocationUtils.get_destination_point(
            center_lat, center_lon, start_bearing, start_distance
        )
        
        for i in range(grid_size):
            for j in range(grid_size):
                # Calculate bearing and distance from start point
                east_distance = j * step_distance
                north_distance = i * step_distance
                
                # Move east from start point
                east_point = LocationUtils.get_destination_point(
                    start_point.latitude, start_point.longitude, 90, east_distance
                )
                
                # Move north from that point
                final_point = LocationUtils.get_destination_point(
                    east_point.latitude, east_point.longitude, 0, north_distance
                )
                
                grid_points.append(final_point)
        
        return grid_points


class AddressUtils:
    """Utilities for address formatting and parsing."""
    
    @staticmethod
    def format_address(
        address: str = None,
        locality: str = None,
        region: str = None,
        postcode: str = None,
        country: str = None
    ) -> str:
        """
        Format address components into a readable address string.
        
        Args:
            address: Street address
            locality: City/locality
            region: State/region
            postcode: Postal code
            country: Country
            
        Returns:
            Formatted address string
        """
        parts = []
        
        if address:
            parts.append(address)
        if locality:
            parts.append(locality)
        if region:
            parts.append(region)
        if postcode:
            parts.append(postcode)
        if country:
            parts.append(country)
        
        return ", ".join(parts)
    
    @staticmethod
    def extract_city_from_address(formatted_address: str) -> str:
        """
        Extract city name from a formatted address.
        
        Args:
            formatted_address: Full formatted address
            
        Returns:
            Extracted city name or empty string
        """
        if not formatted_address:
            return ""
        
        # Simple extraction - assumes city is second component
        parts = [part.strip() for part in formatted_address.split(",")]
        
        if len(parts) >= 2:
            return parts[1]
        
        return ""
    
    @staticmethod
    def get_short_address(formatted_address: str, max_length: int = 50) -> str:
        """
        Get a shortened version of an address.
        
        Args:
            formatted_address: Full formatted address
            max_length: Maximum length of shortened address
            
        Returns:
            Shortened address
        """
        if not formatted_address:
            return ""
        
        if len(formatted_address) <= max_length:
            return formatted_address
        
        # Try to keep first two components
        parts = [part.strip() for part in formatted_address.split(",")]
        
        if len(parts) >= 2:
            short_address = f"{parts[0]}, {parts[1]}"
            if len(short_address) <= max_length:
                return short_address
        
        # Fallback to truncation
        return formatted_address[:max_length - 3] + "..."


# Global utility instances
location_utils = LocationUtils()
address_utils = AddressUtils()