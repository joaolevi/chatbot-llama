import logging
import os
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from llama_index.core.chat_engine.types import BaseChatEngine, NodeWithScore
from llama_index.core.llms import MessageRole
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters
from llama_index.storage.chat_store.redis import RedisChatStore

from app.api.routers.events import EventCallbackHandler
from app.api.routers.models import (
    ChatConfig,
    ChatData,
    Message,
    Result,
    SourceNodes,
)
from app.api.routers.vercel_response import VercelStreamResponse
from app.api.services.llama_cloud import LLamaCloudFileService
from app.engine import get_chat_engine

chat_router = r = APIRouter()

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)
logger = logging.getLogger("uvicorn")

chat_store = RedisChatStore(redis_url=os.getenv("REDIS_URL"), ttl=300)

def process_response_nodes(
    nodes: List[NodeWithScore],
    background_tasks: BackgroundTasks,
):
    """
    Start background tasks on the source nodes if needed.
    """
    files_to_download = SourceNodes.get_download_files(nodes)
    for file in files_to_download:
        background_tasks.add_task(
            LLamaCloudFileService.download_llamacloud_pipeline_file, file
        )


# streaming endpoint - delete if not needed
@r.post("")
async def chat(
    request: Request,
    data: ChatData,
    background_tasks: BackgroundTasks,
    chat_engine: BaseChatEngine = Depends(get_chat_engine),
):
    try:
        if chat_store is None:
            raise HTTPException(
                status_code=500,
                detail="Chat store not initialized",
            )
        user_uuid = data.user_uuid
        last_message_content = data.get_last_message_content()
        messages = data.get_history_messages()

        # doc_ids = data.get_chat_document_ids()
        # filters = generate_filters(doc_ids)
        # logger.info("Creating chat engine with filters", filters.dict())
        chat_engine = get_chat_engine(chat_store=chat_store, user_uuid=user_uuid)
        
        event_handler = EventCallbackHandler()
        chat_engine.callback_manager.handlers.append(event_handler)  # type: ignore

        response = await chat_engine.astream_chat(last_message_content, messages)
        process_response_nodes(response.source_nodes, background_tasks)

        return VercelStreamResponse(request, event_handler, response, data)
    except Exception as e:
        logger.exception("Error in chat engine", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in chat engine: {e}",
        ) from e


def generate_filters(doc_ids):
    if len(doc_ids) > 0:
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="private",
                    value=["true"],
                    operator="nin",  # type: ignore
                ),
                MetadataFilter(
                    key="doc_id",
                    value=doc_ids,
                    operator="in",  # type: ignore
                ),
            ],
            condition="or",  # type: ignore
        )
    else:
        filters = MetadataFilters(
            # Use the "NIN" - "not in" operator to include all public documents (don't have the private key set)
            filters=[
                MetadataFilter(
                    key="private",
                    value=["true"],
                    operator="nin",  # type: ignore
                ),
            ]
        )

    return filters


# non-streaming endpoint - delete if not needed
@r.post("/request")
async def chat_request(
    data: ChatData,
    chat_engine: BaseChatEngine = Depends(get_chat_engine),
) -> Result:
    last_message_content = data.get_last_message_content()
    messages = data.get_history_messages()
    user_uuid = data.user_uuid

    chat_engine = get_chat_engine(chat_store=chat_store, user_uuid=user_uuid)

    response = await chat_engine.achat(last_message_content, messages)
    return Result(
        result=Message(role=MessageRole.ASSISTANT, content=response.response),
        nodes=SourceNodes.from_source_nodes(response.source_nodes),
    )


@r.get("/config")
async def chat_config() -> ChatConfig:
    starter_questions = None
    conversation_starters = os.getenv("CONVERSATION_STARTERS")
    if conversation_starters and conversation_starters.strip():
        starter_questions = conversation_starters.strip().split("\n")
    return ChatConfig(starter_questions=starter_questions)
