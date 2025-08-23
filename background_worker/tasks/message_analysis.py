"""
Message Analysis Background Tasks

Handles LLM-based analysis of group chat messages for preference learning.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..celery_app import celery_app
from llm_service.langgraph_analyzer import langgraph_analyzer
import sys
sys.path.append(r'C:\Users\asus\Desktop\Dinemate')

logger = logging.getLogger(__name__)


@celery_app.task(name='background_worker.tasks.message_analysis.analyze_single_message_task')
def analyze_single_message_task(message_id: str, group_id: str, user_id: str, message_content: str):
    """Real-time analysis of a single message when it's sent."""
    try:
        return asyncio.run(_analyze_single_message_async(message_id, group_id, user_id, message_content))
    except Exception as e:
        logger.error(f"Error in analyze_single_message_task: {str(e)}")
        raise


@celery_app.task(name='background_worker.tasks.message_analysis.analyze_new_messages_task')
def analyze_new_messages_task():
    """Fallback batch analysis for any missed messages (backup only)."""
    try:
        # Run the async function in the event loop
        return asyncio.run(_analyze_new_messages_async())
    except Exception as e:
        logger.error(f"Error in analyze_new_messages_task: {str(e)}")
        raise


@celery_app.task(bind=True, name='background_worker.tasks.message_analysis.analyze_group_preferences_task')
def analyze_group_preferences_task(self, group_id: str):
    """Celery task wrapper for analyzing group preferences."""
    try:
        return asyncio.run(_analyze_group_preferences_async(self, group_id))
    except Exception as e:
        logger.error(f"Error in analyze_group_preferences_task: {str(e)}")
        raise


@celery_app.task(name='background_worker.tasks.message_analysis.analyze_group_trends_task')
def analyze_group_trends_task():
    """Analyze trends across all groups."""
    try:
        return asyncio.run(_analyze_group_trends_async())
    except Exception as e:
        logger.error(f"Error in analyze_group_trends_task: {str(e)}")
        raise


@celery_app.task(name='background_worker.tasks.message_analysis.process_stale_preferences_task')
def process_stale_preferences_task():
    """Process and update stale user preferences."""
    try:
        return asyncio.run(_process_stale_preferences_async())
    except Exception as e:
        logger.error(f"Error in process_stale_preferences_task: {str(e)}")
        raise


async def _analyze_single_message_async(message_id: str, group_id: str, user_id: str, message_content: str):
    """Real-time analysis of a single message."""
    from app.database import startup_db_client
    
    try:
        await startup_db_client()
        
        logger.info(f"Analyzing message {message_id} from user {user_id} in group {group_id}")
        
        # Create user context for analysis
        user_context = {
            "message_id": message_id,
            "user_id": user_id,
            "group_id": group_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Analyze the message using LangGraph
        analysis_result = await langgraph_analyzer.analyze_message(
            message_content,
            user_context
        )
        
        logger.info(f"Analysis completed for message {message_id}, relevance: {analysis_result.get('overall_relevance', 0)}")
        
        # Process the analysis results immediately
        if analysis_result.get("should_update_preferences", False):
            await _update_user_preferences_from_analysis(
                group_id,
                user_id,
                analysis_result
            )
        
        return {
            "message_id": message_id,
            "analyzed": True,
            "preferences_updated": analysis_result.get("should_update_preferences", False),
            "relevance_score": analysis_result.get("overall_relevance", 0)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing single message {message_id}: {str(e)}")
        raise


async def _analyze_new_messages_async():
    """Async implementation of new message analysis."""
    # Import here to avoid circular imports
    from app.database import startup_db_client
    from app.models.group import ChatMessage
    
    try:
        await startup_db_client()
        
        # Find messages from last 10 minutes that haven't been analyzed
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)
        
        # This is a placeholder - in practice you'd have a field to track analyzed messages
        messages = await ChatMessage.find(
            ChatMessage.created_at >= cutoff_time,
            ChatMessage.message_type == "text"
        ).to_list()
        
        logger.info(f"Found {len(messages)} new messages to analyze")
        
        analyzed_count = 0
        for message in messages:
            try:
                # Create user context for analysis
                user_context = {
                    "message_id": str(message.id),
                    "user_id": message.user_id,
                    "group_id": message.group_id,
                    "timestamp": message.created_at.isoformat()
                }
                
                # Analyze the message using LangGraph
                analysis_result = await langgraph_analyzer.analyze_message(
                    message.content,
                    user_context
                )
                
                # Process the analysis results
                if analysis_result.get("should_update_preferences", False):
                    await _update_user_preferences_from_analysis(
                        message.group_id,
                        message.user_id,
                        analysis_result
                    )
                
                analyzed_count += 1
                
            except Exception as e:
                logger.error(f"Error analyzing message {message.id}: {str(e)}")
                continue
        
        logger.info(f"Successfully analyzed {analyzed_count} messages")
        return {"analyzed": analyzed_count, "total": len(messages)}
        
    except Exception as e:
        logger.error(f"Error in message analysis: {str(e)}")
        raise


async def _analyze_group_preferences_async(task, group_id: str):
    """Async implementation of group preferences analysis."""
    from app.database import startup_db_client
    from app.models.group import ChatMessage
    
    try:
        await startup_db_client()
        
        # Get recent messages for this group
        cutoff_time = datetime.utcnow() - timedelta(days=7)  # Last week
        
        messages = await ChatMessage.find(
            ChatMessage.group_id == group_id,
            ChatMessage.created_at >= cutoff_time,
            ChatMessage.message_type == "text"
        ).to_list()
        
        logger.info(f"Analyzing {len(messages)} messages for group {group_id}")
        
        # Batch analyze messages for patterns
        if messages:
            message_texts = [msg.content for msg in messages]
            user_contexts = [{
                "message_id": str(msg.id),
                "user_id": msg.user_id,
                "group_id": msg.group_id,
                "timestamp": msg.created_at.isoformat()
            } for msg in messages]
            
            # Use batch analysis for efficiency
            batch_results = await langgraph_analyzer.batch_analyze_messages([
                {"text": text, "context": context} 
                for text, context in zip(message_texts, user_contexts)
            ])
            
            # Process batch results
            preference_updates = 0
            for result in batch_results:
                if result.get("should_update_preferences", False):
                    await _update_user_preferences_from_analysis(
                        group_id,
                        result["user_id"],
                        result
                    )
                    preference_updates += 1
            
            return {
                "group_id": group_id,
                "messages_analyzed": len(messages),
                "preference_updates": preference_updates
            }
        
        return {"group_id": group_id, "messages_analyzed": 0, "preference_updates": 0}
        
    except Exception as e:
        logger.error(f"Error in group preferences analysis: {str(e)}")
        raise


async def _update_user_preferences_from_analysis(group_id: str, user_id: str, analysis_result: Dict[str, Any]):
    """Update user's group preferences based on analysis results using new generic keyword structure."""
    try:
        from app.services.group_preference_service import group_preference_service
        
        extracted_keywords = analysis_result.get("extracted_keywords", {})
        recommendation_keywords = analysis_result.get("recommendation_keywords", [])
        confidence = analysis_result.get("confidence_scores", {}).get("overall_relevance", 0.7)
        
        has_keywords = any(keywords for keywords in extracted_keywords.values() if isinstance(keywords, list) and keywords)
        
        from shared.config import llm_config
        if has_keywords and confidence > llm_config.MIN_CONFIDENCE_THRESHOLD:
            await group_preference_service.update_preferences_from_llm(
                group_id=group_id,
                user_firebase_id=user_id,
                extracted_keywords=extracted_keywords,
                recommendation_keywords=recommendation_keywords,
                confidence=confidence
            )
            logger.info(f"Updated keyword preferences for user {user_id} (confidence: {confidence:.2f})")
            
        elif analysis_result.get("preferences") and confidence > llm_config.MIN_CONFIDENCE_THRESHOLD:
            preferences = analysis_result.get("preferences", {})
            await group_preference_service._update_from_llm(
                await group_preference_service.create_default_group_preferences(group_id, user_id),
                preferences,
                confidence
            )
            logger.info(f"Updated legacy preferences for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        # Don't re-raise - this is a non-critical operation


async def _analyze_group_trends_async():
    """Analyze trends across all groups for insights and patterns."""
    from app.database import startup_db_client
    from app.models.group import Group
    from app.models.group_preferences import GroupPreferences
    
    try:
        await startup_db_client()
        
        # Get all active groups
        active_groups = await Group.find(Group.status == "active").to_list()
        
        logger.info(f"Analyzing trends for {len(active_groups)} active groups")
        
        trend_data = {
            "popular_cuisines": {},
            "common_dietary_restrictions": {},
            "price_preferences": {},
            "total_groups_analyzed": 0
        }
        
        for group in active_groups:
            try:
                # Get group preferences
                group_prefs = await GroupPreferences.find(
                    GroupPreferences.group_id == str(group.id)
                ).to_list()
                
                for prefs in group_prefs:
                    # Aggregate cuisine preferences
                    cuisines = prefs.preferences.get("preferred_cuisines", [])
                    for cuisine in cuisines:
                        trend_data["popular_cuisines"][cuisine] = trend_data["popular_cuisines"].get(cuisine, 0) + 1
                    
                    # Aggregate dietary restrictions
                    restrictions = prefs.preferences.get("dietary_restrictions", [])
                    for restriction in restrictions:
                        trend_data["common_dietary_restrictions"][restriction] = trend_data["common_dietary_restrictions"].get(restriction, 0) + 1
                    
                    # Aggregate price preferences
                    price_range = prefs.preferences.get("price_range", {})
                    if price_range:
                        price_key = f"{price_range.get('min', 1)}-{price_range.get('max', 4)}"
                        trend_data["price_preferences"][price_key] = trend_data["price_preferences"].get(price_key, 0) + 1
                
                trend_data["total_groups_analyzed"] += 1
                
            except Exception as e:
                logger.error(f"Error analyzing group {group.id}: {str(e)}")
                continue
        
        # Sort trends by popularity
        trend_data["popular_cuisines"] = dict(sorted(
            trend_data["popular_cuisines"].items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        trend_data["common_dietary_restrictions"] = dict(sorted(
            trend_data["common_dietary_restrictions"].items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        logger.info(f"Completed trend analysis for {trend_data['total_groups_analyzed']} groups")
        return trend_data
        
    except Exception as e:
        logger.error(f"Error in group trends analysis: {str(e)}")
        raise


async def _process_stale_preferences_async():
    """Process and refresh stale user preferences."""
    from app.database import startup_db_client
    from app.models.group_preferences import GroupPreferences
    
    try:
        await startup_db_client()
        
        # Find preferences that haven't been updated by LLM in over 30 days
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        
        stale_preferences = await GroupPreferences.find(
            GroupPreferences.last_llm_update < cutoff_time,
            GroupPreferences.is_llm_updated == True
        ).to_list()
        
        logger.info(f"Found {len(stale_preferences)} stale preference records")
        
        processed_count = 0
        for prefs in stale_preferences:
            try:
                # Mark preferences as needing refresh
                # This could trigger re-analysis of recent messages for this user/group
                
                # For now, we'll just reset the LLM confidence to encourage fresh analysis
                prefs.llm_confidence_score = max(0.3, (prefs.llm_confidence_score or 0.7) * 0.8)
                prefs.updated_at = datetime.utcnow()
                await prefs.save()
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing stale preferences {prefs.id}: {str(e)}")
                continue
        
        logger.info(f"Processed {processed_count} stale preference records")
        return {"processed": processed_count, "total": len(stale_preferences)}
        
    except Exception as e:
        logger.error(f"Error processing stale preferences: {str(e)}")
        raise