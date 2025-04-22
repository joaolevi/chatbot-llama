import logging

from llama_index.core.memory import ChatMemoryBuffer

logger = logging.getLogger("uvicorn")

def get_chat_cache_string(chat_store=None, user_uuid="default") -> str:
    chat_memory = ChatMemoryBuffer.from_defaults(
        chat_store=chat_store,
        chat_store_key=user_uuid,
    )
    history = chat_memory.get()
    logger.info(f"Chat cache: {history}")

    cache_str = [str(msg) for msg in history]
    return "\n".join(cache_str)

def get_chat_cache_dict(chat_store=None, user_uuid="default") -> dict:
    chat_memory = ChatMemoryBuffer.from_defaults(
        chat_store=chat_store,
        chat_store_key=user_uuid,
    )
    return chat_memory.to_dict()
