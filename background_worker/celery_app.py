"""
Celery Application Configuration

Central configuration for all background processing tasks.
"""

import os
from celery import Celery
from celery.schedules import crontab
from shared.config import shared_config

# Initialize Celery
celery_app = Celery(
    'dinemate_background_worker',
    broker=shared_config.REDIS_URL,
    backend=shared_config.REDIS_URL,
    include=[
        'background_worker.tasks.message_analysis',
        'background_worker.tasks.data_sync',
        'background_worker.tasks.maintenance'
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Windows-specific configuration
    worker_pool='threads',  # Use threads pool for Windows compatibility
    worker_concurrency=1,  # Single worker to avoid permission issues
)

# Schedule configuration - Only maintenance and batch processing tasks
celery_app.conf.beat_schedule = {
    # MAINTENANCE TASKS (Keep as scheduled)
    'cleanup-expired-cache': {
        'task': 'background_worker.tasks.maintenance.cleanup_expired_cache_task',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    'health-check-services': {
        'task': 'background_worker.tasks.maintenance.health_check_services_task',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes (reduced frequency)
    },
    
    # DATA SYNC TASKS (Keep as scheduled - not event-driven)
    'sync-restaurant-data': {
        'task': 'background_worker.tasks.data_sync.sync_restaurant_data_task',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'update-popular-restaurants': {
        'task': 'background_worker.tasks.data_sync.update_popular_restaurants_task',
        'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
    },
    
    # ANALYTICS TASKS (Keep as scheduled - aggregate analysis)
    'analyze-group-trends': {
        'task': 'background_worker.tasks.message_analysis.analyze_group_trends_task',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    'process-stale-preferences': {
        'task': 'background_worker.tasks.message_analysis.process_stale_preferences_task',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM
    },
    
    # BACKUP TASK (Fallback for missed real-time analysis)
    'analyze-missed-messages': {
        'task': 'background_worker.tasks.message_analysis.analyze_new_messages_task',
        'schedule': crontab(hour='*/6'),  # Every 6 hours as backup only
    },
}

celery_app.conf.timezone = 'UTC'