from typing import Optional, List,Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# Base user schema
class UserBase(BaseModel):
    email: EmailStr
    firebase_id:str
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    preferences: Dict


# User creation schema
class UserCreate(UserBase):
    pass


# User update schema
class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    preferences: Dict


# User response schema
class UserResponse(UserBase):
   pass


# Login schemas
class UserLogin(BaseModel):
    firebase_id:str
    email:EmailStr


class UserLoginResponse(UserBase):
    pass

class UpdatePreferencesRequest(BaseModel):
    # 5 simple onboarding questions
    firebase_id: str
    preferences: dict = {
            "dietary_restrictions": [],  # ["vegetarian", "gluten_free", etc.]
            "preferred_cuisines": [],    # ["italian", "mexican", "chinese"]
            "budget_preference": "moderate",  # "budget", "moderate", "upscale" 
            "dining_style": [],          # ["casual", "fine_dining", "quick_service"]
            "spice_tolerance": "medium"  # "mild", "medium", "spicy"
    }
