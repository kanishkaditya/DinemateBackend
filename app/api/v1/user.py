from fastapi import APIRouter
from typing import List
from ...schemas.user import (
    UpdatePreferencesRequest
    
)
from ...schemas.user import UserLoginResponse
from ...schemas.group import GroupResponse, GroupListResponse
from ...services.user_service import UserService
from ...services.group_service import GroupService
from ...core.exceptions import HTTPExceptions

# Create router
router = APIRouter()



@router.post("/update_preferences", response_model=UserLoginResponse)
async def update_preferences(
    preferences: UpdatePreferencesRequest
):
    """
    Complete user onboarding with 5 simple preference questions
    
    Called after registration during onboarding flow
    """
    user_service = UserService()
    
    try:
        # Convert to dict
        preferences_dict = {
            "dietary_restrictions": preferences.dietary_restrictions,
            "preferred_cuisines": preferences.preferred_cuisines,
            "budget_preference": preferences.budget_preference,
            "dining_style": preferences.dining_style,
            "spice_tolerance": preferences.spice_tolerance,
        }

        print(preferences_dict)
        
        user = await user_service.update_user_preferences(preferences.firebase_id, preferences_dict)
        return user
    except ValueError as e:
        raise HTTPExceptions.not_found(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Onboarding failed")


@router.get("/groups", response_model=GroupListResponse)
async def get_user_groups(firebase_id: str):
    """Get user's groups"""
    group_service = GroupService()
    
    try:
        print(firebase_id)
        groups = await group_service.get_user_groups(firebase_id)
        return GroupListResponse(groups=groups)
    except ValueError as e:
        raise HTTPExceptions.not_found(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Failed to fetch groups")