import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ValidationError
from django.db import close_old_connections

from .services import (
    create_message,
    get_conversation_for_user,
)

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.info("WebSocket connection rejected: Anonymous or unauthenticated user.")
            await self.close(code=4001)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]

        try:
            self.conversation = await self._get_conversation(
                self.conversation_id,
                user,
            )
        except Exception as exc:
            logger.error("Failed to fetch conversation %s for user %s: %s", self.conversation_id, user.id, exc)
            await self.close(code=4003)
            return

        if self.conversation is None:
            logger.info("WebSocket connection rejected: Conversation %s not found for user %s.", self.conversation_id, user.id)
            await self.close(code=4003)
            return

        self.group_name = f"chat_conversation_{self.conversation.id}"

        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )
        except Exception as exc:
            logger.error("Failed to add channel to group %s: %s", self.group_name, exc)
            await self.close(code=4000)
            return

        await self.accept()
        logger.info("WebSocket connected successfully for conversation %s by user %s.", self.conversation_id, user.id)

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        logger.info("WebSocket disconnected with close code %s for group %s.", close_code, group_name)

        if group_name:
            try:
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name,
                )
            except Exception as exc:
                logger.error("Failed to discard group %s on disconnect: %s", group_name, exc)

        try:
            await database_sync_to_async(close_old_connections)()
        except Exception as exc:
            logger.error("Failed to close old database connections on disconnect: %s", exc)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            await self._send_error("Message payload is required.")
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON payload.")
            return

        if not isinstance(data, dict):
            await self._send_error("Message payload must be a JSON object.")
            return

        msg_type = data.get("type", "message")
        user = self.scope["user"]
        display_name = user.get_full_name() or user.username

        if msg_type == "typing":
            is_typing = bool(data.get("is_typing", True))
            try:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "chat.typing",
                        "sender_id": user.id,
                        "sender_username": display_name,
                        "is_typing": is_typing,
                    },
                )
            except Exception as exc:
                logger.error("Failed to broadcast typing state for group %s: %s", getattr(self, "group_name", None), exc)
            return

        content = data.get("content")

        if not isinstance(content, str):
            await self._send_error("Message content must be a string.")
            return

        try:
            message = await self._create_message(
                conversation=self.conversation,
                sender=user,
                content=content,
            )
        except ValidationError as exc:
            await self._send_error(
                self._validation_error_message(exc),
            )
            return
        except Exception as exc:
            logger.error("Failed to create message for conversation %s: %s", getattr(self, "conversation_id", None), exc)
            await self._send_error("Unable to save message. Please try again.")
            return

        payload = {
            "type": "chat.message",
            "message_id": message.id,
            "sender_id": message.sender_id,
            "sender_username": display_name,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }

        try:
            await self.channel_layer.group_send(
                self.group_name,
                payload,
            )
        except Exception as exc:
            logger.error("Failed to broadcast message via group_send to group %s: %s", getattr(self, "group_name", None), exc)

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                    "sender_username": event["sender_username"],
                    "content": event["content"],
                    "created_at": event["created_at"],
                }
            )
        )

    async def chat_typing(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "sender_id": event["sender_id"],
                    "sender_username": event["sender_username"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    async def _send_error(self, message):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "message": message,
                }
            )
        )

    @database_sync_to_async
    def _get_conversation(self, conversation_id, user):
        return get_conversation_for_user(
            conversation_id=conversation_id,
            user=user,
        )

    @database_sync_to_async
    def _create_message(
        self,
        *,
        conversation,
        sender,
        content,
    ):
        return create_message(
            conversation=conversation,
            sender=sender,
            content=content,
        )

    @staticmethod
    def _validation_error_message(exc):
        if exc.messages:
            return exc.messages[0]

        return "Unable to send message."
