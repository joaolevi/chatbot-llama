import logging
import os
import psycopg2
from psycopg2 import sql

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from llama_index.storage.chat_store.redis import RedisChatStore

from app.engine.chat_cache import *

chat_feedback = r = APIRouter()
logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)
logger = logging.getLogger("uvicorn")

chat_store = RedisChatStore(redis_url=os.getenv("REDIS_URL"), ttl=1800)

conn_params = {
    'dbname': os.getenv("POSTGRES_DB_FEEDBACK"),
    'user': os.getenv("POSTGRES_USER"),
    'password': os.getenv("POSTGRES_PASSWORD"),
    'host': os.getenv("POSTGRES_HOST"),
    'port': os.getenv("POSTGRES_PORT")     
}

def inserir_dados(user_uuid: str, feedback: str, str_cache: str):
    conn = None
    try:
        func_name = "inserir_dados: "
        conn = psycopg2.connect(**conn_params)
        logger.info(func_name+"Conexão com o POSGRESQL realizada com sucesso!")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'tb_feedback_chatbot'
            );
        """)
        
        tabela_existe = cursor.fetchone()[0]
        if tabela_existe:
            logger.info(func_name+"Tabela TB_FEEDBACK_CHATBOT já existe! Inserindo dados...")
        else:
            cursor.execute("""
                CREATE TABLE TB_FEEDBACK_CHATBOT (
                    user_uuid VARCHAR PRIMARY KEY,
                    feedback TEXT,
                    conversa TEXT
                );
            """)
            logger.info(func_name+"Tabela criada com sucesso!")

        query = sql.SQL("INSERT INTO TB_FEEDBACK_CHATBOT (user_uuid, feedback, conversa) VALUES (%s, %s, %s)")
        cursor.execute(query, (user_uuid, feedback, str_cache))
        
        conn.commit()
        logger.info(func_name+"Dados inseridos com sucesso!")
        
    except Exception as e:
        logger.error(func_name+f"Erro ao inserir dados: {e}")
    
    finally:
        if conn:
            cursor.close()
            conn.close()

class URLRequest(BaseModel):
    user_uuid: str
    feedback: str

@r.post("") 
def user_chat_feedback(request: URLRequest):
    try:
        user_uuid = request.user_uuid
        feedback = request.feedback
        str_cache = get_chat_cache_string(chat_store=chat_store, user_uuid=user_uuid)
        inserir_dados(user_uuid, feedback, str_cache)
        return {"Feedback salvo com sucesso"}, 200
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao armazenar o feedback; Erro: "+str(e))