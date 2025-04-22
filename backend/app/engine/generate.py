from dotenv import load_dotenv

load_dotenv()

import logging
import os

from app.engine.loaders import get_documents
from app.engine.loaders.s3 import S3Loader
from app.engine.vectordb import get_vector_store
from app.settings import init_settings
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.settings import Settings
from llama_index.core.storage import StorageContext
from llama_index.core.storage.docstore import SimpleDocumentStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

s3_loader = S3Loader()

STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")

def get_doc_store():

    if not os.path.exists(STORAGE_DIR):
        logger.info(f"Storage directory {STORAGE_DIR} does not exist, creating a new one.")
        os.makedirs(STORAGE_DIR, exist_ok=True)

    if os.path.exists(os.path.join(STORAGE_DIR, "docstore.json")):
        logger.info("Loading document store from existing storage directory.")
        return SimpleDocumentStore.from_persist_dir(STORAGE_DIR)
    else:
        logger.info("Creating a new in-memory document store.")
        return SimpleDocumentStore()


def run_pipeline(docstore, vector_store, documents):
    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(
                chunk_size=Settings.chunk_size,
                chunk_overlap=Settings.chunk_overlap,
            ),
            Settings.embed_model,
        ],
        docstore=docstore,
        docstore_strategy="upserts_and_delete",
        vector_store=vector_store, # Adiciona automaticamente os vetores no vector_store
    )

    # Run the ingestion pipeline and store the results
    nodes = pipeline.run(show_progress=True, documents=documents)

    return nodes


def persist_storage(docstore, vector_store):
    storage_context = StorageContext.from_defaults(
        docstore=docstore,
        vector_store=vector_store,
    )
    storage_context.persist(STORAGE_DIR)


def generate_datasource():
    init_settings()
    logger.info("Gerando index para os dados fornecidos")

    documents = get_documents()
    docstore = get_doc_store()
    vector_store = get_vector_store()

    _ = run_pipeline(docstore, vector_store, documents)
    persist_storage(docstore, vector_store)

    logger.info("Geração de index concluída")

def generate_single_doc(doc_s3_url: str):
    init_settings()
    logger.info(f"Gerando index para o documento {doc_s3_url}")

    docstore = get_doc_store()
    vector_store = get_vector_store()

    metadata = {
        "id_empresa": os.getenv("ID_EMPRESA"),
        "id_unidade": os.getenv("ID_UNIDADE"),
    }
    if not metadata:
        raise ValueError(f"Documento não encontrado no banco de dados: {doc_s3_url}")
    
    logging.info(f"Metadados coletados")
    
    documents = s3_loader.get_s3_single_document(doc_s3_url)
    first_document = documents[0]
    first_document.metadata = {
        "id_empresa": metadata["id_empresa"],
        "id_unidade": metadata["id_unidade"],
    }
    _ = run_pipeline(docstore, vector_store, [first_document])
    persist_storage(docstore, vector_store)

    logger.info("Geração de index do documento concluída")

if __name__ == "__main__":
    generate_datasource()
