import os
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_history import ChatHistory

import logging

from cosmos_chat_history import CosmosChatHistory

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """
You are a chat bot. Your name is Mosscap and
you have one goal: figure out what people need.
Your full name, should you need to know it, is
Splendid Speckled Mosscap. You communicate
effectively, but you tend to answer with long
flowery prose.
"""


class Orchestrator:
    def __init__(self):

        # Create a Kernel
        self.kernel = Kernel()

        # Define a service ID that ties to the AI service
        chat_service = AzureChatCompletion(
            service_id="gpt-4",
            deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_API_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
        # Add the AI service to the kernel
        self.kernel.add_service(chat_service)

        # Create the chat function from the prompt template config
        self.chat_function = self.kernel.create_function_from_prompt(
            prompt="{{$chat_history}}",
            plugin_name="chat_bot",
            function_name="chat",
            prompt_execution_settings=chat_service.instantiate_prompt_execution_settings(
                service_id="gpt-4",
                max_tokens=2000,
                temperature=0.7,
                top_p=0.8,
            ),
        )
        # Define a chat history object
        self.cosmos_chat_history = CosmosChatHistory()
        self.history = ChatHistory(system_message=SYSTEM_MESSAGE)

    async def load_history(self, user_id, session_id):
        history = await self.cosmos_chat_history.load_history(user_id, session_id)
        if history:
            self.history = history

    async def store_history(self, user_id, session_id):
        await self.cosmos_chat_history.save_history(user_id, session_id, self.history)

    async def invoke(self, user_input):
        self.history.add_user_message(user_input)
        response = await self.kernel.invoke(
            self.chat_function,
            chat_history=self.history,
        )
        logger.debug(f"{response=}")
        self.history.add_message(response.value[0])

    async def __aenter__(self):
        await self.cosmos_chat_history.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cosmos_chat_history.__aexit__(exc_type, exc_val, exc_tb)
