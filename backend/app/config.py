import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / "backend" / ".env"
SOURCES_DIR = BASE_DIR / "data" / "sources"
CHROMA_DIR = BASE_DIR / "backend" / ".chroma"
COLLECTION = "esbc_kb"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
REQUIRED_META = ["service", "title", "url", "date_checked", "language"]

GEN_MODELS = [
    m.strip()
    for m in os.getenv("GEN_MODELS", "gemini-flash-latest,gemini-flash-lite-latest").split(",")
    if m.strip()
]
GEN_MODEL = GEN_MODELS[0]
TOP_K = 5
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.6"))
