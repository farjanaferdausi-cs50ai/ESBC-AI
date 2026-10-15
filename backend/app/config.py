from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / "backend" / ".env"
SOURCES_DIR = BASE_DIR / "data" / "sources"
CHROMA_DIR = BASE_DIR / "backend" / ".chroma"
COLLECTION = "esbc_kb"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
REQUIRED_META = ["service", "title", "url", "date_checked", "language"]