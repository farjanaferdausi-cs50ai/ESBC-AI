import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent import ask
from app.search import ensure_index, knowledge_stats
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("esbc")


@asynccontextmanager
async def lifespan(_app):
    try:
        ensure_index()
    except (Exception, SystemExit):
        log.exception("knowledge base could not be prepared")
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


@app.get("/api/meta")
def meta():
    return knowledge_stats()


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        return ask(req.message.strip(), plain=req.plain_mode)
    except Exception:
        log.exception("chat failed")
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
