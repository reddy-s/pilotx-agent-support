import logging
import uvicorn

from typing import Annotated
from fastapi import FastAPI, Depends, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

from agent_support.entities import ListSessionsRequest
from agent_support.config import ServiceConfig
from agent_support import AgentSupportService
from agent_support.auth import get_current_user

from service import LogConfig, AgentSupportServiceMetadata

load_dotenv()
log_config = LogConfig().log_config
logging.config.dictConfig(log_config)

logger = logging.getLogger("uvicorn")
logger.info(f"[APP] Log level set to: {logger.getEffectiveLevel()}")


app = FastAPI(
    title=AgentSupportServiceMetadata.name,
    description=AgentSupportServiceMetadata.description,
    summary=AgentSupportServiceMetadata.summary,
    version=AgentSupportServiceMetadata.version,
    openapi_tags=AgentSupportServiceMetadata.tags,
    docs_url=AgentSupportServiceMetadata.enable_docs_url,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=AgentSupportServiceMetadata.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
agent_support_service = AgentSupportService()


@app.post("/agent-support/v1/sessions/list", tags=["Data"])
async def list_user_sessions(
    request: ListSessionsRequest, user: dict = Depends(get_current_user)
) -> dict:
    logger.debug(
        f"[API: agent-sessions] Received list agent sessions request for user: {user.get('user_id')}"
    )
    response = await agent_support_service.list_sessions(request, user.get("user_id"))
    logger.debug(f"[API: agent-sessions] Returning results for request: {response}")
    return response


@app.get("/agent-support/v1/sessions/{session_id}", tags=["Data"])
async def get_user_session(
    session_id: Annotated[str, Path(title="Session you like to retrieve")],
    user: dict = Depends(get_current_user),
) -> dict:
    logger.debug(
        f"[API: agent-sessions] Received get session {session_id} for user: {user.get('user_id')}"
    )
    response = await agent_support_service.get_session(session_id, user.get("user_id"))
    logger.debug(f"[API: agent-sessions] Returning results for request: {response}")
    return response


@app.get("/agent-support/v1/config", tags=["Configuration"])
async def config_request() -> dict:
    logger.debug("[API: Config] Received config request")
    response = ServiceConfig.get_or_create_instance().config[0][0]
    logger.debug(f"[API: Config] Returning results for request: {response}")
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
