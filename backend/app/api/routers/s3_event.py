import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.engine.generate import generate_single_doc

s3_new_document_event_router = r = APIRouter()
logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)
logger = logging.getLogger("uvicorn")

class URLRequest(BaseModel):
    url: str

@r.post("") 
def s3_new_document_event(request: URLRequest):
    try:
        url = request.url
        generate_single_doc(url)
        return {"message": "Extração de metadados concluída"}, 200
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))