# app/services/auth_service.py
from typing import Optional, Dict, Any
from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, UserLoginResponse

class UserService:
    def __init__(self):
        pass

    async def update_user_preferences(self, firebase_id: str, preferences: Dict[str, Any]) -> User:
        """
        Update user's default preferences (from onboarding)
        
        Args:
            firebase_uid: Firebase user ID
            preferences: Preference dictionary
            
        Returns:
            Updated user
        """
        user = await User.find_one(User.firebase_id == firebase_id)
        if not user:
            raise ValueError("User not found")
        
        user.preferences = preferences
        await user.save()
        return UserLoginResponse.model_validate(user.model_dump())


# Global service instance  
user_service = UserService()