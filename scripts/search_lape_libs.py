#!/usr/bin/env python3
"""
search_lape_libs.py - keyword/fuzzy retrieval over lape_lib_symbol_index.jsonl

This is NOT vector-embedding RAG. It is a fast, zero-external-dependency,
keyword + difflib-fuzzy search. Use it until the MCP server is implemented.

Usage:
    python scripts/search_lape_libs.py "TRSObjectV2 fields" --limit 10
    python scripts/search_lape_libs.py "TRSObjectV2" --kind field --limit 20
    python scripts/search_lape_libs.py "Bank withdraw" --json
    python scripts/search_lape_libs.py "Mouse uptext" --limit 5

Exit codes:
    0  - success (even if no matches found)
    1  - index file cannot be opened/read at all
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

INDEX_PATH = Path(__file__).parent.parent / "docs" / "generated" / "lape_lib_symbol_index.jsonl"


def tokenize(text: str) -> list[str]:
    """
    Split a query into lowercase search tokens.
    Handles whitespace separators and CamelCase sub-words.
    Drops single-character tokens to avoid noise.
    """
    raw = re.split(r"[\s_\-\.]+", text.lower())
    camel: list[str] = []
    for part in raw:
        camel.extend(re.findall(r"[a-z]+|[0-9]+", part))
    all_tokens = list({t for t in raw + camel if len(t) > 1})
    return all_tokens


def score_entry(entry: dict, query: str, tokens: list[str]) -> tuple[int, list[str]]:
    """
    Score one index entry against a query string.

    Scoring tiers (cumulative — a result can hit multiple tiers):
      100  exact name match
       75  name contains full query string
       50  name contains at least one query token
      +35  difflib fuzzy name match (ratio >= 0.75), scaled
       40  signature contains full query string
       22  signature contains at least one token
       30  summary contains full query string
       15  summary contains at least one token
       22  related_symbols contains full query string
       18  file_path contains at least one token
       10  related_symbols contains at least one token
       14  source_snippet contains full query string
        7  source_snippet contains at least one token

    Returns (score, list_of_match_reasons).
    """
    score = 0
    reasons: list[str] = []

    name = (entry.get("name") or "").strip()
    signature = (entry.get("signature") or "").strip()
    summary = (entry.get("summary") or "").strip()
    file_path = (entry.get("file_path") or "").strip()
    source_snippet = (entry.get("source_snippet") or "").strip()
    related = " ".join(entry.get("related_symbols") or [])

    q = query.lower()
    n = name.lower()
    sig = signature.lower()
    summ = summary.lower()
    fp = file_path.lower()
    snip = source_snippet.lower()
    rel = related.lower()

    # Name scoring
    if n == q:
        score += 100
        reasons.append("exact name match")
    elif q in n:
        score += 75
        reasons.append("name contains query")
    elif any(t in n for t in tokens):
        score += 50
        reasons.append("name token match")

    # Difflib fuzzy name (only when name scoring is below substring level)
    if score < 75:
        ratio = difflib.SequenceMatcher(None, q, n).ratio()
        if ratio >= 0.75:
            bonus = int(ratio * 35)
            score += bonus
            reasons.append(f"fuzzy name ({ratio:.2f})")

    # Signature scoring
    if signature:
        if q in sig:
            score += 40
            reasons.append("signature match")
        elif any(t in sig for t in tokens):
            score += 22
            reasons.append("signature token match")

    # Summary scoring
    if q in summ:
        score += 30
        reasons.append("summary match")
    elif any(t in summ for t in tokens):
        score += 15
        reasons.append("summary token match")

    # Related symbols scoring
    if q in rel:
        score += 22
        reasons.append("related symbol match")
    elif any(t in rel for t in tokens):
        score += 10
        reasons.append("related token match")

    # File path scoring
    if any(t in fp for t in tokens):
        score += 18
        reasons.append("file path match")

    # Source snippet scoring
    if source_snippet:
        if q in snip:
            score += 14
            reasons.append("snippet match")
        elif any(t in snip for t in tokens):
            score += 7
            reasons.append("snippet token match")

    return score, reasons


def load_index(path: Path) -> tuple[list[dict], int]:
    """
    Load the JSONL index.
    Returns (entries, bad_line_count).
    Prints a warning per bad line to stderr.
    Exits with code 1 if the file cannot be opened at all.
    """
    entries: list[dict] = []
    bad = 0
    try:
        with path.open(encoding="utf-8-sig") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.rstrip("\n\r")
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    bad += 1
                    print(f"[WARN] Line {lineno}: invalid JSON — {exc}", file=sys.stderr)
    except OSError as exc:
        print(f"[ERROR] Cannot open index at {path}: {exc}", file=sys.stderr)
        sys.exit(1)
    return entries, bad


def _truncate(text: str, max_len: int = 120) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


def format_result_human(entry: dict, score: int, reasons: list[str], rank: int) -> str:
    lines = [
        f"[{rank}] {entry.get('name', '?')}  ({entry.get('kind', '?')})  score={score}",
        f"    File    : {entry.get('file_path', '')} line {entry.get('location', '')}",
    ]
    sig = entry.get("signature", "")
    if sig:
        lines.append(f"    Signature: {_truncate(sig, 100)}")
    summ = entry.get("summary", "")
    if summ:
        lines.append(f"    Summary  : {_truncate(summ, 140)}")
    snip = entry.get("source_snippet", "")
    if snip:
        lines.append(f"    Snippet  : {_truncate(snip, 120)}")
    unc = entry.get("uncertainty", "")
    if unc:
        lines.append(f"    Note     : {_truncate(unc, 100)}")
    lines.append(f"    Match    : {', '.join(reasons)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="search_lape_libs",
        description=(
            "Keyword/fuzzy search over lape_lib_symbol_index.jsonl.\n"
            "This is the retrieval fallback used until the MCP server is implemented."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", help="Search query (natural language or symbol name)")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of results to show (default: 10)",
    )
    parser.add_argument(
        "--kind",
        metavar="KIND",
        help=(
            "Filter by symbol kind before scoring. "
            "Valid values: field, method, function, procedure, record, "
            "constant, variable, include, alias, enum, operator, other"
        ),
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit results as a JSON array instead of human-readable text",
    )
    args = parser.parse_args()

    entries, bad_lines = load_index(INDEX_PATH)
    if not entries:
        print("[ERROR] Index loaded 0 entries — cannot search.", file=sys.stderr)
        sys.exit(1)

    query = args.query.strip()
    tokens = tokenize(query)

    # Kind filter
    candidates = entries
    if args.kind:
        k_filter = args.kind.strip().lower()
        filtered = [e for e in entries if (e.get("kind") or "").lower() == k_filter]
        if filtered:
            candidates = filtered
        else:
            print(
                f"[WARN] No entries with kind='{args.kind}' — searching all kinds instead.",
                file=sys.stderr,
            )

    # Score every candidate
    scored: list[tuple[int, list[str], dict]] = []
    for entry in candidates:
        s, r = score_entry(entry, query, tokens)
        if s > 0:
            scored.append((s, r, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = scored[: args.limit]

    if args.json_out:
        out = []
        for rank, (s, r, e) in enumerate(results, 1):
            row = dict(e)
            row["score"] = s
            row["match_reasons"] = r
            row["rank"] = rank
            out.append(row)
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(
            f"Query: '{query}'"
            f"  |  tokens: {tokens}"
            f"  |  kind: {args.kind or 'any'}"
        )
        print(
            f"Index: {len(entries)} entries ({bad_lines} bad lines)"
            f"  |  candidates: {len(candidates)}"
            f"  |  scored: {len(scored)}"
            f"  |  showing top {len(results)}"
        )
        print()
        if not results:
            print("No matches found.")
            return
        for rank, (s, r, e) in enumerate(results, 1):
            print(format_result_human(e, s, r, rank))
            print()


if __name__ == "__main__":
    main()
