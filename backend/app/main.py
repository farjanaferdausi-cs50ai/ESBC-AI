"""FastAPI backend for ESBC-AI."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent import ask

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("esbc")

app = FastAPI(title="ESBC-AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=1000)
    plain_mode: bool = False


class Source(BaseModel):
    id: int
    title: str
    url: str
    date_checked: str
    service: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    language: str
    confident: bool
    top_score: float | None = None
    sources: list[Source] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        return ask(req.message.strip(), plain=req.plain_mode)
    except Exception:
        log.exception("chat failed")
        raise HTTPException(status_code=503, detail="The assistant is temporarily unavailable. Please try again.")
