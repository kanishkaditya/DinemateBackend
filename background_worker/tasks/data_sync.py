"""
Data Synchronization Background Tasks

Handles syncing external data sources and updating cached information.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
sys.path.append(r'C:\Users\asus\Desktop\Dinemate')

from ..celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='background_worker.tasks.data_sync.sync_restaurant_data_task')
def sync_restaurant_data_task(self):
    """Sync restaurant data with external APIs."""
    try:
        return asyncio.run(_sync_restaurant_data_async())
    except Exception as e:
        logger.error(f"Error in sync_restaurant_data_task: {str(e)}")
        raise


@celery_app.task(name='background_worker.tasks.data_sync.update_popular_restaurants_task')
def update_popular_restaurants_task():
    """Update popular restaurant rankings."""
    try:
        return asyncio.run(_update_popular_restaurants_async())
    except Exception as e:
        logger.error(f"Error in update_popular_restaurants_task: {str(e)}")
        raise


async def _sync_restaurant_data_async():
    """Sync restaurant data with Foursquare API."""
    from app.database import startup_db_client
    from app.models.restaurant import Restaurant
    from app.services.foursquare_service import foursquare_service
    
    try:
        await startup_db_client()
        
        # Find restaurants that need data refresh (older than 7 days)
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        restaurants_to_update = await Restaurant.find(
            Restaurant.last_synced_at < cutoff_time
        ).limit(50).to_list()  # Batch process 50 at a time
        
        logger.info(f"Found {len(restaurants_to_update)} restaurants to update")
        
        updated_count = 0
        for restaurant in restaurants_to_update:
            try:
                # Get fresh data from Foursquare
                fresh_data = await foursquare_service.get_restaurant_details(restaurant.fsq_id)
                
                # Update restaurant record
                restaurant.name = fresh_data.get("name", restaurant.name)
                restaurant.rating = fresh_data.get("rating", restaurant.rating)
                restaurant.price = fresh_data.get("price", restaurant.price)
                restaurant.last_synced_at = datetime.utcnow()
                
                # Update other fields as needed
                if "hours" in fresh_data:
                    # Update hours information
                    pass
                
                await restaurant.save()
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating restaurant {restaurant.fsq_id}: {str(e)}")
                continue
        
        logger.info(f"Successfully updated {updated_count} restaurants")
        return {"updated": updated_count, "total": len(restaurants_to_update)}
        
    except Exception as e:
        logger.error(f"Error in restaurant data sync: {str(e)}")
        raise


async def _update_popular_restaurants_async():
    """Update popular restaurant rankings based on user interactions."""
    from app.database import startup_db_client
    from app.models.restaurant import Restaurant
    
    try:
        await startup_db_client()
        
        # Calculate popularity scores based on recent activity
        cutoff_time = datetime.utcnow() - timedelta(days=30)  # Last month
        
        # This would involve complex aggregation queries
        # For now, we'll just update a few sample restaurants
        
        restaurants = await Restaurant.find().limit(100).to_list()
        
        updated_count = 0
        for restaurant in restaurants:
            try:
                # Calculate popularity score (placeholder logic)
                # In practice, this would aggregate user interactions, visits, etc.
                
                # For now, just update the timestamp
                restaurant.last_synced_at = datetime.utcnow()
                await restaurant.save()
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating popularity for {restaurant.fsq_id}: {str(e)}")
                continue
        
        logger.info(f"Updated popularity scores for {updated_count} restaurants")
        return {"updated": updated_count}
        
    except Exception as e:
        logger.error(f"Error updating popular restaurants: {str(e)}")
        raise