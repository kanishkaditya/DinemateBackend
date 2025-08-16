from fastapi import APIRouter, status
from schemas.user import (
    UserCreate, 
    UserLogin, 
    UserLoginResponse,
    UpdatePreferencesRequest
    
)
from schemas.user import UserResponse
from services.auth_service import AuthService
from core.exceptions import HTTPExceptions

# Create router
router = APIRouter()


@router.post("/register", response_model=UserLoginResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate):

    auth_service = AuthService()
    
    try:
        user = await auth_service.register_user(request)
        print(user)
        return UserLoginResponse.model_validate(user.model_dump())
    except ValueError as e:
        raise HTTPExceptions.bad_request(str(e))
    except Exception as e:
        print(e)
        raise HTTPExceptions.internal_server_error("Registration failed")


@router.post("/login", response_model=UserLoginResponse)
async def login(request: UserLogin):

    auth_service = AuthService()
    
    try:
        login_response = await auth_service.login_user(request)
        return login_response
    except ValueError as e:
        raise HTTPExceptions.unauthorized(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Login failed")

@router.get("/user/{firebase_uid}", response_model=UserLoginResponse)
async def get_user_by_firebase_id(firebase_uid: str):

    auth_service = AuthService()
    
    user = await auth_service.get_user_by_firebase_uid(firebase_uid)
    if not user:
        raise HTTPExceptions.not_found("User not found")
    
    return UserLoginResponse.model_validate(user.model_dump())