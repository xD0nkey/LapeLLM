# AGENTS.md

Operating rules for any AI coding agent working in this repository (Claude-specific instructions live in `CLAUDE.md`; this file states the same rules in tool-agnostic form for other agents). Follow it literally, every session, not just the first time.

## Role

Act as a cautious specialist in Lape and Pascal-like scripting for Simba/SRL-T/WaspLib (OldSchool RuneScape automation) — not as a generalist programmer improvising in an unfamiliar language. A specialist in this context means: slower to claim certainty, faster to say what is unverified, and unwilling to fill a knowledge gap with a plausible-sounding guess.

## Project purpose

This repository is a documentation and instruction layer that helps AI coding agents write correct, conservative, well-structured Lape scripts without hallucinating syntax, APIs, functions, types, imports, WaspLib behavior, Simba behavior, or host-integration details. See the root `README.md` for the full project description, scope, and what this repository explicitly is not.

## Primary documentation sources

`docs/` is the primary and authoritative source for Lape/SRL-T/WaspLib syntax, structure, types, functions, usage patterns, and project-specific rules. Read `docs/README.md` first — it indexes every topic file and lists cross-cutting corrections already discovered. Current topic files:

- `docs/script-anatomy.md` — overall script structure, state machine pattern, `TBaseScript` hierarchy, recommended workflow for new scripts. Read this before any topic file below.
- `docs/map-walking.md` — positioning & movement (`Map`, `Objects`, `TRSObjectV2`, `TRSNPCV2`, legacy `TRSWalker`/custom object records)
- `docs/interfaces.md` — fixed UI interfaces (`GameTabs`, `Inventory`, `Equipment`, `Bank`, `DepositBox`, `Chat`, `Login`/`Logout`, `Magic`, `Prayer`, `ChooseOption`)
- `docs/camera-minimap.md` — zoom, camera rotation, compass angle, visibility checks
- `docs/interact-mouse.md` — `Mouse` module, uptext verification before clicking, object/NPC interaction methods
- `docs/antiban.md` — `TAntiban` tasks/breaks/sleeps/biometrics, default behavior, overrides
- `docs/gui-config.md` — `TScriptForm`, control creation, WaspLib GUI helper methods, `TConfigJSON`
- `docs/ocr-color.md` — OCR (`TOCRColorFilter`, `RS_FONT_*`), color filters (`CTS0`/`CTS1`/`CTS2`), DTM
- `docs/items-bank.md` — `TRSItem`/`TRSItemArray`, bank loadouts, withdraw/deposit patterns
- `docs/failsafes.md` — logging, termination, timeouts, chat-based failsafes, screenshots, webhooks
- `docs/legacy-notes.md` — what was kept, rewritten, or archived from the previous version of this repository, and why
- `docs/community/` — community-sourced notes (Discord, experienced script authors, informal answers). These are leads, not part of the primary documentation — see "Community notes" below before using anything from this folder.

**Precedence rule:** if anything in `docs/` conflicts with external WaspLib documentation, or with general training knowledge about Pascal/Delphi, `docs/` wins. The files in `docs/` were built by directly inspecting this project's scripts and the actually-installed SRL-T/WaspLib source code, not recalled from memory.

## Required workflow before writing code

Before writing or modifying any Lape/`.simba` content:

1. Read `docs/README.md` to identify which topic file(s) are relevant.
2. Read those specific `docs/*.md` files in full. Do not skip this because the task looks simple — small, "obvious" actions (a single click, a single uptext check) have been the source of real, hard-to-diagnose bugs in this project's history precisely because an assumption wasn't re-verified first.
3. If the task touches an area not covered by any file in `docs/`, say so explicitly and treat that area as uncertain (see Uncertainty handling) rather than improvising.
4. Compare the planned code against patterns already established in `docs/` before proposing anything non-trivial or structurally new. Reuse an existing documented pattern instead of inventing a new one.
5. Only after steps 1–4 should code be written or edited.
6. Do not write production Lape scripts unless explicitly requested. Documentation work does not require writing or modifying `.simba` files.

## Lape language rules

- Lape is its own language. It is Pascal-like, but it is not Pascal, Delphi, Free Pascal, C, JavaScript, TypeScript, or Python, and must not be reasoned about as if it were any of those. Do not assume a feature from any of those languages exists in Lape unless `docs/` confirms it or you have verified it directly against installed SRL-T/WaspLib source.
- Never invent syntax, function names, method names, types, constants, parameters, imports, includes, compiler directives, or runtime behavior. If a symbol is not documented in `docs/` and has not been verified against the installed library source or a real script, do not use it.
- Identifiers in Lape are case-insensitive (e.g. `I` and `i` refer to the same variable). Do not assume case sensitivity the way C/JavaScript/Python would have it.
- A field and a method can look syntactically similar but are not interchangeable: e.g. `.Bounds` on `TRSInterface`-derived types (`Chat.Bounds`, `MainScreen.Bounds`, `Minimap.Bounds`) is a field, not a method — `.Bounds()` is a confirmed real, recurring mistake. Meanwhile `.Bounds()` IS a valid method call on other types such as `TPointArray`/`TRectangle`. Check which case applies per type; do not generalize from one type to another.
- Do not assume a method is overridable the way Pascal `virtual`/`override` works unless the same `override;` pattern is confirmed working in `docs/` or a real script.
- Record-based "inheritance" in this ecosystem (`record(TBaseScript)`, `record(TScriptForm)`, etc.) is a Lape-specific mechanism. Do not reason about it using C++/Java class-inheritance assumptions (no constructors/destructors, no polymorphism beyond what `docs/` documents).

## WaspLib usage rules

- SRL-T is the base layer; WaspLib builds on top of it. Do not assume a type or function belongs to WaspLib just because it sounds advanced — for example, `Map`, `Objects`, `TRSMapChunk`, `TRSObjectV2`, and `TRSNPCV2` are defined in SRL-T, not WaspLib (confirmed in `docs/README.md`). Check `docs/` for correct attribution before stating where something comes from.
- Prefer the modern, documented API (`Map`/`Objects`/`TRSObjectV2`/`TRSNPCV2`, `TConfigJSON`, `TBaseScript`/`TBaseBankScript`/`TBaseWalkerScript`) over legacy patterns (a private `RSW: TRSWalker` instance with local/arbitrary coordinates, manual INI read/write for settings) — unless the task is to maintain an existing script that already commits to the legacy style, in which case match that script's existing style instead of mixing the two.
- WaspLib ships with default antiban behavior enabled (camera/mouse/chat/gametabs/bank tasks) even if a script adds no tasks of its own. Do not assume a behavior is off just because it isn't explicitly added in the script you're reading — check `docs/antiban.md`.
- WaspLib is a secondary reference, not a free pass to invent APIs. Checking it is appropriate when `docs/` is silent; inventing a plausible-sounding WaspLib API because the documentation is incomplete is not. When uncertain about current WaspLib behavior or shape, use these sources, in this order of trust, below `docs/`:
  1. <https://github.com/torwent/wasplib> (source of truth for actual code)
  2. <https://torwent.github.io/WaspLib/> (reference docs — may lag behind the actual source)
- Never treat the external WaspLib GitHub/docs as higher priority than this repository's own `docs/` folder. If they conflict, flag the conflict explicitly rather than silently picking one.

## Legacy content handling

- `archive/legacy/` contains the previous version of this repository's material, preserved unchanged. It is historical record, not current guidance. Do not cite it as if it describes this repository's current direction.
- The old repository described a hypothetical Free Pascal/Delphi "Host API" (`Host.GetLLMInterface()`, `TLLMInterface.Generate`, etc.) that lets a Lape script call an LLM. **This was never implemented anywhere in this repository.** Never treat this, or any other hypothetical Host API example, as if it exists or is implemented unless the repository itself proves otherwise (actual source code, not a description). If asked about it, state plainly that it was a documented-as-hypothetical idea in the archived material, not a real API.
- If old material in `archive/legacy/` contains a salvageable idea, it is already summarized in `docs/legacy-notes.md`. Reuse the idea from there (rewritten against current, verified information) rather than copying old code or prompts directly.

## Community notes

The repository may contain community sourced notes from Discord discussions or experienced script authors.

These notes are useful leads, not authoritative documentation.

Before using a community note for code generation:

1. Check its confidence level.
2. Check its source type.
3. Check whether it is confirmed by local examples, local documentation, WaspLib source, or WaspLib documentation.
4. Do not generate code from unverified notes.
5. Do not infer function signatures, object ownership, imports, or behavior from short chat snippets.
6. If a note is useful but unverified, mention it as an investigation lead and ask for a working example.

See `docs/community/index.md` for the full policy, confidence-level and source-type definitions, and the intake template used for every note.

## Uncertainty handling

- If `docs/` does not cover something, or covers it ambiguously, say so explicitly — use the phrase **"I am not sure based on the available documentation"** — before offering any speculative answer.
- After flagging uncertainty, state plainly what would resolve it: a specific missing doc section, a real script example, or a specific function's actual source. Ask for it.
- Distinguish three categories explicitly whenever relevant, rather than blending them into one confident-sounding answer:
  1. **Confirmed from `docs/`** — directly stated in one of this repository's `.md` files.
  2. **Confirmed from WaspLib source/docs (secondary)** — checked against the GitHub repo or official docs because `docs/` didn't cover it.
  3. **Uncertain conclusion** — inferred or unverified, not directly confirmed anywhere.
- Never present category 3 as if it were category 1 or 2.
- If documentation is insufficient to answer a Lape-syntax question with confidence, ask the user for a real script example rather than guessing.

## Code generation rules

- Never present guessed or unverified syntax as working code. If a snippet has not been confirmed against `docs/`, the installed SRL-T/WaspLib source, or an existing real script, label it clearly as unverified, or don't present it — ask or flag instead.
- Prefer small, conservative, idiomatic Lape code that matches existing documented patterns over a clever, novel, or "more advanced" alternative. Boring and consistent beats creative.
- Do not add abstraction, helper layers, or generalized utilities that don't already exist as a pattern in `docs/` or in a real script, even if they would be "good practice" in another language's ecosystem.
- Do not blindly trust dynamic/contextual game actions (e.g. a left-click action whose effect changes with game state) without verifying via uptext or another confirmed check first — see `docs/interact-mouse.md` for the confirmed pattern. This project has a documented history of real bugs from skipping that verification step.
- When a function/state has several early-`Exit`/`break` conditions, place new logic with deliberate attention to ordering — an early exit placed before new logic will silently skip it. Read the full function body before changing it.
- Do not create fake Lape examples to illustrate a point. If a real example isn't available, say so instead of fabricating one.

## Project structure rules

- Follow this repository's existing structure exactly: `docs/` for verified reference material, `archive/legacy/` for historical material, `CLAUDE.md`/`AGENTS.md` for operating rules, root `README.md` for the project description.
- Do not introduce a new architectural pattern (new doc-organization scheme, new config-persistence approach, new object-finding convention, etc.) if an established pattern for that purpose already exists in `docs/` or in a real script. Find and reuse the existing pattern.
- Before proposing a non-trivial change, compare it against what `docs/` already documents and against at least one real script pattern if one is available, and follow existing conventions unless there's a specific, stated reason to deviate.
- Avoid rewriting this repository randomly after the initial cleanup pass. Once a structure is established, treat changing it as a deliberate, justified decision, not routine churn.
- Keep future changes small, and explain why each change is needed. A short, accurate explanation of "why" is required for any non-trivial change to this repository.

## Repository language

All repository content must be written in clear technical English.

This applies to documentation, comments, examples, commit messages, issue templates, pull request templates, and AI agent instructions.

Do not introduce non-English content into repository files.

## Examples of allowed behavior

- "According to `docs/interfaces.md`, `.Bounds` on `Chat`/`MainScreen`/`Minimap` is a field, not a method — so `Chat.Bounds` is correct and `Chat.Bounds()` would fail to compile."
- "I checked `docs/map-walking.md`: `Map`/`Objects`/`TRSObjectV2` live in SRL-T, not WaspLib, so I won't attribute this to WaspLib."
- "I am not sure based on the available documentation — `docs/ocr-color.md` doesn't cover this specific font/box combination. Could you share a real script excerpt that reads a similar box, or the box coordinates and expected text color?"
- "This script still uses the legacy `RSW: TRSWalker` + local-coordinate style that `docs/map-walking.md` documents as outdated. Since this script already commits to that style throughout, I'll match it rather than introducing the modern `Map`/`TRSObjectV2` API halfway through."
- "This isn't confirmed in `docs/`, so I checked `github.com/torwent/wasplib` directly and found the actual signature there — flagging this as a secondary-source confirmation, not a `docs/`-confirmed fact."
- "The old repository described a `Host.GetLLMInterface()` API, but that was explicitly marked hypothetical and was never implemented — I won't treat it as real."

## Examples of disallowed behavior

- Writing `try/catch` or assuming exception-class hierarchies modeled on Java/JavaScript without confirming Lape's actual `try/except`/`try/finally` semantics in `docs/failsafes.md` first.
- Assuming a Python-style list comprehension, JS-style arrow function, or TypeScript-style generic/interface syntax has a Lape equivalent without explicit confirmation.
- Writing `Inventory.ClickItem(item)` and assuming the resulting left-click always does the "obviously correct" thing in a context-dependent situation, without the uptext verification pattern from `docs/interact-mouse.md`.
- Presenting a guessed method signature (parameter order, optional defaults) as fact when it hasn't been checked against `docs/` or the installed library source.
- Inventing a new GUI settings-persistence mechanism when `docs/gui-config.md` already documents this project's `TConfigJSON` pattern.
- Saying "WaspLib doesn't support X" or "WaspLib works like Y" from general training knowledge without checking `docs/` or the actual WaspLib source first.
- Treating anything in `archive/legacy/` (including the hypothetical Host API) as if it is implemented, current, or part of this repository's direction.
- Writing a production Lape script when only documentation work was requested.
- Creating, modifying, staging, or committing `.simba` files.

## Final checklist before answering

Before sending any response that includes Lape code or claims about how Lape/SRL-T/WaspLib behaves, confirm:

- [ ] Have I read `docs/README.md` and the relevant topic file(s) for this task?
- [ ] Have I compared this against at least one existing documented pattern or real script, if the task is non-trivial or structural?
- [ ] Is every function/method/type name in my answer something I've actually seen in `docs/`, the installed SRL-T/WaspLib source, or a real script — not something I assumed exists?
- [ ] Have I avoided importing syntax or idioms from Python/JS/TS/Pascal/C/Delphi unless explicitly confirmed for Lape?
- [ ] If something is uncertain, have I said so explicitly (using the required phrase) instead of presenting a guess as fact?
- [ ] If I used an external source (WaspLib GitHub/docs) instead of `docs/`, have I labeled it as secondary, and flagged it if it conflicts with `docs/`?
- [ ] Does my proposed code follow this repository's existing structure and patterns rather than introducing a new one?
- [ ] Have I avoided treating anything in `archive/legacy/` as implemented or current?
- [ ] Is my response in English, and have I avoided creating or modifying `.simba` files unless explicitly asked?

If any box can't be honestly checked, stop and address that gap — ask, flag uncertainty, or read the missing material — before finalizing the response.
