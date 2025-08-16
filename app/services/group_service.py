from typing import List, Optional
import random
import string
from models.group import Group, ChatMessage, GroupStatus, MessageType
from models.user import User
from schemas.group import (
    GroupCreate, GroupJoin, MessageCreate, 
    GroupResponse, GroupDetailResponse, MessageResponse, GroupMember
)
from services.group_preference_service import GroupPreferencesService


class GroupService:
    def __init__(self):
        pass
    
    
    async def create_group(self, group_data: GroupCreate) -> GroupResponse:
        user = await User.find_one(User.firebase_id == group_data.firebase_id)
        if not user:
            raise ValueError("User not found")
        
        # Retry loop to handle potential duplicate invite codes
        max_retries = 10
        for attempt in range(max_retries):
            invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            

            group = Group(
                name=group_data.name,
                description=group_data.description,
                created_by=user.firebase_id,
                invite_code=invite_code,
                member_ids=[user.firebase_id]
            )
            
            try:
                await group.save()
                break  # Success, exit retry loop
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    # Duplicate invite code, try again with new code
                    if attempt == max_retries - 1:
                        raise ValueError("Failed to generate unique invite code after multiple attempts")
                    continue
                else:
                    # Different error, re-raise
                    raise
        
        # Auto-create group preferences for the creator
        preference_service = GroupPreferencesService()
        await preference_service.create_default_group_preferences(str(group.id), user.firebase_id)
        
        await self._add_system_message(str(group.id), f"{user.username} created the group")
        
        return await self._group_to_response(group)
    
    async def join_group(self, join_data: GroupJoin) -> GroupResponse:
        user = await User.find_one(User.firebase_id == join_data.firebase_id)
        if not user:
            raise ValueError("User not found")
        
        group = await Group.find_one(Group.invite_code == join_data.invite_code)
        if not group:
            raise ValueError("Invalid invite code")
        
        if user.firebase_id in group.member_ids:
            raise ValueError("User already in group")
        
        if len(group.member_ids) >= group.max_members:
            raise ValueError("Group is full")
        
        group.member_ids.append(user.firebase_id)
        await group.save()
        
        # Auto-create group preferences for the new member
        preference_service = GroupPreferencesService()
        await preference_service.create_default_group_preferences(str(group.id), user.firebase_id)
        
        await self._add_system_message(str(group.id), f"{user.username} joined the group")
        
        return await self._group_to_response(group)
    
    async def get_user_groups(self, firebase_id: str) -> List[GroupResponse]:
        user = await User.find_one(User.firebase_id == firebase_id)
        if not user:
            raise ValueError("User not found")
        groups = await Group.find(Group.member_ids == user.firebase_id).to_list()
        return [await self._group_to_response(group) for group in groups]
    
    async def get_group_detail(self, group_id: str, firebase_id: str) -> GroupDetailResponse:
        user = await User.find_one(User.firebase_id == firebase_id)
        if not user:
            raise ValueError("User not found")
        
        group = await Group.get(group_id)
        if not group:
            raise ValueError("Group not found")
        
        if user.firebase_id not in group.member_ids:
            raise ValueError("User not a member of this group")
        
        members = await self._get_group_members(group)
        recent_messages = await self._get_recent_messages(group_id, limit=20)
        
        group_response = await self._group_to_response(group)
        
        return GroupDetailResponse(
            **group_response.model_dump(),
            members=members,
            recent_messages=recent_messages
        )
    
    async def send_message(self, group_id: str, message_data: MessageCreate) -> MessageResponse:
        user = await User.find_one(User.firebase_id == message_data.firebase_id)
        if not user:
            raise ValueError("User not found")
        
        group = await Group.get(group_id)
        if not group:
            raise ValueError("Group not found")
        
        if user.firebase_id not in group.member_ids:
            raise ValueError("User not a member of this group")
        
        message = ChatMessage(
            group_id=group_id,
            user_id=user.firebase_id,
            user_name=user.username,
            message_type=message_data.message_type,
            content=message_data.content,
            restaurant_data=message_data.restaurant_data
        )
        await message.save()
        
        group.message_count += 1
        group.last_message_at = message.created_at
        await group.save()
        
        return MessageResponse(
            id=str(message.id),
            group_id=message.group_id,
            user_id=message.user_id,
            user_name=message.user_name,
            message_type=message.message_type,
            content=message.content,
            restaurant_data=message.restaurant_data,
            created_at=message.created_at
        )
    
    async def get_messages(self, group_id: str, firebase_id: str, 
                          limit: int = 50, skip: int = 0) -> List[MessageResponse]:
        user = await User.find_one(User.firebase_id == firebase_id)
        if not user:
            raise ValueError("User not found")
        
        group = await Group.get(group_id)
        if not group:
            raise ValueError("Group not found")
        
        if user.firebase_id not in group.member_ids:
            raise ValueError("User not a member of this group")
        
        return await self._get_recent_messages(group_id, limit, skip)
    
    async def leave_group(self, group_id: str, firebase_id: str) -> bool:
        user = await User.find_one(User.firebase_id == firebase_id)
        if not user:
            raise ValueError("User not found")
        
        group = await Group.get(group_id)
        if not group:
            raise ValueError("Group not found")
        
        if user.firebase_id not in group.member_ids:
            raise ValueError("User not a member of this group")
        
        group.member_ids.remove(user.firebase_id)
        
        if len(group.member_ids) == 0:
            await group.delete()
        else:
            await group.save()
            await self._add_system_message(group_id, f"{user.username} left the group")
        
        return True
    
    async def _add_system_message(self, group_id: str, content: str):
        message = ChatMessage(
            group_id=group_id,
            user_id="system",
            user_name="System",
            message_type=MessageType.SYSTEM,
            content=content
        )
        await message.save()
    
    async def _get_group_members(self, group: Group) -> List[GroupMember]:
        members = await User.find(User.firebase_id.in_(group.member_ids)).to_list()
        return [
            GroupMember(
                id=str(member.id),
                username=member.username,
                full_name=member.full_name,
                is_active=member.is_active
            )
            for member in members
        ]
    
    async def _get_recent_messages(self, group_id: str, limit: int = 50, skip: int = 0) -> List[MessageResponse]:
        messages = await ChatMessage.find(
            ChatMessage.group_id == group_id
        ).sort(-ChatMessage.created_at).skip(skip).limit(limit).to_list()
        
        return [
            MessageResponse(
                id=str(msg.id),
                group_id=msg.group_id,
                user_id=msg.user_id,
                user_name=msg.user_name,
                message_type=msg.message_type,
                content=msg.content,
                restaurant_data=msg.restaurant_data,
                created_at=msg.created_at
            )
            for msg in reversed(messages)  # Reverse to show oldest first
        ]
    
    async def _group_to_response(self, group: Group) -> GroupResponse:
        return GroupResponse(
            id=str(group.id),
            name=group.name,
            description=group.description,
            created_by=group.created_by,
            invite_code=group.invite_code,
            status=group.status,
            member_count=len(group.member_ids),
            max_members=group.max_members,
            last_message_at=group.last_message_at,
            message_count=group.message_count,
            selected_restaurant=group.selected_restaurant,
            created_at=group.created_at
        )