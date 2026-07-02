# Lape Library MCP Server

`scripts/mcp_lape_libs_server.py` is an MCP server that exposes the Lape/SRL-T/WaspLib/Farm symbol index as a single tool named `search_lape_libs`. It wraps the existing `scripts/search_lape_libs.py` retrieval logic and serves it over the stdio MCP transport.

---

## What it does

The server provides one tool (`search_lape_libs`) that searches `docs/generated/lape_lib_symbol_index.jsonl` (8623 entries) by keyword and fuzzy name matching. It returns ranked results with symbol names, kinds, file paths, line numbers, signatures, and match reasons.

This is **not** vector embedding search. It is the same keyword + `difflib` fuzzy matching used by `scripts/search_lape_libs.py`, exposed as an MCP tool so Claude can call it directly from any MCP-capable client without shell access.

---

## Relationship to `scripts/search_lape_libs.py`

The MCP server imports `load_index`, `score_entry`, and `tokenize` directly from `search_lape_libs.py` at startup. It does not duplicate the search logic. Both tools query the same JSONL index and produce equivalent results:

| | `search_lape_libs.py` | MCP server |
|---|---|---|
| Invocation | `py scripts/search_lape_libs.py "<query>"` | MCP tool call |
| Output format | Human-readable text or `--json` | Always JSON |
| Kind filter | `--kind <kind>` | `kind` parameter |
| Limit | `--limit N` | `limit` parameter |
| Index loaded | Per invocation | Once at server startup |

---

## Dependencies

| Package | Version installed | Install command |
|---------|------------------|-----------------|
| `mcp[cli]` | 1.28.1 | `py -m pip install "mcp[cli]"` |

No other external dependencies. The MCP package pulls in `anyio`, `pydantic`, `httpx`, `starlette`, and `uvicorn` transitively, but these are all handled automatically.

---

## How to run manually

```
py scripts/mcp_lape_libs_server.py
```

The server blocks on stdin/stdout (stdio transport). Send MCP JSON-RPC messages to stdin. This is normally done by an MCP client (Claude Desktop, Claude Code), not by hand.

To verify the server starts without errors:

```
py -c "import scripts.mcp_lape_libs_server"
```

Or from the repo root:

```
py -c "import sys; sys.path.insert(0,'scripts'); import mcp_lape_libs_server; print('OK')"
```

---

## Claude Code configuration

The MCP server is registered in `.claude/settings.local.json` for this project:

```json
{
  "mcpServers": {
    "lape-libs": {
      "command": "py",
      "args": ["scripts/mcp_lape_libs_server.py"]
    }
  }
}
```

Claude Code reads this on startup and makes the `search_lape_libs` tool available to the model. The path `scripts/mcp_lape_libs_server.py` is relative to the project root.

---

## Claude Desktop configuration

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "lape-libs": {
      "command": "py",
      "args": ["C:\\path\\to\\LapeLLM\\scripts\\mcp_lape_libs_server.py"]
    }
  }
}
```

Replace `C:\\path\\to\\LapeLLM` with the absolute path to the repo on the target machine. Use double backslashes in JSON strings on Windows. Restart Claude Desktop after editing.

---

## Tool name

```
search_lape_libs
```

---

## Tool input schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Symbol name, type name, or keyword to search for. Required."
    },
    "limit": {
      "type": "integer",
      "default": 10,
      "description": "Maximum number of results to return. Clamped to 1–50."
    },
    "kind": {
      "type": "string",
      "description": "Optional. Filter by symbol kind before scoring. Valid values: field, method, function, procedure, record, constant, variable, include, alias, enum, operator."
    }
  },
  "required": ["query"]
}
```

---

## Tool output schema

The tool returns a JSON string. Top-level envelope:

```json
{
  "query": "string",
  "kind_filter": "string | null",
  "index_size": 8623,
  "bad_lines_in_index": 0,
  "candidates_after_kind_filter": 1261,
  "total_matches": 12,
  "showing": 10,
  "results": [ ... ],
  "guidance": "string (only present when results are empty or weak)"
}
```

Each result object:

```json
{
  "rank": 1,
  "name": "TRSObjectV2.ObjType",
  "kind": "field",
  "summary": "Field of TRSObjectV2. Integer object-type identifier from game data.",
  "file_path": "SRL-T/osr/map/mapobject.simba",
  "location": 436,
  "score": 127,
  "match_reasons": ["name contains query", "summary match", "related symbol match"],
  "signature": "ObjType: Int32;",
  "source_snippet": "",
  "uncertainty": "unclear from source — exact valid values not stated",
  "related_symbols": ["TRSObjectV2", "TRSMapObject"]
}
```

`signature`, `source_snippet`, `uncertainty`, and `related_symbols` are omitted when empty.

---

## Example tool calls

### Fields of TRSObjectV2

```
search_lape_libs(query="TRSObjectV2", kind="field", limit=20)
```

Returns 12 matches. Top 2: `TRSObjectV2.ObjType` (score 127), `TRSObjectV2.Rotations` (score 127), both from `SRL-T/osr/map/mapobject.simba`.

### Bank withdraw methods

```
search_lape_libs(query="Bank withdraw", limit=10)
```

Returns 357 matches. Top results include `BANK_WITHDRAW_ALL` (constant), `TRSBankItem.GetNoted`, `Bank.Setup`, `TRSBank.Setup` — all from `SRL-T/osr/interfaces/mainscreen/bank.simba`. For the actual withdraw method, query `"TRSBank.Withdraw"` directly.

### Uptext checking

```
search_lape_libs(query="UpText", limit=10)
```

Returns 60 matches. Top results: `TRSMainScreen.GetUpText`, `TRSMainScreen.IsUpText` (mainscreen.simba), `MainScreen.GetUpText`, `MainScreen.IsUpText`.

### TBaseScript overview

```
search_lape_libs(query="TBaseScript", limit=10)
```

Returns 32 matches. Rank 1: `TBaseScript` (record, exact match, score 170) from `WaspLib/osr/basescript.simba`. Followed by all `TBaseScript.*` methods.

### Symbol not in index (Lape built-in)

```
search_lape_libs(query="StrToInt", limit=10)
```

Returns 0 matches. Guidance is included explaining that `StrToInt` is a Lape interpreter built-in — it is not defined in the scanned SRL-T/WaspLib/Farm source files and will never appear in this index. For built-in Lape functions, consult the Lape language documentation directly.

---

## Limitations

1. **Not semantic search.** This tool does not use embeddings, cosine similarity, or any ML model. Conceptual queries ("function that converts a string to a number") will not reliably find `StrToInt`.

2. **Lape built-ins are absent.** The index covers only `SRL-T/`, `WaspLib/`, and `Farm/` source files under the installed Simba Includes directory. Lape interpreter built-ins (`StrToInt`, `IntToStr`, `Length`, `WriteLn`, etc.) are not in any scanned file and will return no results.

3. **Mechanical summaries.** Most auto-generated summaries are brief (`"Returns Boolean"`, `"Field of X. Type: Y."`). Low summary quality means semantic queries match poorly. After getting a result, always verify by reading the source file at `%LOCALAPPDATA%\Simba\Includes\` + `file_path`.

4. **Duplicate entries.** Symbols appearing in both `SRL-T/osr/map/mapobject.simba` and the dead-code file `SRL-T/osr/map/objects.simba` show up twice. Prefer entries from `mapobject.simba`.

5. **Index staleness.** The index was scanned on 2026-07-01. If the SRL-T/WaspLib libraries are updated, the index may be stale. Stale index entries should be re-verified against the actual source file.

6. **Score ties.** Many symbols score identically (same match tier hit). Within a tie, results are ordered by their original position in the JSONL file, not by any secondary relevance signal.

7. **`py` launcher required on this machine.** Python is invoked via the Windows Python Launcher (`py`), not `python`. If deploying on another machine, adjust the `command` in the MCP config accordingly.

---

## Troubleshooting

**Server fails to start with `ModuleNotFoundError: No module named 'mcp'`**

Install the dependency:
```
py -m pip install "mcp[cli]"
```

**Server fails to start with `ModuleNotFoundError: No module named 'search_lape_libs'`**

The server must be run from the project root (so `scripts/` is resolved correctly), or the MCP config must use the absolute path to the server file. Check that `scripts/search_lape_libs.py` exists alongside `scripts/mcp_lape_libs_server.py`.

**`FileNotFoundError` or `OSError` on the JSONL index**

Check that `docs/generated/lape_lib_symbol_index.jsonl` exists. The server resolves it relative to `scripts/mcp_lape_libs_server.py`'s own location (`../docs/generated/...`). If the file is missing, the tool will return a structured error rather than crashing.

**`search_lape_libs` does not appear in Claude's tool list**

1. Confirm `.claude/settings.local.json` contains the `mcpServers` block.
2. Restart the Claude Code session so the config is re-read.
3. Run `py scripts/mcp_lape_libs_server.py` manually to confirm it starts without errors.

**Results look off-target**

The tool uses keyword matching. Rephrase with a more specific symbol name, add `kind="field"`, or query the exact suspected symbol name. Weak results are not proof of absence — they mean the query terms do not appear literally in the index.
