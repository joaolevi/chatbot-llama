import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pytesseract import pytesseract
from pdf2image import convert_from_bytes
import requests
import json

from llama_index.core.indices import VectorStoreIndex
from llama_index.core import Document

from app.engine.index import get_index

ocr_llm_route = r = APIRouter()

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)
logger = logging.getLogger("uvicorn")

class OcrLLM(BaseModel):
    url: str
    prompt: str

import json

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
        logger(f"Erro ao decodificar o JSON: {e}")
        logger(f"Texto recebido: {response_text[:500]}")
        return {}

@r.post("")
def vectorization_mode_ocr(request: OcrLLM):
    try:
        images = convert_from_bytes(requests.get(request.url).content)

        documents = []
        for index, image in enumerate(images):
            texto = pytesseract.image_to_string(image, lang='por')
            doc = Document(text=texto)
            documents.append(doc)
        
        index = VectorStoreIndex.from_documents(documents, verbose=True)
        response = index.as_query_engine().query(request.prompt)
        result_json = json_formater(str(response))
        return result_json
    except Exception as e:
        logger.error(f"Erro no processamento do arquivo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing file")
