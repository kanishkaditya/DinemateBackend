"""
Maintenance Background Tasks

Handles system maintenance, cleanup, and health monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
sys.path.append(r'C:\Users\asus\Desktop\Dinemate')
from ..celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='background_worker.tasks.maintenance.cleanup_expired_cache_task')
def cleanup_expired_cache_task():
    """Clean up expired cache entries."""
    try:
        return asyncio.run(_cleanup_expired_cache_async())
    except Exception as e:
        logger.error(f"Error in cleanup_expired_cache_task: {str(e)}")
        raise


@celery_app.task(name='background_worker.tasks.maintenance.health_check_services_task')
def health_check_services_task():
    """Check health of external services."""
    try:
        return asyncio.run(_health_check_services_async())
    except Exception as e:
        logger.error(f"Error in health_check_services_task: {str(e)}")
        raise


async def _cleanup_expired_cache_async():
    """Remove expired cache entries from the database."""
    from app.database import startup_db_client
    from app.models.restaurant import RestaurantSearchCache
    
    try:
        await startup_db_client()
        
        # Remove cache entries older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Find expired cache entries
        expired_cache = await RestaurantSearchCache.find(
            RestaurantSearchCache.created_at < cutoff_time
        ).to_list()
        
        deleted_count = 0
        for cache_entry in expired_cache:
            try:
                await cache_entry.delete()
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting cache entry {cache_entry.id}: {str(e)}")
                continue
        
        logger.info(f"Cleaned up {deleted_count} expired cache entries")
        return {"deleted": deleted_count, "total": len(expired_cache)}
        
    except Exception as e:
        logger.error(f"Error in cache cleanup: {str(e)}")
        raise


async def _health_check_services_async():
    """Check health of external services and log status."""
    from app.services.foursquare_service import foursquare_service
    import redis
    from shared.config import shared_config
    
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    try:
        # Check Foursquare API
        try:
            foursquare_healthy = await foursquare_service.health_check()
            health_status["services"]["foursquare"] = {
                "status": "healthy" if foursquare_healthy else "unhealthy",
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            health_status["services"]["foursquare"] = {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
        
        # Check Redis
        try:
            r = redis.from_url(shared_config.REDIS_URL)
            r.ping()
            health_status["services"]["redis"] = {
                "status": "healthy",
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
        
        # Check MongoDB
        try:
            from app.database import startup_db_client, get_database
            await startup_db_client()
            db = await get_database()
            # Simple ping to check connectivity
            health_status["services"]["mongodb"] = {
                "status": "healthy",
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            health_status["services"]["mongodb"] = {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
        
        # Log overall health status
        unhealthy_services = [
            name for name, status in health_status["services"].items() 
            if status["status"] != "healthy"
        ]
        
        if unhealthy_services:
            logger.warning(f"Unhealthy services detected: {', '.join(unhealthy_services)}")
        else:
            logger.info("All services are healthy")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        raise