from fastapi import APIRouter, status
from typing import Dict, Any
from ...services.group_preference_service import GroupPreferencesService
from ...core.exceptions import HTTPExceptions

router = APIRouter()



@router.get("/groups/{group_id}/aggregated-preferences")
async def get_group_aggregated_preferences(group_id: str):

    service = GroupPreferencesService()
    
    try:
        aggregated = await service.get_group_aggregated_preferences(group_id)
        return aggregated
    except Exception as e:
        raise HTTPExceptions.internal_server_error(str(e))