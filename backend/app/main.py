"""FastAPI backend for ESBC-AI."""
import logging
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent import ask
from app.search import ensure_index, index_ready, knowledge_stats

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("esbc")


def _warm_up():
    """Build the knowledge base in the background so the port opens immediately."""
    try:
        ensure_index()
        log.info("knowledge base ready")
    except (Exception, SystemExit):
        log.exception("knowledge base could not be prepared")


@asynccontextmanager
async def lifespan(_app):
    threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(title="ESBC-AI API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=1000)
    plain_mode: bool = False
    language: Literal["auto", "bn", "en"] = "auto"


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
    trace: dict | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return knowledge_stats()


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not index_ready():
        raise HTTPException(
            status_code=503,
            detail="The knowledge base is warming up. Please try again in a moment.",
        )
    try:
        return ask(req.message.strip(), plain=req.plain_mode, language=req.language)
    except Exception as exc:
        log.exception("chat failed")
        text = str(exc)
        if any(k in text for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
            raise HTTPException(
                status_code=503,
                detail="The free AI service is busy right now. Please wait about a minute and try again.",
            )
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
        )
