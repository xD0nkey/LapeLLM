#!/usr/bin/env python3
"""
build_lape_lib_docs.py — Generate compact symbol documentation from the existing symbol index.

Reads:   docs/generated/lape_lib_symbol_index.jsonl   (8623 entries)
Writes:  docs/generated/lape_lib_symbol_docs.jsonl    (enriched symbol docs)
         docs/generated/lape_lib_symbol_docs.md       (human-readable overview)

Does NOT read or modify library source files. Works entirely from the symbol index.
Run this before build_lape_rag.py.

Usage:
    py scripts/build_lape_lib_docs.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_PATH = REPO_ROOT / "docs" / "generated" / "lape_lib_symbol_index.jsonl"
DOCS_JSONL = REPO_ROOT / "docs" / "generated" / "lape_lib_symbol_docs.jsonl"
DOCS_MD = REPO_ROOT / "docs" / "generated" / "lape_lib_symbol_docs.md"


# ── Source root detection ────────────────────────────────────────────────────

def derive_source_root(file_path: str) -> str:
    """Map a relative file path to its library name."""
    fp = file_path.replace("\\", "/")
    if fp.startswith("SRL-T/"):
        return "SRL-T"
    if fp.startswith("WaspLib/"):
        return "WaspLib"
    if fp.startswith("Farm/"):
        return "Farm"
    return "unknown"


# ── Container detection ──────────────────────────────────────────────────────

def derive_container(name: str) -> str:
    """
    Extract the container record/type from a dotted symbol name.
    'TRSBank.Withdraw' -> 'TRSBank'
    'Withdraw' -> ''
    """
    if "." in name:
        return name.rsplit(".", 1)[0]
    return ""


# ── Signature parsing ────────────────────────────────────────────────────────

def parse_lape_signature(sig: str, kind: str) -> dict:
    """
    Parse a Lape declaration signature conservatively.
    Returns: {return_type: str|None, parameters: list[dict]}
    Never invents information not present in the signature.
    """
    result: dict = {"return_type": None, "parameters": []}
    if not sig:
        return result

    # Field: "FieldName: Type;" or "FieldName, Other: Type;"
    if kind == "field":
        m = re.match(r"[\w\s,]+:\s*(.+?)\s*;?\s*$", sig.strip())
        if m:
            result["return_type"] = m.group(1).strip()
        return result

    # Variable: "VarName: Type;"
    if kind == "variable":
        m = re.match(r"\w+\s*:\s*(.+?)\s*;?\s*$", sig.strip())
        if m:
            result["return_type"] = m.group(1).strip()
        return result

    # Function/method/operator: extract return type after closing paren
    if kind in ("function", "method", "operator"):
        m = re.search(r"\)\s*:\s*([^;{(]+?)\s*(?:;|override|overload|$)", sig, re.IGNORECASE)
        if m:
            result["return_type"] = m.group(1).strip().rstrip(";")

    # Extract parameters from parentheses
    m = re.search(r"\(([^)]*)\)", sig)
    if not m:
        return result
    params_raw = m.group(1).strip()
    if not params_raw:
        return result

    # Split by semicolon (Lape parameter separator)
    for group in params_raw.split(";"):
        group = group.strip()
        if not group:
            continue
        # Strip const/var/out prefix
        clean = re.sub(r"^\s*(const|var|out)\s+", "", group, flags=re.IGNORECASE).strip()
        colon = clean.find(":")
        if colon == -1:
            result["parameters"].append({"raw": group})
            continue
        names_part = clean[:colon].strip()
        type_and_default = clean[colon + 1:].strip()
        # Split off default value
        default_val = None
        if "=" in type_and_default:
            type_str, default_raw = type_and_default.split("=", 1)
            type_str = type_str.strip()
            default_val = default_raw.strip()
        else:
            type_str = type_and_default.strip()
        for nm in names_part.split(","):
            param: dict = {"name": nm.strip(), "type": type_str}
            if default_val is not None:
                param["default"] = default_val
            result["parameters"].append(param)

    return result


# ── Summary generation ───────────────────────────────────────────────────────

# Summaries that are so generic they should be replaced with a structured one
_GENERIC_STARTS = (
    "Returns ",
    "Procedure ",
    "Function ",
    "Method on",
    "Global variable",
    "Include directive",
    "Alias for",
    "Alias:",
    "Enum value",
    "Constant ",
    "Declares ",
    "Record type",
    "Field of",
    "Record field",
)


def _is_generic_summary(text: str) -> bool:
    if not text or len(text) < 20:
        return True
    return any(text.startswith(p) for p in _GENERIC_STARTS)


def make_summary(entry: dict, parsed: dict) -> str:
    """
    Build a short (≤200 char), conservative, non-hallucinating summary.
    Uses existing summary when it appears genuinely informative.
    Falls back to a minimal structured description based only on declared facts.
    """
    existing = (entry.get("summary") or "").strip()
    name = entry.get("name", "")
    kind = (entry.get("kind") or "").lower()
    container = derive_container(name)
    rt = parsed.get("return_type") or ""
    params = parsed.get("parameters") or []

    # Keep existing summary if it looks informative
    if existing and not _is_generic_summary(existing):
        return existing[:200]

    # Build a minimal, honest replacement
    if kind == "field":
        if container:
            return f"Field of {container}. Type: {rt}." if rt else f"Field of {container}."
        return f"Record field. Type: {rt}." if rt else "Record field."

    if kind == "variable":
        return f"Global variable of type {rt}." if rt else "Global variable."

    if kind == "record":
        return f"Record type {name}. Inspect source for field list and inheritance."

    if kind in ("function", "method", "procedure"):
        on = f"on {container}" if container else ""
        if rt:
            return f"{'Method' if container else 'Function'} {on}. Returns {rt}. Verify behavior in source before use.".strip()
        return f"{'Method' if container else 'Procedure'} {on}. Inspect source for behavior.".strip()

    if kind == "constant":
        return existing or f"Constant {name}."

    if kind == "enum":
        return f"Enum value in {container}." if container else f"Enum value {name}."

    if kind == "include":
        return existing or f"Include directive: {name}."

    if kind == "alias":
        return existing or f"Alias: {name}."

    if kind == "operator":
        return "Operator declaration. Inspect source for behavior."

    return existing or f"Declares {kind} {name}. Inspect source for details."


# ── Entry enrichment ─────────────────────────────────────────────────────────

_CONFIDENCE_MAP = {"confirmed": "high", "partial": "medium", "unclear": "low"}


def enrich_entry(entry: dict) -> dict:
    """Convert one symbol_index entry into a symbol_docs entry."""
    name = entry.get("name", "")
    kind = (entry.get("kind") or "").lower()
    sig = entry.get("signature", "") or ""
    file_path = entry.get("file_path", "") or ""
    location = entry.get("location", 0)
    uncertainty = (entry.get("uncertainty") or "").strip()
    raw_conf = (entry.get("confidence") or "").lower()
    confidence = _CONFIDENCE_MAP.get(raw_conf, "medium")

    container = derive_container(name)
    source_root = derive_source_root(file_path)
    parsed = parse_lape_signature(sig, kind)
    summary = make_summary(entry, parsed)
    line_num = int(location) if isinstance(location, (int, float)) else 0

    return {
        "name": name,
        "kind": kind,
        "signature": sig,
        "summary": summary,
        "file_path": file_path,
        "line_start": line_num,
        "line_end": line_num,
        "container": container,
        "parent": "",  # record inheritance not inferrable without full parse
        "return_type": parsed.get("return_type") or "",
        "parameters": parsed.get("parameters") or [],
        "source_root": source_root,
        "confidence": confidence,
        "notes": uncertainty,
    }


# ── I/O helpers ──────────────────────────────────────────────────────────────

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
                print(f"[WARN] Line {lineno}: {exc}", file=sys.stderr)
    return entries


def write_jsonl(docs: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")


def write_md(docs: list[dict], path: Path) -> None:
    by_root: dict = defaultdict(lambda: defaultdict(list))
    for doc in docs:
        by_root[doc["source_root"]][doc["file_path"]].append(doc)

    lines = [
        "# Lape Library Symbol Docs",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"Total entries: {len(docs)}  ",
        "Source: `docs/generated/lape_lib_symbol_index.jsonl`  ",
        "Built by: `scripts/build_lape_lib_docs.py`",
        "",
        "Do not edit manually — regenerate by running the build script.",
        "",
        "---",
        "",
    ]

    for root in ("SRL-T", "WaspLib", "Farm", "unknown"):
        if root not in by_root:
            continue
        lines += [f"## {root}", ""]
        for fp in sorted(by_root[root].keys()):
            entries_in_file = by_root[root][fp]
            lines += [f"### `{fp}`", ""]
            for doc in entries_in_file:
                sig = doc["signature"]
                summ = doc["summary"]
                notes = doc.get("notes", "")
                lines.append(f"**{doc['name']}** _{doc['kind']}_  line {doc['line_start']}")
                if sig:
                    lines += ["```", sig, "```"]
                lines.append(f"_{summ}_")
                if notes:
                    lines.append(f"Notes: {notes}")
                lines.append("")
        lines += ["---", ""]

    path.write_text("\n".join(lines), encoding="utf-8")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Loading index from {INDEX_PATH} ...")
    if not INDEX_PATH.exists():
        print(f"[ERROR] Index not found: {INDEX_PATH}", file=sys.stderr)
        sys.exit(1)

    entries = load_jsonl(INDEX_PATH)
    print(f"Loaded {len(entries)} entries.")

    print("Enriching entries...")
    docs = [enrich_entry(e) for e in entries]

    # Stats
    by_root: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for doc in docs:
        by_root[doc["source_root"]] = by_root.get(doc["source_root"], 0) + 1
        by_kind[doc["kind"]] = by_kind.get(doc["kind"], 0) + 1

    print("\nSource root breakdown:")
    for r, n in sorted(by_root.items()):
        print(f"  {r}: {n}")
    print("\nKind breakdown:")
    for k, n in sorted(by_kind.items(), key=lambda x: -x[1]):
        print(f"  {k}: {n}")

    print(f"\nWriting {DOCS_JSONL} ...")
    write_jsonl(docs, DOCS_JSONL)

    print(f"Writing {DOCS_MD} ...")
    write_md(docs, DOCS_MD)

    print(f"\nDone. {len(docs)} symbol docs written.")


if __name__ == "__main__":
    main()
