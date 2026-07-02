#!/usr/bin/env python3
"""
build_lape_rag.py — Build a local ChromaDB vector index from Lape library symbol docs
and repository documentation.

Dependencies:
    py -m pip install chromadb sentence-transformers

Reads:
    docs/generated/lape_lib_symbol_docs.jsonl   (primary — run build_lape_lib_docs.py first)
    README.md, CLAUDE.md, AGENTS.md
    docs/**/*.md

Writes:
    .cache/lape_rag/                             (ChromaDB persistent store, gitignored)
    docs/generated/lape_rag_manifest.json        (build manifest)

This script always does a clean rebuild (deletes and recreates the collection).

Usage:
    py scripts/build_lape_rag.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "lape_rag"
SYMBOL_DOCS_PATH = REPO_ROOT / "docs" / "generated" / "lape_lib_symbol_docs.jsonl"
MANIFEST_PATH = REPO_ROOT / "docs" / "generated" / "lape_rag_manifest.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "lape_libs"
BATCH_SIZE = 100

# Repo docs to index as policy/reference chunks
REPO_DOC_TARGETS = [
    ("README.md", "repository_doc"),
    ("CLAUDE.md", "policy_doc"),
    ("AGENTS.md", "policy_doc"),
]


# ── ID generation ────────────────────────────────────────────────────────────

def stable_id(text: str, prefix: str = "c") -> str:
    """Content-stable chunk ID. Consistent across rebuilds for the same content."""
    h = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"


# ── Load symbol docs ─────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    entries: list[dict] = []
    with path.open(encoding="utf-8-sig") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n\r")
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[WARN] {path.name} line {lineno}: {exc}", file=sys.stderr)
    return entries


# ── Symbol → chunk ───────────────────────────────────────────────────────────

_CHUNK_TYPE_MAP = {
    "record": "record_doc",
    "field": "field_doc",
}


def symbol_to_chunk(doc: dict) -> dict | None:
    """Convert a symbol_docs entry to a RAG chunk dict."""
    name = doc.get("name", "")
    kind = doc.get("kind", "")
    sig = doc.get("signature", "") or ""
    summary = doc.get("summary", "") or ""
    file_path = doc.get("file_path", "") or ""
    line_start = doc.get("line_start") or 0
    line_end = doc.get("line_end") or line_start
    container = doc.get("container", "") or ""
    source_root = doc.get("source_root", "") or ""
    confidence = doc.get("confidence", "medium") or "medium"
    notes = doc.get("notes", "") or ""

    if not name:
        return None

    chunk_type = _CHUNK_TYPE_MAP.get(kind, "symbol_doc")

    # Build a self-contained text optimized for semantic embedding.
    # Include name, kind, signature, summary, library, location — enough context
    # that a query about "bank withdraw" will embed close to this chunk.
    parts = [f"[{kind}] {name}"]
    if sig:
        parts.append(f"Signature: {sig}")
    if summary:
        parts.append(f"Summary: {summary}")
    if container:
        parts.append(f"Container: {container}")
    if source_root:
        parts.append(f"Library: {source_root}")
    if file_path:
        loc = f" line {line_start}" if line_start else ""
        parts.append(f"File: {file_path}{loc}")
    if notes:
        parts.append(f"Notes: {notes}")

    text = "\n".join(parts)
    chunk_id = stable_id(f"{name}:{file_path}:{line_start}", "s")

    title = f"{name} ({kind})"
    if source_root:
        title = f"{source_root} / {title}"

    # ChromaDB metadata values must be str, int, float, or bool (no None, no list)
    return {
        "id": chunk_id,
        "chunk_type": chunk_type,
        "title": title,
        "text": text,
        "file_path": file_path,
        "line_start": int(line_start),
        "line_end": int(line_end),
        "symbol": name,
        "kind": kind,
        "container": container,
        "source_root": source_root,
        "confidence": confidence,
        "generated_from": "lape_lib_symbol_docs.jsonl",
    }


# ── Markdown file → chunks ───────────────────────────────────────────────────

def chunk_markdown(path: Path, chunk_type: str, max_chars: int = 3500) -> list[dict]:
    """
    Split a Markdown file into H2-section chunks.
    Returns a list of chunk dicts with metadata.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[WARN] Cannot read {path}: {exc}", file=sys.stderr)
        return []

    rel = path.relative_to(REPO_ROOT).as_posix()

    # Split on H2 headings
    parts = re.split(r"(?m)^(## .+)$", text)
    chunks: list[dict] = []

    def _make_doc_chunk(section_text: str, section_title: str) -> dict:
        full_text = f"[{rel} > {section_title}]\n{section_text}"
        cid = stable_id(f"{rel}:{section_title}", "d")
        return {
            "id": cid,
            "chunk_type": chunk_type,
            "title": f"{rel} > {section_title}",
            "text": full_text[:max_chars],
            "file_path": rel,
            "line_start": 0,
            "line_end": 0,
            "symbol": "",
            "kind": "doc",
            "container": "",
            "source_root": "repo_docs",
            "confidence": "high",
            "generated_from": rel,
        }

    if len(parts) <= 1:
        # No H2 sections — chunk the whole file
        if text.strip():
            chunks.append(_make_doc_chunk(text, path.name))
        return chunks

    # Pre-header intro
    intro = parts[0].strip()
    if intro:
        chunks.append(_make_doc_chunk(intro, f"{path.name} (intro)"))

    # Section pairs: [header, body, header, body, ...]
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        section_title = header.lstrip("#").strip()
        full = f"{header}\n{body}"
        chunks.append(_make_doc_chunk(full, section_title))

    return chunks


# ── Build all chunks ─────────────────────────────────────────────────────────

def build_all_chunks(docs: list[dict]) -> list[dict]:
    all_chunks: list[dict] = []
    seen: set[str] = set()

    def add(chunk: dict | None) -> None:
        if chunk and chunk["id"] not in seen:
            all_chunks.append(chunk)
            seen.add(chunk["id"])

    # 1. Symbol docs
    print(f"  Building symbol chunks from {len(docs)} docs...")
    for doc in docs:
        add(symbol_to_chunk(doc))
    sym_count = len(all_chunks)
    print(f"  -> {sym_count} symbol chunks")

    # 2. Repo docs (README, CLAUDE.md, AGENTS.md)
    for rel_path, c_type in REPO_DOC_TARGETS:
        full = REPO_ROOT / rel_path
        if full.exists():
            for c in chunk_markdown(full, c_type):
                add(c)

    # 3. All docs/*.md files
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.is_dir():
        # Exclude the large auto-generated files already covered by symbol chunks
        skip_names = {"lape_lib_symbol_docs.md", "lape_lib_symbol_index.md"}
        for md in sorted(docs_dir.rglob("*.md")):
            if md.name in skip_names:
                continue
            for c in chunk_markdown(md, "repository_doc"):
                add(c)

    doc_count = len(all_chunks) - sym_count
    print(f"  -> {doc_count} repo doc chunks")
    print(f"  Total: {len(all_chunks)} chunks")
    return all_chunks


# ── ChromaDB helpers ─────────────────────────────────────────────────────────

def safe_meta(chunk: dict) -> dict:
    """Strip keys ChromaDB cannot store as metadata (non-scalar, id, text)."""
    skip = {"id", "text"}
    out: dict = {}
    for k, v in chunk.items():
        if k in skip:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif v is None:
            out[k] = ""
        else:
            out[k] = str(v)
    return out


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Dependency check ─────────────────────────────────────────────────────
    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except ImportError:
        print(
            "[ERROR] Missing dependencies. Run:\n"
            "  py -m pip install chromadb sentence-transformers",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Load symbol docs ──────────────────────────────────────────────────────
    if not SYMBOL_DOCS_PATH.exists():
        print(
            f"[ERROR] Symbol docs not found at {SYMBOL_DOCS_PATH}\n"
            "Run first: py scripts/build_lape_lib_docs.py",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Loading symbol docs from {SYMBOL_DOCS_PATH} ...")
    docs = load_jsonl(SYMBOL_DOCS_PATH)
    print(f"Loaded {len(docs)} symbol doc entries.")

    # ── Build chunks ──────────────────────────────────────────────────────────
    print("\nBuilding RAG chunks ...")
    chunks = build_all_chunks(docs)

    if not chunks:
        print("[ERROR] No chunks generated.", file=sys.stderr)
        sys.exit(1)

    # ── Set up ChromaDB ───────────────────────────────────────────────────────
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nInitialising ChromaDB at {CACHE_DIR} ...")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print("Model will be downloaded on first run (~90 MB) and cached locally.")

    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(CACHE_DIR))

    # Clean rebuild
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing '{COLLECTION_NAME}' collection for clean rebuild.")
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME, embedding_function=ef)
    print(f"Created collection '{COLLECTION_NAME}'.")

    # ── Embed and index in batches ────────────────────────────────────────────
    total = len(chunks)
    print(f"\nEmbedding and indexing {total} chunks ...")
    print("This may take several minutes on first run (model download + embedding).\n")

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[safe_meta(c) for c in batch],
        )
        done = min(i + BATCH_SIZE, total)
        print(f"  [{done:>5}/{total}]  {done / total * 100:5.1f}%", end="\r", flush=True)

    print(f"\n  Indexed {total} chunks.             ")

    # ── Chunk type breakdown ──────────────────────────────────────────────────
    type_counts: dict[str, int] = {}
    for c in chunks:
        ct = c["chunk_type"]
        type_counts[ct] = type_counts.get(ct, 0) + 1

    # ── Write manifest ────────────────────────────────────────────────────────
    manifest = {
        "rag_built": True,
        "backend": "chromadb",
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimensions": 384,
        "collection_name": COLLECTION_NAME,
        "chunk_count": total,
        "symbol_doc_count": len(docs),
        "chunk_type_breakdown": type_counts,
        "source_roots": ["SRL-T", "WaspLib", "Farm", "repo_docs"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "index_path": ".cache/lape_rag/",
        "notes": [
            f"Embedding model: {EMBEDDING_MODEL} (384-dim, sentence-transformers)",
            "Vector store: ChromaDB (local persistent, gitignored at .cache/lape_rag/)",
            "RAG results are finding aids — verify all claims against source files.",
            "Lape built-ins (StrToInt, WriteLn, etc.) are not in the scanned library index "
            "and will not appear in RAG results.",
            "Rebuild after any library update: py scripts/build_lape_lib_docs.py && py scripts/build_lape_rag.py",
        ],
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Manifest written to {MANIFEST_PATH}")

    print("\n=== Build complete ===")
    print(f"Chunks indexed    : {total}")
    print(f"Symbol docs       : {len(docs)}")
    print(f"Chunk breakdown   :")
    for ct, n in sorted(type_counts.items()):
        print(f"  {ct:<22} {n}")
    print(f"Index path        : {CACHE_DIR}")


if __name__ == "__main__":
    main()
