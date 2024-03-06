import os
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureTextCompletion,
)
from semantic_kernel.connectors.ai.open_ai.contents import OpenAIChatMessageContent
from semantic_kernel.connectors.ai.open_ai.contents.function_call import FunctionCall
from semantic_kernel.connectors.ai.open_ai.contents.tool_calls import ToolCall

from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.core_plugins.time_plugin import TimePlugin
from semantic_kernel.core_plugins.web_search_engine_plugin import WebSearchEnginePlugin
from semantic_kernel.connectors.search_engine.bing_connector import BingConnector

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

        bing = BingConnector(api_key=os.environ["BING_SEARCH_API_KEY"])
        web_search_engine = WebSearchEnginePlugin(bing)
        self.kernel.import_plugin_from_object(web_search_engine, plugin_name="search")
        self.search_function = self.kernel.func("search", "search")
        self.kernel.import_plugin_from_object(TimePlugin(), plugin_name="time")
        # Define a service ID that ties to the AI service
        chat_service = AzureChatCompletion(
            service_id="gpt4",
            deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_API_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
        text_service = AzureTextCompletion(
            service_id="gpt-35-turbo-instruct",
            deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME_TEXT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_API_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
        # Add the AI service to the kernel
        self.kernel.add_service(chat_service)
        self.kernel.add_service(text_service)

        # Create the chat function from the prompt template config
        self.chat_function = self.kernel.create_function_from_prompt(
            prompt="{{$chat_history}}",
            plugin_name="chat_bot",
            function_name="chat",
            prompt_execution_settings=chat_service.instantiate_prompt_execution_settings(
                service_id="gpt4",
                max_tokens=2000,
                temperature=0.7,
                top_p=0.8,
            ),
        )

        self.intent_function = self.kernel.create_function_from_prompt(
            prompt="Return True if the intent of the following input is to ask a question that can only be answered with a online search, and False otherwise: {{$input}}, remember do not return anything else.",
            plugin_name="intent",
            function_name="get_intent",
            prompt_execution_settings=text_service.instantiate_prompt_execution_settings(
                service_id="gpt-35-turbo-instruct",
                max_tokens=2,
                temperature=0.0,
            ),
        )
        self.query_function = self.kernel.create_function_from_prompt(
            prompt="Create a search query that can be sent to Bing Search do not try to answer and only use the context to create the query not to answer, current date {{ time.today }}, context: {{$chat_history}}, question: {{$input}}, make sure that the query actually answers the question, don't get distracted by the context.",
            plugin_name="search",
            function_name="create_query",
            prompt_execution_settings=text_service.instantiate_prompt_execution_settings(
                service_id="gpt-35-turbo-instruct",
                max_tokens=100,
                temperature=0.0,
            ),
        )
        # Create the chat function from the prompt template config
        self.summary_function = self.kernel.create_function_from_prompt(
            prompt="Please summarize the following conversation in one or two sentences: {{$chat_history}}",
            plugin_name="summary",
            function_name="summarize",
            prompt_execution_settings=text_service.instantiate_prompt_execution_settings(
                service_id="gpt-35-turbo-instruct",
                max_tokens=300,
                temperature=0.0,
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
        summary = await self.kernel.invoke(
            self.summary_function, chat_history=self.history
        )
        await self.cosmos_chat_history.save_history(
            user_id, session_id, self.history, str(summary)
        )

    async def invoke(self, user_input):
        # add translation
        
        intent = await self.kernel.invoke(self.intent_function, input=user_input)
        str_intent = str(intent).strip()
        if str_intent == "True":
            query = await self.kernel.invoke(
                self.query_function, input=user_input, chat_history=self.history
            )
            query = str(query).strip().replace('"', "")
            self.history.add_user_message(user_input)
            tool_message = OpenAIChatMessageContent(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="0",
                        type="function",
                        function=FunctionCall(
                            name="search-search",
                            arguments="{ 'query': '" + query + "', 'num_results': 3 }",
                        ),
                    )
                ],
            )
            self.history.add_message(tool_message)
            search_results = await self.search_function.invoke(
                self.kernel,
                query=query,
                num_results=3,
            )
            if search_results and isinstance(search_results, list):
                search_results = search_results[0]
            val = search_results.value.replace("[", "").replace("]", "").strip()
            tool_result_message = OpenAIChatMessageContent(
                role="tool", content=val, metadata={"tool_call_id": "0"}
            )
            self.history.add_message(tool_result_message)
        else:
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
