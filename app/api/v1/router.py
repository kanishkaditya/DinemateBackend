from fastapi import APIRouter
from . import (
    auth, groups, restaurants, group_preferences, user
)

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    groups.router,
    prefix="/group",
    tags=["groups"]
)

api_router.include_router(
    restaurants.router,
    prefix="/restaurants",
    tags=["restaurants"]
)

api_router.include_router(
    group_preferences.router,
    prefix="/group-preferences",
    tags=["group-preferences"]
)

api_router.include_router(
    user.router,
    prefix="/user",
    tags=["users"]
)

