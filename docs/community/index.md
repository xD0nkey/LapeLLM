# Community Notes

This folder captures useful technical information that reaches this repository informally: Discord discussions, answers from experienced script authors, short chat snippets, and other informal community knowledge about Lape, Simba, SRL-T, and WaspLib.

This information can be valuable, but it did not arrive through the same verification process as the rest of `docs/`. A community note must not be treated as equivalent to a confirmed `docs/` topic file unless it has actually been confirmed by source code, a working example, local repository documentation, or official/reference documentation. This folder exists so that useful-but-unverified information has a place to live without being mixed into, or mistaken for, verified documentation.

## Policy

1. Community notes are useful leads, not authoritative documentation.
2. Short Discord answers must be preserved with their original meaning, but rewritten into clear technical English.
3. Do not invent missing context. If the original snippet doesn't say it, the note doesn't say it either.
4. Do not expand a short community answer into a complete API description unless it is verified elsewhere.
5. Mark every note with a confidence level (see below).
6. Mark every note with a source type (see below).
7. Record what the note appears to imply.
8. Record what is still unknown.
9. Record what would confirm it.
10. If the note mentions a symbol, function, method, property, or API, do not assume its signature unless the signature was actually provided or independently confirmed.
11. If a community note is only a hint — no clear symbol, no clear topic — log it in `unresolved.md` rather than forcing it into a topic file.
12. If a note is confirmed later, move or copy the relevant information into the correct topic file under `docs/` (the primary, verified documentation), and update or remove the community note.
13. Community notes are never permission to hallucinate Lape syntax. The rest of `CLAUDE.md`/`AGENTS.md` (never invent syntax, never present a guess as fact, ask for a real example) applies in full to anything sourced from this folder.

## Confidence levels

Every note must be marked with exactly one of these:

- **Confirmed** — verified against source code, a working example, or authoritative documentation. A confirmed note should normally be promoted into the relevant primary `docs/` topic file rather than staying here.
- **Likely** — consistent with known patterns and probably correct, but not independently verified.
- **Unverified** — plausible, but nothing in this repository or its reference sources confirms it yet.
- **Contradictory** — conflicts with another note, with `docs/`, or with the WaspLib source/documentation. The conflict must be stated explicitly, not silently resolved.
- **Deprecated** — was true at some point but is believed to no longer apply (for example, referring to an older SRL-6/SMART-era API instead of the current SRL-T/WaspLib stack; see `docs/legacy-notes.md` for a worked example of this exact failure mode).

## Source types

Every note must be marked with one or more of these:

- **Community discussion** — a Discord message, forum post, or similar informal exchange.
- **Local example** — a real script or script fragment available locally.
- **Local documentation** — another file in this repository's `docs/`.
- **WaspLib source** — the actual installed/published WaspLib or SRL-T source code.
- **WaspLib documentation** — the official WaspLib reference documentation.
- **User provided example** — a script or snippet provided directly by the user in conversation.

## Files in this folder

| File | Purpose |
|---|---|
| [intake-template.md](intake-template.md) | The template to copy for every new community note. |
| [unresolved.md](unresolved.md) | Hints that are too vague or under-specified to file under a specific topic yet. |
| [gui.md](gui.md) | Notes about script GUIs, forms, controls, and on-client overlays. |
| [minimap.md](minimap.md) | Notes about minimap behavior and minimap-related debugging/overlays. |
| [debugging.md](debugging.md) | Notes about debugging techniques, debug overlays, and diagnostic helpers. |
| [api-notes.md](api-notes.md) | Notes about specific symbols/functions/methods that don't fit the other topic files. |

## How an AI agent should use this folder

1. Treat everything here as a lead, not a fact. The confidence level and source type on each note say exactly how much weight it can carry.
2. Before generating any code from a community note: check its confidence level, check its source type, and check whether `docs/` (the primary documentation), a local example, or the actual WaspLib source independently confirms it.
3. Do not generate code from a note that is `Unverified`, `Contradictory`, or `Deprecated`. At most, mention it as an investigation lead and ask the user for a working example or a source-code reference.
4. Do not infer a function signature, object ownership, required import, or runtime behavior from a short chat snippet just because the snippet mentions a symbol name. "What is unknown" in the note is exactly the list of things that must not be guessed.
5. When a note is confirmed (by a working example, by source code, or by official documentation), move or copy the verified content into the correct primary `docs/` topic file, and either delete the community note or update it to `Confirmed` with a pointer to where it now lives. Do not leave confirmed information duplicated indefinitely between a community note and the primary documentation.

## How to add a new note

1. Copy `intake-template.md`.
2. Fill in every section. Do not skip "What is unknown" or "Unsafe assumptions."
3. If the note has a clear topic (GUI, minimap, debugging) and a clear symbol or claim, add it to the matching topic file.
4. If it does not have a clear topic or symbol yet, add it to `unresolved.md` instead.
5. Do not delete the original meaning of the snippet when rewriting it into technical English — rewrite for clarity, not to add or remove claims.
