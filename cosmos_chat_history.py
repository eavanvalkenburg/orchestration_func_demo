import os
import logging
from azure.cosmos.aio import CosmosClient

from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.contents import OpenAIChatMessageContent

logger = logging.getLogger(__name__)


class CosmosChatHistory:
    def __init__(self):
        self.cosmos_client = CosmosClient.from_connection_string(
            os.environ["COSMOS_DB_CONN_STRING"]
        )

    async def load_history(self, user_id: str, session_id: str) -> ChatHistory:
        try:
            database = self.cosmos_client.get_database_client(
                os.environ["COSMOS_DB_DATABASE"]
            )
            container = database.get_container_client(os.environ["COSMOS_DB_CONTAINER"])
            logger.info(
                "loading history for user %s and session %s", user_id, session_id
            )
            hist = await container.read_item(item=session_id, partition_key=user_id)
            messages = [
                OpenAIChatMessageContent.model_validate(msg)
                for msg in hist.get("messages")
            ]
            return ChatHistory(messages=messages)
        except Exception:
            logger.info(
                "Failed to load history for user %s and session %s", user_id, session_id
            )
            return None

    async def save_history(
        self, user_id: str, session_id: str, history: ChatHistory, summary: str = None
    ) -> None:
        try:
            database = self.cosmos_client.get_database_client(
                os.environ["COSMOS_DB_DATABASE"]
            )
            container = database.get_container_client(os.environ["COSMOS_DB_CONTAINER"])
            logger.info(
                "saving history for user %s and session %s", user_id, session_id
            )
            messages = [
                msg.model_dump(
                    mode="json",
                    exclude_none=True,
                    exclude=["encoding", "ai_model_id", "function_call"],
                )
                for msg in history.messages
            ]
            item = {
                "id": session_id,
                "session_id": session_id,
                "user_id": user_id,
                "messages": messages,
            }
            if summary:
                item["summary"] = summary
            logger.debug(f"{item=}")
            await container.upsert_item(body=item)
        except Exception as exc:
            logger.error(
                "Failed to save history for user %s and session %s", user_id, session_id
            )
            logger.error(exc)

    async def __aenter__(self):
        await self.cosmos_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cosmos_client.__aexit__(exc_type, exc, tb)
