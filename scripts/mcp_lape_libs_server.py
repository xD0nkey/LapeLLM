#!/usr/bin/env python3
"""
mcp_lape_libs_server.py — MCP server exposing three tools:

  search_lape_libs   — keyword/fuzzy search over the symbol index (existing)
  search_lape_rag    — semantic vector search over symbol docs and repo docs
  lape_index_status  — diagnostic report on all loaded indexes

Runs via stdio transport (standard for Claude Desktop / Claude Code MCP integration).

Dependencies:
    py -m pip install "mcp[cli]" chromadb sentence-transformers

Build the RAG index before starting (required for search_lape_rag):
    py scripts/build_lape_lib_docs.py
    py scripts/build_lape_rag.py

Claude Code project config (.claude/settings.local.json):
    {
      "mcpServers": {
        "lape-libs": {
          "command": "py",
          "args": ["scripts/mcp_lape_libs_server.py"]
        }
      }
    }

Claude Desktop config (%APPDATA%\\Claude\\claude_desktop_config.json):
    {
      "mcpServers": {
        "lape-libs": {
          "command": "py",
          "args": ["C:\\\\path\\\\to\\\\LapeLLM\\\\scripts\\\\mcp_lape_libs_server.py"]
        }
      }
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ── Shared paths ──────────────────────────────────────────────────────────────
_scripts_dir = Path(__file__).parent
_repo_root = _scripts_dir.parent
_CACHE_DIR = _repo_root / ".cache" / "lape_rag"
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_COLLECTION_NAME = "lape_libs"

# ── Import keyword search logic ───────────────────────────────────────────────
sys.path.insert(0, str(_scripts_dir))
from search_lape_libs import load_index, score_entry, tokenize  # noqa: E402

# ── Load symbol index ─────────────────────────────────────────────────────────
_INDEX_PATH = _repo_root / "docs" / "generated" / "lape_lib_symbol_index.jsonl"
_DOCS_PATH = _repo_root / "docs" / "generated" / "lape_lib_symbol_docs.jsonl"
_MANIFEST_PATH = _repo_root / "docs" / "generated" / "lape_rag_manifest.json"

_sym_load_error: Optional[str] = None
_entries: list[dict] = []
_bad_lines: int = 0

try:
    _entries, _bad_lines = load_index(_INDEX_PATH)
    if not _entries:
        _sym_load_error = f"Symbol index at {_INDEX_PATH} loaded 0 entries."
except SystemExit:
    _sym_load_error = f"Symbol index not found or unreadable: {_INDEX_PATH}"

# ── Load RAG collection ───────────────────────────────────────────────────────
_rag_collection = None
_rag_load_error: Optional[str] = None
_rag_manifest: dict = {}

try:
    _rag_manifest_text = _MANIFEST_PATH.read_text(encoding="utf-8") if _MANIFEST_PATH.exists() else ""
    if _rag_manifest_text:
        _rag_manifest = json.loads(_rag_manifest_text)
except Exception:
    pass

try:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    if not _CACHE_DIR.exists():
        _rag_load_error = (
            f"RAG index not found at {_CACHE_DIR}. "
            "Build it: py scripts/build_lape_lib_docs.py && py scripts/build_lape_rag.py"
        )
    else:
        _rag_ef = SentenceTransformerEmbeddingFunction(model_name=_EMBEDDING_MODEL)
        _rag_client = chromadb.PersistentClient(path=str(_CACHE_DIR))
        _rag_collection = _rag_client.get_collection(_COLLECTION_NAME, embedding_function=_rag_ef)

except ImportError:
    _rag_load_error = (
        "chromadb or sentence-transformers not installed. "
        "Run: py -m pip install chromadb sentence-transformers"
    )
except Exception as _exc:
    _rag_load_error = f"RAG initialization failed: {_exc}"

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP(
    "lape-libs",
    instructions=(
        "Search Lape/SRL-T/WaspLib/Farm library symbols.\n"
        "Use search_lape_libs for exact symbol/type lookups.\n"
        "Use search_lape_rag for natural language and conceptual queries.\n"
        "Use lape_index_status to check what is loaded."
    ),
)


# ── Tool 1: search_lape_libs (keyword/fuzzy) ──────────────────────────────────

@mcp.tool()
def search_lape_libs(
    query: str,
    limit: int = 10,
    kind: Optional[str] = None,
) -> str:
    """Search the Lape/SRL-T/WaspLib/Farm symbol index for functions, types, record
    fields, constants, methods, and other symbols using keyword and fuzzy matching.

    Returns ranked results with name, kind, summary, file path, line number,
    signature (when available), and match reasons.

    This is keyword + difflib fuzzy matching — NOT vector embedding search.
    For natural language queries, use search_lape_rag instead.

    For best results:
    - Use exact or likely symbol names: "TRSBank.Withdraw", "TRSObjectV2"
    - For record fields: query="TRSObjectV2", kind="field"
    - Broad natural language queries work poorly — use search_lape_rag for those

    Args:
        query: Symbol name, type name, or keyword. Required.
        limit: Maximum results (default 10, max 50).
        kind:  Optional kind filter: field, method, function, procedure, record,
               constant, variable, include, alias, enum, operator.
    """
    if _sym_load_error:
        return json.dumps({
            "error": _sym_load_error,
            "results": [],
            "guidance": (
                "Symbol index failed to load. "
                "Ensure docs/generated/lape_lib_symbol_index.jsonl exists. "
                "Fallback: py scripts/search_lape_libs.py \"<query>\" --limit 10"
            ),
        }, indent=2)

    if not query or not query.strip():
        return json.dumps({"error": "query is required and must be non-empty", "results": []}, indent=2)

    query = query.strip()
    limit = max(1, min(limit, 50))
    tokens = tokenize(query)

    candidates = _entries
    kind_warning: Optional[str] = None
    if kind:
        k = kind.strip().lower()
        filtered = [e for e in _entries if (e.get("kind") or "").lower() == k]
        if filtered:
            candidates = filtered
        else:
            kind_warning = (
                f"No entries with kind='{kind}' — searching all kinds. "
                "Valid: field, method, function, procedure, record, constant, "
                "variable, include, alias, enum, operator."
            )

    scored: list[tuple[int, list[str], dict]] = []
    for entry in candidates:
        s, r = score_entry(entry, query, tokens)
        if s > 0:
            scored.append((s, r, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    results = []
    for rank, (s, reasons, e) in enumerate(top, 1):
        row: dict = {
            "rank": rank,
            "name": e.get("name", ""),
            "kind": e.get("kind", ""),
            "summary": e.get("summary", ""),
            "file_path": e.get("file_path", ""),
            "location": e.get("location", ""),
            "score": s,
            "match_reasons": reasons,
        }
        for f in ("signature", "source_snippet", "uncertainty", "related_symbols"):
            v = e.get(f)
            if v:
                row[f] = v
        results.append(row)

    response: dict = {
        "query": query,
        "kind_filter": kind,
        "index_size": len(_entries),
        "bad_lines_in_index": _bad_lines,
        "candidates_after_kind_filter": len(candidates),
        "total_matches": len(scored),
        "showing": len(results),
        "results": results,
    }
    if kind_warning:
        response["kind_warning"] = kind_warning
    if not results:
        response["guidance"] = (
            "No keyword matches found. "
            "Try search_lape_rag for natural language queries, or rephrase with the exact symbol name. "
            "Fallback: py scripts/search_lape_libs.py \"<query>\" --limit 10"
        )
    elif scored and scored[0][0] < 40:
        response["guidance"] = (
            "Low match scores — results may be off-target. "
            "Try search_lape_rag for a semantic search, or use a more specific symbol name."
        )
    return json.dumps(response, indent=2, ensure_ascii=False)


# ── Tool 2: search_lape_rag (semantic vector search) ─────────────────────────

def _rag_build_where(
    kind: Optional[str],
    source_root: Optional[str],
    chunk_type: Optional[str],
) -> Optional[dict]:
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


def _extract_summary(text: str, max_len: int = 200) -> str:
    for line in text.splitlines():
        if line.startswith("Summary:"):
            return line[8:].strip()[:max_len]
    for line in text.splitlines()[1:]:
        s = line.strip()
        if s and not s.startswith("["):
            return s[:max_len]
    return text[:max_len]


@mcp.tool()
def search_lape_rag(
    query: str,
    limit: int = 8,
    kind: Optional[str] = None,
    source_root: Optional[str] = None,
    chunk_type: Optional[str] = None,
) -> str:
    """Semantic vector search over Lape/SRL-T/WaspLib/Farm library docs and
    repository documentation.

    Uses sentence-transformers (all-MiniLM-L6-v2) embeddings and ChromaDB.
    Natural language queries work well. More useful than search_lape_libs for
    conceptual or broad queries that don't have an exact symbol name.

    Results are finding aids — always verify against source files in
    %LOCALAPPDATA%\\Simba\\Includes\\.

    Important caveats:
    - Lape interpreter built-ins (StrToInt, WriteLn, etc.) are not in the index.
    - RAG results are not authoritative. Source inspection wins.
    - Weak or empty results do not prove a symbol is absent — retry with
      search_lape_libs using an exact symbol name.

    Args:
        query:       Natural language query or symbol name. Required.
        limit:       Maximum results (default 8, max 50).
        kind:        Optional: filter by symbol kind (field, method, function, …)
        source_root: Optional: SRL-T | WaspLib | Farm | repo_docs
        chunk_type:  Optional: symbol_doc | record_doc | field_doc |
                     repository_doc | policy_doc
    """
    if _rag_load_error:
        return json.dumps({
            "error": _rag_load_error,
            "results": [],
            "guidance": (
                "RAG search unavailable. Use search_lape_libs for keyword/fuzzy search. "
                "To build the RAG index: "
                "py scripts/build_lape_lib_docs.py && py scripts/build_lape_rag.py"
            ),
        }, indent=2)

    if not query or not query.strip():
        return json.dumps({"error": "query is required and must be non-empty", "results": []}, indent=2)

    query = query.strip()
    limit = max(1, min(limit, 50))

    try:
        n = min(limit, _rag_collection.count())
        if n == 0:
            return json.dumps({"query": query, "results": [], "guidance": "RAG collection is empty — rebuild."}, indent=2)

        kwargs: dict = {
            "query_texts": [query],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        where = _rag_build_where(kind, source_root, chunk_type)
        if where:
            kwargs["where"] = where

        raw = _rag_collection.query(**kwargs)
    except Exception as exc:
        return json.dumps({"error": f"RAG query failed: {exc}", "results": []}, indent=2)

    ids = raw.get("ids", [[]])[0]
    distances = raw.get("distances", [[]])[0]
    docs_text = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]

    results = []
    for i, (rid, dist, doc_text, meta) in enumerate(zip(ids, distances, docs_text, metas)):
        score = round(max(0.0, 1.0 - dist / 2.0), 4)
        results.append({
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
        })

    response: dict = {
        "query": query,
        "backend": "chromadb",
        "embedding_model": _EMBEDDING_MODEL,
        "filters": {"kind": kind, "source_root": source_root, "chunk_type": chunk_type},
        "results": results,
        "guidance": (
            "RAG results are finding aids — verify all claims in source files at "
            "%LOCALAPPDATA%\\Simba\\Includes\\. "
            "For exact symbol lookups, also use search_lape_libs."
        ),
    }
    if not results:
        response["guidance"] = (
            "No semantic matches found. "
            "Lape built-ins (StrToInt, WriteLn, etc.) are not in this index. "
            "Try search_lape_libs for keyword search, or check that the RAG index is built."
        )

    return json.dumps(response, indent=2, ensure_ascii=False)


# ── Tool 3: lape_index_status (diagnostics) ───────────────────────────────────

@mcp.tool()
def lape_index_status() -> str:
    """Report the current status of all loaded Lape library indexes.

    Returns a JSON object describing:
    - Symbol index (keyword/fuzzy): entry count, load status
    - Symbol docs (enriched index): file existence
    - RAG index (semantic vector): availability, chunk count, backend, model
    - Available MCP tools

    Use this to verify the retrieval system is healthy before writing code.
    """
    # Symbol docs file existence check
    sym_docs_exists = _DOCS_PATH.exists()
    sym_docs_count = 0
    if sym_docs_exists:
        try:
            with _DOCS_PATH.open(encoding="utf-8-sig") as fh:
                sym_docs_count = sum(1 for line in fh if line.strip())
        except OSError:
            sym_docs_count = -1

    # RAG chunk count
    rag_chunks = 0
    if _rag_collection is not None:
        try:
            rag_chunks = _rag_collection.count()
        except Exception:
            rag_chunks = -1

    status: dict = {
        "symbol_index_loaded": _sym_load_error is None and len(_entries) > 0,
        "symbol_index_entries": len(_entries),
        "symbol_index_bad_lines": _bad_lines,
        "symbol_index_error": _sym_load_error,
        "symbol_docs_available": sym_docs_exists,
        "symbol_docs_entries": sym_docs_count,
        "rag_available": _rag_collection is not None,
        "rag_chunks": rag_chunks,
        "rag_backend": "chromadb" if _rag_collection is not None else None,
        "rag_embedding_model": _EMBEDDING_MODEL if _rag_collection is not None else None,
        "rag_index_path": str(_CACHE_DIR) if _CACHE_DIR.exists() else None,
        "rag_error": _rag_load_error,
        "rag_manifest": _rag_manifest if _rag_manifest else None,
        "mcp_tools": ["search_lape_libs", "search_lape_rag", "lape_index_status"],
    }
    return json.dumps(status, indent=2, ensure_ascii=False)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
