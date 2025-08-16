from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    RESTAURANT_SUGGESTION = "restaurant_suggestion"
    SYSTEM = "system"


class GroupStatus(str, Enum):
    ACTIVE = "active"
    PLANNING = "planning"
    DECIDED = "decided"
    ARCHIVED = "archived"


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    firebase_id: str


class GroupJoin(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=6)
    firebase_id: str


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    message_type: MessageType = MessageType.TEXT
    restaurant_data: Optional[dict] = None
    firebase_id: str


class MessageResponse(BaseModel):
    id: str
    group_id: str
    user_id: str
    user_name: str
    message_type: MessageType
    content: str
    restaurant_data: Optional[dict]
    created_at: datetime


class GroupMember(BaseModel):
    id: str
    username: str
    full_name: str
    is_active: bool


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_by: str
    invite_code: str
    status: GroupStatus
    member_count: int
    max_members: int
    last_message_at: Optional[datetime]
    message_count: int
    selected_restaurant: Optional[dict]
    created_at: datetime


class GroupDetailResponse(GroupResponse):
    members: List[GroupMember]
    recent_messages: List[MessageResponse]


class GroupListResponse(BaseModel):
    groups: List[GroupResponse]