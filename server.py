from fastapi import FastAPI, Depends
from .services import ask_llm
from db import get_db
from services.db_service import DBService

app = FastAPI(title="LangChain + FastAPI + MongoDB")
db = DBService()

@app.post("/ask")
async def ask_question():
    db.find_one("")
    return {"a": "Hello WOrld"}