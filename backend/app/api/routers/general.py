import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import re

from llama_index.core import Document, VectorStoreIndex

general_prompt_route = r = APIRouter()
logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)
logger = logging.getLogger("uvicorn")

def json_formater(response_text: str) -> dict:
    start_marker = '```json'
    end_marker = '```'
    try:
        if start_marker in response_text and end_marker in response_text:
            start_index = response_text.find(start_marker) + len(start_marker)
            end_index = response_text.find(end_marker, start_index)
            json_text = response_text[start_index:end_index].strip()
        else:
            json_start = response_text.find('{')
            json_text = response_text[json_start:].strip()
        result_json = json.loads(json_text)
        return result_json
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar o JSON: {e}")
        return {}

class PromptRequest(BaseModel):
    prompt: str

@r.post("")
def general_prompt_requests(request: PromptRequest):
    logger.info("Requisição de prompt recebida: " + request.prompt)
    try:
        documents = [Document(text=" ")]
        index = VectorStoreIndex.from_documents(documents)
        result = index.as_query_engine().query(request.prompt)
        
        response_string = str(result)
        result = json_formater(response_string)
        
        logger.info(f"Resultado do prompt: {result}")
        return {"message": result.get("message", "")}  # Retorna apenas o campo "message" no JSON
    
    except Exception as e:
        logger.error(f"Erro no processamento do prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))
