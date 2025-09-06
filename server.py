from fastapi import FastAPI, Depends
from .services import ask_llm
from db import get_db
from services.db_service import DBService
from services.llm_service import LLMService

app = FastAPI(title="Program Preview Generator")
db = DBService()

@app.post("/generate_preview")
async def ask_question(pregram_id: str):
    llm_service = LLMService()
    output = llm_service.generate_preview_for_engaging_modules(pregram_id)
    return output