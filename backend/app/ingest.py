"""Ingest official source documents into the Chroma vector store."""
import re
import sys

import chromadb

from app.config import CHROMA_DIR, COLLECTION, REQUIRED_META, SOURCES_DIR
from app.embeddings import embed


def parse_doc(path):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if not m:
        raise ValueError(f"{path.name}: front matter (--- ... ---) is missing")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    missing = [k for k in REQUIRED_META if not meta.get(k)]
    if missing:
        raise ValueError(f"{path.name}: missing fields {missing}")
    return meta, m.group(2).strip()


def split_sentences(text):
    parts = re.split(r"(?<=[\u0964.?!])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text, max_chars=800, overlap=120):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units = []
    for p in paragraphs:
        units.extend([p] if len(p) <= max_chars else split_sentences(p))

    chunks, current = [], ""
    for unit in units:
        if current and len(current) + len(unit) + 1 > max_chars:
            chunks.append(current)
            current = current[-overlap:] + " " + unit
        else:
            current = f"{current}\n{unit}" if current else unit
    if current:
        chunks.append(current)
    return chunks


def main():
    files = sorted(SOURCES_DIR.rglob("*.md"))
    if not files:
        sys.exit(f"No .md files found in {SOURCES_DIR}")

    ids, docs, metas, embed_texts = [], [], [], []
    for path in files:
        meta, body = parse_doc(path)
        keywords = meta.get("keywords", "")
        for i, chunk in enumerate(chunk_text(body)):
            ids.append(f"{path.stem}-{i}")
            docs.append(chunk)
            # Bilingual search keywords help English questions find Bangla pages and the reverse.
            embed_texts.append(f"{chunk}\nKeywords: {keywords}" if keywords else chunk)
            metas.append({**meta, "source_file": path.name, "chunk": i})

    print(f"{len(files)} files -> {len(docs)} chunks")
    embeddings = embed(embed_texts, "RETRIEVAL_DOCUMENT")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
    print(f"Done. Stored {collection.count()} chunks in {CHROMA_DIR}")


if __name__ == "__main__":
    main()
