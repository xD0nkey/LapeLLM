#!/usr/bin/env python3
"""
search_lape_rag.py — Semantic RAG search over Lape/SRL-T/WaspLib/Farm library docs.

Requires:  .cache/lape_rag/ to exist (run build_lape_rag.py first)
           py -m pip install chromadb sentence-transformers

Usage:
    py scripts/search_lape_rag.py "how do I withdraw items from the bank" --limit 8
    py scripts/search_lape_rag.py "TRSObjectV2 inherited fields" --limit 8
    py scripts/search_lape_rag.py "how do I check uptext" --limit 8
    py scripts/search_lape_rag.py "which API handles walking to map objects" --limit 8
    py scripts/search_lape_rag.py "StrToInt" --limit 8
    py scripts/search_lape_rag.py "bank withdraw" --json --limit 8

This is semantic vector search — not keyword matching. Natural language queries
work well. Results are finding aids; always verify against source files.

Important caveats:
  - Lape interpreter built-ins (StrToInt, WriteLn, Length, etc.) are not in the
    index — they are defined by the Lape interpreter, not the scanned library files.
  - Weak or empty results are inconclusive. Retry with the keyword fallback:
    py scripts/search_lape_libs.py "<query>" --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "lape_rag"
COLLECTION_NAME = "lape_libs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ── ChromaDB collection loader ───────────────────────────────────────────────

_collection = None  # module-level cache for the collection object


def get_collection():
    """Load and cache the ChromaDB collection. Exits on failure."""
    global _collection
    if _collection is not None:
        return _collection

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

    if not CACHE_DIR.exists():
        print(
            f"[ERROR] RAG index not found at {CACHE_DIR}\n"
            "Build it first: py scripts/build_lape_rag.py",
            file=sys.stderr,
        )
        sys.exit(1)

    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(CACHE_DIR))

    try:
        _collection = client.get_collection(COLLECTION_NAME, embedding_function=ef)
    except Exception as exc:
        print(
            f"[ERROR] Cannot open collection '{COLLECTION_NAME}': {exc}\n"
            "Rebuild: py scripts/build_lape_rag.py",
            file=sys.stderr,
        )
        sys.exit(1)

    return _collection


# ── Metadata filter builder ──────────────────────────────────────────────────

def build_where(
    kind: str | None,
    source_root: str | None,
    chunk_type: str | None,
) -> dict | None:
    """Build a ChromaDB $and/$eq metadata filter from optional CLI args."""
    conds: list[dict] = []
    if kind:
        conds.append({"kind": {"$eq": kind.lower()}})
    if source_root:
        conds.append({"source_root": {"$eq": source_root}})
    if chunk_type:
        conds.append({"chunk_type": {"$eq": chunk_type.lower()}})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


# ── Search ───────────────────────────────────────────────────────────────────

def search(
    query: str,
    limit: int = 8,
    kind: str | None = None,
    source_root: str | None = None,
    chunk_type: str | None = None,
) -> list[dict]:
    """
    Semantic search over the RAG collection.
    Returns a list of result dicts sorted by descending similarity score.
    """
    collection = get_collection()
    n_results = min(limit, collection.count())
    if n_results == 0:
        return []

    kwargs: dict = {
        "query_texts": [query],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    where = build_where(kind, source_root, chunk_type)
    if where:
        kwargs["where"] = where

    raw = collection.query(**kwargs)

    ids = raw.get("ids", [[]])[0]
    distances = raw.get("distances", [[]])[0]
    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]

    results: list[dict] = []
    for i, (rid, dist, doc_text, meta) in enumerate(zip(ids, distances, docs, metas)):
        # ChromaDB returns L2 distances for sentence-transformers EF.
        # Map to a [0,1] similarity score: score = 1 - dist/2
        # (For unit-normalised vectors, max L2 distance = 2.0)
        score = round(max(0.0, 1.0 - dist / 2.0), 4)
        results.append(
            {
                "rank": i + 1,
                "score": score,
                "chunk_type": meta.get("chunk_type", ""),
                "title": meta.get("title", ""),
                "symbol": meta.get("symbol", ""),
                "kind": meta.get("kind", ""),
                "summary": _extract_summary(doc_text),
                "file_path": meta.get("file_path", ""),
                "line_start": meta.get("line_start", 0),
                "line_end": meta.get("line_end", 0),
                "source_root": meta.get("source_root", ""),
                "container": meta.get("container", ""),
                "confidence": meta.get("confidence", ""),
                "text": doc_text,
            }
        )
    return results


def _extract_summary(text: str, max_len: int = 200) -> str:
    """Extract the 'Summary:' line from a chunk, or fall back to the first content line."""
    for line in text.splitlines():
        if line.startswith("Summary:"):
            return line[8:].strip()[:max_len]
    # Fallback: first non-bracket line
    for line in text.splitlines()[1:]:
        stripped = line.strip()
        if stripped and not stripped.startswith("["):
            return stripped[:max_len]
    return text[:max_len]


# ── Output formatting ────────────────────────────────────────────────────────

def _trunc(s: str, n: int = 120) -> str:
    return s[:n] + "…" if len(s) > n else s


def format_human(r: dict) -> str:
    kind_label = r["kind"] or r["chunk_type"]
    lib = f"  [{r['source_root']}]" if r.get("source_root") else ""
    lines = [
        f"[{r['rank']}] {r['title']}  score={r['score']:.3f}{lib}",
        f"    Kind     : {kind_label}",
        f"    File     : {r['file_path']}  line {r['line_start']}",
    ]
    if r.get("summary"):
        lines.append(f"    Summary  : {_trunc(r['summary'], 160)}")
    # Show first line of raw text if it adds info
    first_line = r["text"].splitlines()[0] if r.get("text") else ""
    if first_line and not first_line.startswith("["):
        lines.append(f"    Preview  : {_trunc(first_line, 120)}")
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="search_lape_rag",
        description=(
            "Semantic RAG search over Lape/SRL-T/WaspLib/Farm library docs.\n"
            "Requires .cache/lape_rag/ built by scripts/build_lape_rag.py.\n\n"
            "This is vector embedding search — natural language queries work well.\n"
            "Results are finding aids. Always verify against source files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", help="Natural language query or symbol name")
    parser.add_argument(
        "--limit", type=int, default=8, metavar="N",
        help="Maximum results (default: 8)",
    )
    parser.add_argument(
        "--kind", metavar="KIND",
        help="Filter by symbol kind: field, method, function, record, constant, …",
    )
    parser.add_argument(
        "--source-root", metavar="ROOT",
        help="Filter by library: SRL-T, WaspLib, Farm, repo_docs",
    )
    parser.add_argument(
        "--chunk-type", metavar="TYPE",
        help=(
            "Filter by chunk type: symbol_doc, record_doc, field_doc, "
            "repository_doc, policy_doc"
        ),
    )
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Emit results as a JSON array",
    )
    args = parser.parse_args()

    query = args.query.strip()
    if not query:
        print("[ERROR] Query must be non-empty.", file=sys.stderr)
        sys.exit(1)

    results = search(
        query=query,
        limit=args.limit,
        kind=args.kind,
        source_root=getattr(args, "source_root", None),
        chunk_type=getattr(args, "chunk_type", None),
    )

    if args.json_out:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    print(
        f"Query: '{query}'"
        f"  |  limit={args.limit}"
        f"  |  results={len(results)}"
    )
    if args.kind:
        print(f"Filter: kind={args.kind}")
    if getattr(args, "source_root", None):
        print(f"Filter: source_root={args.source_root}")
    print()

    if not results:
        print("No results found.")
        print()
        print("Suggestions:")
        print("  - Rebuild the index: py scripts/build_lape_rag.py")
        print("  - Lape built-ins (StrToInt, WriteLn, etc.) are not in the index.")
        print("  - Try the keyword fallback: py scripts/search_lape_libs.py \"<query>\" --limit 10")
        return

    for r in results:
        print(format_human(r))
        print()

    print("---")
    print("RAG results are finding aids — always verify against source files.")
    print("Keyword fallback: py scripts/search_lape_libs.py \"<query>\" --limit 10")


if __name__ == "__main__":
    main()
