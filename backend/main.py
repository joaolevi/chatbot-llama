from dotenv import load_dotenv

load_dotenv()

import logging
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.api.routers.chat import chat_router
from app.api.routers.upload import file_upload_router
from app.api.routers.s3_event import s3_new_document_event_router
from app.api.routers.feedback import chat_feedback
from app.api.routers.ocr import ocr_llm_route
from app.api.routers.general import general_prompt_route
from app.settings import init_settings
from app.observability import init_observability
from fastapi.staticfiles import StaticFiles


app = FastAPI()

init_settings()
init_observability()

environment = os.getenv("ENVIRONMENT", "dev")  # Default to 'development' if not set
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("uvicorn")

if environment == "dev":
    logger.warning("Running in development mode - allowing CORS for all origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Redirect to documentation page when accessing base URL
    @app.get("/")
    async def redirect_to_docs():
        return RedirectResponse(url="/docs")


def mount_static_files(directory, path):
    if os.path.exists(directory):
        for dir, _, _ in os.walk(directory):
            relative_path = os.path.relpath(dir, directory)
            mount_path = path if relative_path == "." else f"{path}/{relative_path}"
            logger.info(f"Mounting static files '{dir}' at {mount_path}")
            app.mount(mount_path, StaticFiles(directory=dir), name=f"{dir}-static")


# Mount the data files to serve the file viewer
mount_static_files("data", "/api/files/data")
# Mount the output files from tools
mount_static_files("output", "/api/files/output")

app.include_router(chat_router, prefix="/api/chat")
app.include_router(file_upload_router, prefix="/api/chat/upload")
app.include_router(s3_new_document_event_router, prefix="/api/s3_event")
app.include_router(chat_feedback, prefix="/api/feedback")
app.include_router(ocr_llm_route, prefix="/api/ocr")
app.include_router(general_prompt_route, prefix="/api/general")

if __name__ == "__main__":
    app_host = os.getenv("APP_HOST", "0.0.0.0")
    app_port = int(os.getenv("APP_PORT", "8000"))
    reload = True if environment == "dev" else False

    uvicorn.run(app="main:app", host=app_host, port=app_port, reload=reload)
