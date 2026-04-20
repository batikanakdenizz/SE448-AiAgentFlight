import os
import uuid
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import process_message

app = FastAPI(title="AI Flight Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> list of messages
sessions: dict[str, list] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list = []


@app.get("/")
def root():
    return {"status": "AI Flight Agent is running", "time": datetime.utcnow().isoformat()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]

    try:
        response_text, tool_calls = await process_message(history, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    sessions[session_id] = history

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tool_calls=tool_calls
    )


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"message": "Session cleared"}
