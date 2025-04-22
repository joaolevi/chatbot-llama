import os
from app.engine.index import get_index
from fastapi import HTTPException
from llama_index.core.memory import ChatMemoryBuffer

def get_chat_engine(chat_store=None, filters=None, user_uuid="default"):
    system_prompt = os.getenv("SYSTEM_PROMPT")
    top_k = os.getenv("TOP_K", 3)

    index = get_index()
    if index is None:
        raise HTTPException(
            status_code=500,
            detail=str(
                "StorageContext is empty - call 'poetry run generate' to generate the storage first"
            ),
        )
    
    chat_memory = ChatMemoryBuffer.from_defaults(
        token_limit=3000,
        chat_store=chat_store,
        chat_store_key=user_uuid,
    )

    return index.as_chat_engine(
        similarity_top_k=int(top_k),
        system_prompt=system_prompt,
        chat_mode="condense_plus_context",
        filters=filters,
        memory=chat_memory
    )
