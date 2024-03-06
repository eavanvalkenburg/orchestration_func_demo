import azure.functions as func
import logging

from orchestrator import Orchestrator

from orchestrator_plugin import Orchestrator as OrchestratorPlugin
from orchestrator_summary_plugin import Orchestrator as OrchestratorSummaryPlugin

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

logger = logging.getLogger(__name__)


async def run_orchestrator(orchestrator, req: func.HttpRequest) -> func.HttpResponse:
    req_body = req.get_json()
    logger.info(req_body)
    user_input = req_body.get("user_input")
    user_id = req_body.get("user_id", "default_user")
    session_id = req_body.get("session_id", "default_session")
    if not user_input:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully. But the user_input cannot be empty.",
            status_code=200,
        )
    try:
        await orchestrator.load_history(user_id, session_id)
        await orchestrator.invoke(user_input)
        return func.HttpResponse(str(orchestrator.history.messages[-1]))
    except Exception as exc:
        logger.error(exc)
        return func.HttpResponse(
            "An error occured while processing the request. Please try again later.",
            status_code=400,
        )
    finally:
        await orchestrator.store_history(user_id, session_id)


@app.route(route="invoke")
async def invoke(req: func.HttpRequest) -> func.HttpResponse:
    async with Orchestrator() as orchestrator:
        return await run_orchestrator(orchestrator, req)


@app.route(route="invoke/with_plugin")
async def invoke_plugin(req: func.HttpRequest) -> func.HttpResponse:
    async with OrchestratorPlugin() as orchestrator:
        return await run_orchestrator(orchestrator, req)


@app.route(route="invoke/with_plugin_and_summary")
async def invoke_summary_plugin(req: func.HttpRequest) -> func.HttpResponse:
    async with OrchestratorSummaryPlugin() as orchestrator:
        return await run_orchestrator(orchestrator, req)
