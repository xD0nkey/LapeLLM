# Lape Library Retrieval — Fallback Command Reference

`scripts/search_lape_libs.py` is the **primary retrieval fallback** for querying the symbol index until the MCP server is implemented. This document describes what it does, how to use it, its scoring method, its limitations, and example outputs.

---

## What it does

The script searches `docs/generated/lape_lib_symbol_index.jsonl` (8623 entries across SRL-T, WaspLib, and Farm) using keyword matching and `difflib`-based fuzzy similarity. It is **not** vector embedding RAG — it does not use embeddings, cosine similarity, or any ML model. It depends only on the Python standard library.

Results are scored and ranked. Each result includes the symbol name, kind, summary, file path, line number, signature (if available), source snippet (if available), and match reason(s).

---

## Commands

### General query

```
py scripts/search_lape_libs.py "<query>" --limit 10
```

### Field-specific lookup

Use `--kind field` when looking for record fields by parent record name:

```
py scripts/search_lape_libs.py "<record or symbol name>" --kind field --limit 20
```

### Machine-readable JSON output

```
py scripts/search_lape_libs.py "<query>" --json --limit 10
```

### Full option reference

```
py scripts/search_lape_libs.py "<query>" [--limit N] [--kind KIND] [--json]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--limit N` | 10 | Maximum results to show |
| `--kind KIND` | (all) | Filter by symbol kind before scoring |
| `--json` | off | Emit results as a JSON array |

Valid `--kind` values: `field`, `method`, `function`, `procedure`, `record`, `constant`, `variable`, `include`, `alias`, `enum`, `operator`.

---

## Fields searched

The script searches across all of these fields from each index entry:

| Field | Weight tier |
|-------|-------------|
| `name` | Highest (exact match 100 pts, substring 75 pts, token 50 pts, fuzzy 35 pts max) |
| `signature` | High (substring 40 pts, token 22 pts) |
| `summary` | Medium (substring 30 pts, token 15 pts) |
| `related_symbols` | Medium (substring 22 pts, token 10 pts) |
| `file_path` | Medium (token 18 pts) |
| `source_snippet` | Lower (substring 14 pts, token 7 pts) |
| `kind` | Not scored — used only for `--kind` filtering |
| `location` | Not scored — included in output |
| `uncertainty` | Not scored — included in output when non-empty |

---

## Scoring method

Scores are cumulative — a result can hit multiple tiers simultaneously:

```
100  exact name match         (name == query, case-insensitive)
 75  name contains query      (full query string is a substring of name)
 50  name token match         (any query token appears in name)
+35  fuzzy name bonus         (difflib ratio >= 0.75, scaled: ratio × 35)

 40  signature match          (full query is substring of signature)
 22  signature token match    (any query token in signature)

 30  summary match            (full query is substring of summary)
 15  summary token match      (any query token in summary)

 22  related symbol match     (full query in related_symbols)
 10  related token match      (any query token in related_symbols)

 18  file path match          (any query token in file_path)

 14  snippet match            (full query in source_snippet)
  7  snippet token match      (any query token in source_snippet)
```

Tokenization splits on whitespace, underscores, hyphens, and dots, and also splits CamelCase subwords into lowercase parts. Single-character tokens are dropped. Example: `"TRSObjectV2 fields"` → tokens `['trsobjectv2', 'trsobjectv', 'fields']`.

---

## This is keyword/fuzzy retrieval, not vector embedding RAG

This script does **not** use:
- Vector embeddings
- Cosine similarity
- Any ML model or external AI service
- Any dependency outside the Python standard library (`difflib`, `json`, `re`, `argparse`, `pathlib`)

It is a fast, deterministic keyword search with basic fuzzy name matching. For semantic queries ("find a function that does X conceptually"), it will match only if the concept appears literally in the name, signature, summary, or snippet fields. Many of the auto-generated summaries are brief (e.g. `"Field of TRSBank. Type: TRSItemInterface."`) so semantic precision is limited.

**MCP status**: the `search_lape_libs` MCP tool described in CLAUDE.md is not yet configured. Once it is, it will use the same JSONL as its source and return results in the same format, but with better semantic ranking via embeddings. Until then, this script is the required fallback.

---

## Limitations

1. **Summary quality**: Most summaries were generated mechanically (`"Returns Boolean"`, `"Field of X. Type: Y."`). They are accurate but not descriptive. Queries for conceptual meaning ("function that converts text to integer") will match poorly if the relevant function is not named suggestively.

2. **No semantic understanding**: "parse integer" returns `TIntegerArray.*` methods because `integer` is a token in their names and signatures. It does not return `StrToInt` or similar conversion functions unless those words appear literally.

3. **Token granularity**: CamelCase splitting helps (e.g. `"TRSObjectV2"` produces the token `"trsobjectv2"`) but very long qualified names like `PRSMapObjectArray.GetClosest` may score unexpectedly high for short queries due to token overlap.

4. **Duplicate entries**: Some symbols appear in both `SRL-T/osr/map/mapobject.simba` and `SRL-T/osr/map/objects.simba` (a known dead-code file in SRL-T). The index contains both, and both will appear in results. Prefer entries from `mapobject.simba` — see `docs/README.md` for the known-gaps note about `objects.simba`.

5. **Mechanical field summaries**: The 1250 record fields added in the third scan pass have auto-generated summaries (`"Field of RecordName. Type: T."`). They do not describe the field's purpose. Use `--kind field` and then read the source file to understand what a field does.

6. **`py` launcher required**: On this system, Python is invoked via `py` (the Python Launcher for Windows), not `python`. Always use `py scripts/search_lape_libs.py ...`.

7. **Result verification**: The script returns what the index says at scan time. The index was scanned on 2026-07-01. Always verify signatures and behavior against the actual source file using the `file_path` and `location` returned in each result.

---

## Example outputs

All examples below use `--limit 5` for brevity.

### `"file handling"`

```
py scripts/search_lape_libs.py "file handling" --limit 5
```

Top results: `files`, `BackupFile`, `RestoreFile`, `DeleteFiles`, `_SkipFile` — all from `SRL-T/utils/system/file.simba`. Scoring driven by `file` token in name and file_path, plus `handling` token in signature/summary.

### `"string manipulation"`

```
py scripts/search_lape_libs.py "string manipulation" --limit 5
```

Top results: `String.Pos`, `String.PosR`, `String.PosEx`, `String.Capitalize`, `String.Upper` — all from `SRL-T/utils/string.simba`. Scoring driven by `string` token in name and related_symbols.

### `"array"`

```
py scripts/search_lape_libs.py "array" --limit 5
```

Top results: `PRSMapObjectArray.*` methods. `array` is a substring of `mapobjectarray` in the file path and name, giving high scores. For more targeted results, query `"TPointArray"` or a specific array type.

### `"parse integer"`

```
py scripts/search_lape_libs.py "parse integer" --limit 5
```

Top results: `TIntegerArray.*` methods. Limitation: no function literally named "parse integer" exists. If looking for string-to-int conversion, query `"StrToInt"` or `"ExtractNumber"` instead.

### `"TRSObjectV2 fields"`

```
py scripts/search_lape_libs.py "TRSObjectV2 fields" --limit 5
```

Top results: `TRSObjectV2` (record), `TRSObjectV2.Find`, `TRSObjectV2.FindEx`. For the actual record fields, use `--kind field` instead (see next example).

### `"TRSObjectV2" --kind field`

```
py scripts/search_lape_libs.py "TRSObjectV2" --kind field --limit 5
```

Top results: `TRSObjectV2.ObjType` (score 127), `TRSObjectV2.Rotations` (score 127), then fields of other records that use `TRSObjectV2` as a type (`TRSBanks.ObjectsCache`, `TBirdHouse.Obj`, `TFarmPatch.Obj`). The top 2 are the actual fields belonging to `TRSObjectV2`. Note: `TRSMapObject` is the parent record; query `"TRSMapObject" --kind field` to see the inherited fields.

### `"Bank withdraw"`

```
py scripts/search_lape_libs.py "Bank withdraw" --limit 5
```

Top results: `BANK_WITHDRAW_ALL` (constant), `TRSBankItem.GetNoted`, `Bank.Setup`, `TRSBank.Setup`, `TRSBank.SetupAlignment`. For the actual withdraw methods, increase `--limit` or query `"TRSBank.Withdraw"` directly.

### `"Mouse uptext"`

```
py scripts/search_lape_libs.py "Mouse uptext" --limit 5
```

Top results: `TMouse._Debug`, `TMouse.Setup`, `TMouse.WindMouse`, `TMouse.Idle` — all `TMouse.*` methods from `SRL-T/utils/input/mouse.simba`. The `mouse` token dominates; `uptext` does not appear as a standalone method name. For uptext checking specifically, query `"UpText"` or `"IsUpText"` directly.

### `"TBaseScript"`

```
py scripts/search_lape_libs.py "TBaseScript" --limit 5
```

Top results: `TBaseScript` (record, exact match, score 170), `TBaseScript.PrintReport`, `TBaseScript.Init`, `TBaseScript.SetAction`, `TBaseScript.ShouldHandlePaint` — all from `WaspLib/osr/basescript.simba`. Exact and substring name matches give strong scores.

---

## How Claude must use this script

Per `CLAUDE.md`:

1. Before answering any Lape question, run the script first:
   ```
   py scripts/search_lape_libs.py "<query>" --limit 10
   ```
2. For record field lookups:
   ```
   py scripts/search_lape_libs.py "<record name>" --kind field --limit 20
   ```
3. Use the returned `file_path` and `location` to read the actual source for exact signatures and behavior.
4. The script result is a starting point, not a final answer. Always verify against source when the exact signature, parameter order, or behavior matters.
5. If the script returns no result, fall back to direct source inspection under `C:\Users\sebas\AppData\Local\Simba\Includes\`.
6. Do not claim the script returned a result without actually running it.

## Query strategy

This script is **keyword/fuzzy based, not semantic embedding search.** Broad natural language queries ("function that converts text to integer") only match when those exact words appear in a symbol's name, signature, or summary. When a broad query gives weak or off-topic results, retry with specific terms:

- Use exact or likely symbol names, type names, or field names instead of descriptions.
- Use `--kind field` for record field lookups — without it, method results dominate.
- If you suspect a function name, query it directly rather than describing what it does.

Examples of targeted retries that give better results than broad queries:

```
py scripts/search_lape_libs.py "StrToInt" --limit 10
py scripts/search_lape_libs.py "UpText" --limit 10
py scripts/search_lape_libs.py "IsUpText" --limit 10
py scripts/search_lape_libs.py "TRSObjectV2" --kind field --limit 20
```

Two rules that must not be broken:

- **Weak retrieval results are not evidence of absence.** No useful result means the query was not phrased in terms the index contains — not that the symbol does not exist. Inspect the `file_path` values returned and read the source directly.
- **Do not answer from a weak result without source verification.** If a result's summary is generic (`"Returns Boolean"`, `"Procedure X.Y"`), open the cited source file before claiming the symbol behaves a certain way.
