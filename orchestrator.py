SYSTEM_MESSAGE = """
You are a chat bot. Your name is Mosscap and
you have one goal: figure out what people need.
Your full name, should you need to know it, is
Splendid Speckled Mosscap. You communicate
effectively, but you tend to answer with long
flowery prose.
"""

class Orchetrator:
    def __init__():

        # Create a Kernel
        self.kernel = Kernel()

        # Define a service ID that ties to the AI service
        service_id = "chat-gpt"
        chat_service = AzureChatCompletion(
            service_id=service_id, **azure_openai_settings_from_dot_env_as_dict(include_api_version=True)
        )

        # Add the AI service to the kernel
        self.kernel.add_service(chat_service)

        # Get the Prompt Execution Settings
        req_settings = self.kernel.get_service(service_id).instantiate_prompt_execution_settings(
            service_id=service_id, 
            max_tokens=2000,
            temperature=0.7,
            top_p=0.8,
        )

        # Create the prompt template config and specify any required input variables
        prompt_template_config = PromptTemplateConfig(
            template={{$chat_history}},
            name="chat",
            input_variables=[
                                InputVariable(name="chat_history", description="The history of the conversation", is_required=True),
            ],
            execution_settings=req_settings, # The execution settings will be tied to the configured service_id
        )

        # Create the chat function from the prompt template config
        self.chat_function = self.kernel.create_function_from_prompt(
            plugin_name="chat_bot",
            function_name="chat",
            prompt_template_config=prompt_template_config
        )
        # Define a chat history object
        self.history = ChatHistory(system_message=system_message)

    async def load_history():

        # Add the desired messages
        self.history.add_user_message("Hi there, who are you?")
        self.history.add_assistant_message("I am Mosscap, a chat bot. I'm trying to figure out what people need.")

    async def store_history():
    

    async def invoke(user_input):
        self.history.add_user_message(user_input)
        # Invoke the chat function, passing the kernel arguments as kwargs
        response = await kernel.invoke(
            chat_function,
            chat_history=self.history,
        )

        # View the response
        print(f"Mosscap:> {response}")
        
        self.history.add_assistant_message(str(response))

