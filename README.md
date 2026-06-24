# LapeLLM

## Purpose

This repository is a documentation and instruction layer for AI coding agents (Claude and others) that write or modify Lape scripts. Lape is the Pascal-like scripting language used by Simba to automate OldSchool RuneScape, typically through the SRL-T and WaspLib libraries.

The problem this repository addresses: language models do not reliably know Lape, Simba, SRL-T, or WaspLib. They are far more likely to have been trained on Pascal, Delphi, C, JavaScript, or Python, and they tend to fill gaps in their knowledge by inventing syntax, functions, types, or APIs that look plausible but do not exist. In a scripting environment like Simba, invented syntax does not just fail to compile — it can also compile into code that behaves differently from what was intended, because Lape is permissive and the runtime errors are not always obvious. Hallucinated WaspLib or SRL-T APIs are a specific and recurring version of this problem, because both libraries are large, change over time, and are not part of any model's standard training data in a verified way.

This repository exists to reduce that failure mode: to give an AI agent verified, current reference material before it writes code, and explicit rules for what to do when that material is incomplete.

## Scope

In scope:
- Documentation of Lape language behavior as actually observed in SRL-T/WaspLib source code and real scripts.
- Documentation of SRL-T/WaspLib API usage patterns: interfaces, walking/mapping, antiban, GUI/config, OCR/color detection, items/bank, failsafes.
- Operating instructions for AI coding agents working in this repository or using it as a reference (`CLAUDE.md`, `AGENTS.md`).
- A clear process for what to do when documentation is missing or uncertain.

Out of scope:
- A general-purpose Pascal/Delphi/Free Pascal reference. Lape overlaps with Pascal syntax but is documented here only as it is actually used in Simba/SRL-T/WaspLib scripts.
- Production Lape scripts. This repository does not currently contain runnable `.simba` example scripts (see "Git and file handling" below) and does not claim to.
- An LLM-calling host application. An earlier version of this repository described a hypothetical Free Pascal/Delphi application that would expose LLM provider APIs (OpenAI, Anthropic, etc.) to Lape scripts. That was never implemented and is not part of this repository's current direction. See `docs/legacy-notes.md`.

## SRL-T and WaspLib as core references

This repository is an AI documentation and instruction layer for conservative Lape script generation. SRL-T and WaspLib are both central references for the script ecosystem this repository targets. The repository does not replace either documentation set. Instead, it helps AI agents use those references safely by summarizing verified patterns, recording uncertainty, and pointing to the relevant source material before code is generated.

The main goal is to reduce hallucinated syntax, fake APIs, wrong assumptions, invalid imports, unsupported function calls, and incorrect script structure. This is why the repository tracks uncertainty and missing examples instead of pretending every gap is already documented.

## What this repository is not

- It is not a finished or exhaustive Lape/WaspLib reference. Coverage is uneven: some areas (interfaces, antiban, GUI/config, OCR/color, items/bank, failsafes, map/walking) have been deliberately researched and verified; many others have not been touched at all.
- It is not a guarantee that every statement in `docs/` is still correct. SRL-T and WaspLib are actively developed. Documentation here reflects a verified snapshot, not a live feed.
- It is not a place to find ready-to-run bot scripts.
- It is not a general AI-assistant configuration repository. Everything here is specific to writing Lape code correctly.

## Repository structure

```
README.md              - this file
CLAUDE.md               - operating rules for Claude sessions working in this repository
AGENTS.md               - the same operating rules, written for other AI coding agents
.gitignore               - excludes *.simba files from version control
docs/
  README.md             - index of the docs/ folder
  srl-t-reference-policy.md - when and how to consult SRL-T documentation
  wasplib-reference-policy.md - when and how to consult WaspLib documentation
  library-relationship.md - how SRL-T and WaspLib relate in this repository
  script-generation-workflow.md - conservative workflow for AI agents
  quality-review.md     - review notes against SRL-T and WaspLib documentation
  known-gaps.md         - current uncertainty and missing-example tracking
  script-anatomy.md      - high-level overview of Lape/WaspLib script structure
  map-walking.md         - positioning and movement (Map, Objects, TRSObjectV2, legacy TRSWalker)
  interfaces.md          - fixed UI interfaces (Inventory, Bank, Chat, GameTabs, etc.)
  camera-minimap.md      - zoom, camera rotation, visibility checks
  interact-mouse.md      - mouse interaction, uptext verification, ChooseOption
  antiban.md             - TAntiban tasks, breaks, sleeps, biometrics
  gui-config.md          - TScriptForm, GUI controls, TConfigJSON settings persistence
  ocr-color.md           - OCR and color-detection patterns
  items-bank.md          - items, inventory, and bank handling
  failsafes.md           - logging, termination, timeouts, error handling
  legacy-notes.md        - what was kept, rewritten, or archived from the previous version of this repository
  community/             - community-sourced notes (Discord, experienced script authors); leads, not verified documentation
archive/
  legacy/                - old repository content, preserved unchanged, no longer treated as current guidance
```

## How AI agents should use this repository

An AI agent working on a Lape/Simba/WaspLib task in or with this repository should:

1. Read `CLAUDE.md` (if running as Claude) or `AGENTS.md` (otherwise) before writing or modifying any script.
2. Read `docs/README.md` to find which topic file in `docs/` is relevant to the task at hand.
3. Read that topic file in full before writing code. Treat it as the primary source for syntax, types, and function behavior in that area.
4. Compare any new code against patterns already documented in `docs/`, rather than inventing a new approach to a problem `docs/` already covers.
5. When `docs/` does not cover something, say so explicitly rather than guessing. See "Uncertainty policy" below.

This repository is intended to be read by the agent, not just by a human maintainer. Sections in `CLAUDE.md`/`AGENTS.md` are written as direct operating instructions for that purpose.

## Lape documentation policy

`docs/` is the primary source of truth for this repository, specific to the project: it is built from direct inspection of installed SRL-T/WaspLib source code and real scripts, not from general training knowledge about Pascal-family languages.

Lape is its own language. It is Pascal-like, but it is not Pascal, Delphi, or Free Pascal, and it must not be documented or reasoned about as if it were. Where `docs/` does not state that a Pascal/Delphi feature exists in Lape, it should not be assumed to exist.

Documentation in `docs/` should be treated as accurate at the time it was written, not as permanently authoritative. SRL-T and WaspLib are under active development. If real code contradicts a `docs/` file, the real code wins, and the `docs/` file should be corrected.

## WaspLib reference policy

WaspLib (and the underlying SRL-T library) is large, and this repository does not document all of it. The external resources below are secondary references, to be used only when `docs/` does not already answer the question:

1. <https://github.com/torwent/wasplib> — source code, the highest-trust external source since it reflects what actually ships.
2. <https://torwent.github.io/WaspLib/> — reference documentation, which can lag behind the actual source code.

Secondary does not mean disposable: when `docs/` is silent on something, checking these sources is expected, not optional. But nothing pulled from these sources should be presented with the same confidence as something confirmed in `docs/`, and if something from these external sources conflicts with `docs/`, that conflict must be stated explicitly rather than silently resolved in either direction.

Using WaspLib as a secondary reference is not permission to invent a plausible-sounding WaspLib API. If neither `docs/` nor these sources confirm something, it is unconfirmed, full stop.

## Uncertainty policy

This repository treats documented uncertainty as more valuable than confident-sounding guesses.

- If something is not covered by `docs/` and cannot be confirmed against the WaspLib/SRL-T source, that must be stated plainly, not papered over.
- Guessed syntax must never be presented as working code.
- When uncertainty blocks an answer, the correct response is to say what is missing — a specific documentation file, a real script example, or a specific function's source — not to fill the gap with a plausible-sounding invention.

See `CLAUDE.md`/`AGENTS.md` for the exact required phrasing and workflow.

## Working with examples

This repository does not currently include runnable `.simba` example scripts. If you are extending `docs/` or asking an AI agent to solve a problem not yet covered:

- Provide a real script excerpt (a function, a record, an include chain) rather than a description of what you want the code to do. Concrete, real code is what resolves uncertainty; descriptions of intent do not.
- If documentation for some behavior is missing, the most useful contribution is a real, working example of that behavior, with enough surrounding context (includes, type declarations) to verify it actually compiles and runs in the real environment, not just a fragment.
- Do not paste hypothetical or "this is roughly how it would look" code as if it were confirmed working code. Mark it as unverified if you're not certain it runs.

## Community notes

This repository can also store informal knowledge from experienced script authors — Discord discussions, short chat snippets, and other informal community answers about Lape, Simba, SRL-T, or WaspLib.

This information is tracked separately, under `docs/community/`, and is never treated as equivalent to the verified material in the rest of `docs/`. Every community note carries an explicit confidence level (Confirmed, Likely, Unverified, Contradictory, or Deprecated) and source type, records what is known and unknown about it, and states what would be needed to confirm it. A community note must be verified — against source code, a working example, local documentation, or official WaspLib documentation — before it is used to generate code. See `docs/community/index.md` for the full policy.

## Git and file handling

`.simba` files are excluded from this repository (`.gitignore` contains `*.simba`). This is intentional: this repository documents how to write Lape scripts, it does not host them. Do not stage, commit, or otherwise add `.simba` files. If a `.simba` file is ever found staged, unstage it before committing.

When contributing:
- Keep changes scoped and explain why they are needed; avoid unrelated rewrites in the same change.
- Do not push directly to `main` unless explicitly instructed to.
- Commit messages and all repository content must be in English (see `CLAUDE.md`/`AGENTS.md`).

## Current limitations

Documented honestly rather than glossed over:

- Coverage of `docs/` is uneven. Several areas relevant to real script-writing (pure Lape language semantics independent of any library call, build/compile error diagnostics, performance characteristics) have not been separately researched.
- `docs/` was verified against one snapshot of installed SRL-T/WaspLib source and a set of real scripts examined during research; it is not continuously re-verified against upstream changes.
- This repository contains no automated tests, linting, or CI for Lape code, and currently has no mechanism to verify that documented patterns still compile against the latest SRL-T/WaspLib release.
- The previous version of this repository's premise (an LLM-calling host application for Lape scripts) is archived, not deleted, and could resurface as a separate, explicitly-scoped effort if ever revisited — it is not part of the current direction.

## Contributing

- Add documentation to `docs/` only when it is backed by a real script example or by direct inspection of SRL-T/WaspLib source. Do not add documentation for behavior you have not verified.
- If you are correcting an existing `docs/` file, state what was wrong and what evidence supports the correction, the same way `docs/README.md`'s "key cross-cutting corrections" section does.
- If you are adding a new topic file to `docs/`, add it to the index in `docs/README.md` and to the structure list in this file.
- Keep `CLAUDE.md` and `AGENTS.md` in sync when adding repository-wide rules — they describe the same operating rules for different agents and should not diverge.
- Do not commit `.simba` files (see "Git and file handling").

## License

No license file is currently present in this repository. Treat the content as all-rights-reserved by the repository owner until a license is added.
