"""Embeddings through the Gemini API (no local ML model needed)."""
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.config import EMBED_DIM, EMBED_MODEL, ENV_PATH

load_dotenv(ENV_PATH)
_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is missing in backend/.env")
        _client = genai.Client(api_key=key)
    return _client


def embed(texts, task_type, batch_size=20):
    """task_type: RETRIEVAL_DOCUMENT for stored chunks, RETRIEVAL_QUERY for questions."""
    vectors = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        for attempt in range(5):
            try:
                res = _get_client().models.embed_content(
                    model=EMBED_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=EMBED_DIM,
                    ),
                )
                vectors.extend([e.values for e in res.embeddings])
                break
            except Exception as exc:
                if attempt == 4:
                    raise
                wait = 5 * (attempt + 1)
                print(f"Embedding retry in {wait}s ({exc})")
                time.sleep(wait)
        time.sleep(1)
    return vectors