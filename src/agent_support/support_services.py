import logging

from http import HTTPStatus

from . import ServiceConfig
from .entities import ListSessionsRequest
from .storage import FirestoreSessionService


class AgentSupportService:
    def __init__(self):
        self.app_name = ServiceConfig.get_or_create_instance().appName
        self.conversations = FirestoreSessionService()

    async def list_sessions(self, request: ListSessionsRequest, user_id: str) -> dict:
        sessions, cursor = await self.conversations.list_sessions(
            app_name=self.app_name,
            user_id=user_id,
            page_size=request.pageSize,
            cursor=request.cursor,
        )
        return {"sessions": sessions.model_dump().get("sessions"), "cursor": cursor}

    async def get_session(self, session_id: str, user_id: str) -> dict:
        session = await self.conversations.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        return session.model_dump()
