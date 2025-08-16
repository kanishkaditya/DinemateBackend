# app/services/auth_service.py
from typing import Optional, Dict, Any
from models.user import User
from schemas.user import UserCreate, UserLogin, UserLoginResponse

class AuthService:
    def __init__(self):
        pass
    
    async def register_user(self, request: UserCreate) -> User:
        """
        Register user after Firebase authentication success
        
        Args:
            request: Firebase user data
            
        Returns:
            Created user
            
        Raises:
            ValueError: If user already exists
        """
        # Check if user already exists by firebase_uid
        existing_user = await User.find_one(User.firebase_id == request.firebase_id)
        if existing_user:
            raise ValueError("User already registered")
        
        # Check email uniqueness
        existing_email = await User.find_one(User.email == request.email)
        if existing_email:
            raise ValueError("Email already in use")
        
        # Check username uniqueness  
        existing_username = await User.find_one(User.username == request.username)
        if existing_username:
            raise ValueError("Username already taken")
        
        # Create user
        user = User(
            firebase_id=request.firebase_id,
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            preferences={}  # Empty initially, filled during onboarding
        )
        
        await user.save()
        return user
    
    async def login_user(self, request: UserLogin) -> UserLoginResponse:
        """
        Login user after Firebase authentication success
        
        Args:
            request: Firebase UID
            
        Returns:
            User data with preferences and groups
            
        Raises:
            ValueError: If user not found
        """
        # Find user by firebase_uid
        user = await User.find_one(User.firebase_id == request.firebase_id)
        if not user:
            raise ValueError("User not found. Please register first.")
        
        if not user.is_active:
            raise ValueError("Account is deactivated")
        
        
        return UserLoginResponse.model_validate(user.model_dump())
    
    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID"""
        return await User.find_one(User.firebase_uid == firebase_uid)