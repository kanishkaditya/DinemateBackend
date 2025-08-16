from fastapi import APIRouter, status, Query
from typing import List
from schemas.group import (
    GroupCreate, GroupJoin, MessageCreate, GroupResponse, 
    GroupDetailResponse, MessageResponse, GroupListResponse
)
from services.group_service import GroupService
from core.exceptions import HTTPExceptions

router = APIRouter()


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(group_data: GroupCreate):
    """Create a new group"""
    group_service = GroupService()
    
    try:
        group = await group_service.create_group(group_data)
        return group
    except ValueError as e:
        raise HTTPExceptions.bad_request(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Failed to create group")


@router.post("/join", response_model=GroupResponse)
async def join_group(join_data: GroupJoin):
    """Join group with invite code"""
    group_service = GroupService()
    
    try:
        group = await group_service.join_group(join_data)
        return group
    except ValueError as e:
        raise HTTPExceptions.bad_request(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Failed to join group")



@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group_detail(group_id: str, firebase_id: str = Query(...)):
    """Get group details with members and recent messages"""
    group_service = GroupService()
    
    try:
        group = await group_service.get_group_detail(group_id, firebase_id)
        return group
    except ValueError as e:
        raise HTTPExceptions.bad_request(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Failed to fetch group")


@router.post("/{group_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(group_id: str, message_data: MessageCreate):
    """Send a message to the group"""
    group_service = GroupService()
    
    try:
        message = await group_service.send_message(group_id, message_data)
        return message
    except ValueError as e:
        raise HTTPExceptions.bad_request(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Failed to send message")


@router.get("/{group_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    group_id: str, 
    firebase_id: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """Get group messages with pagination"""
    group_service = GroupService()
    
    try:
        messages = await group_service.get_messages(group_id, firebase_id, limit, skip)
        return messages
    except ValueError as e:
        raise HTTPExceptions.bad_request(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Failed to fetch messages")


@router.delete("/{group_id}/leave")
async def leave_group(group_id: str, firebase_id: str = Query(...)):
    """Leave a group"""
    group_service = GroupService()
    
    try:
        await group_service.leave_group(group_id, firebase_id)
        return {"message": "Successfully left the group"}
    except ValueError as e:
        raise HTTPExceptions.bad_request(str(e))
    except Exception as e:
        raise HTTPExceptions.internal_server_error("Failed to leave group")