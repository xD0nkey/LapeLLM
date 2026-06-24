# Legacy notes: what came from the old version of this repository

This file documents what was carried over, rewritten, or archived when this repository was rebuilt as an AI instruction and documentation layer for Lape scripting. It exists so the reasoning behind the rebuild is not lost, and so old material is not silently discarded.

The original files are preserved unchanged in [`../archive/legacy/`](../archive/legacy/). This file explains what they were, why they were moved, and what (if anything) from them is still relevant.

## What the old repository actually was

The previous version of this repository described a hypothetical "LapeLLM" host application: a Free Pascal/Delphi program that would expose a `Host.GetLLMInterface()` API to Lape scripts, letting a `.lape` script call out to an LLM provider (OpenAI, Anthropic, etc.) through types like `TLLMInterface` with methods such as `Generate`, `GenerateStream`, `SetModel`, `SetTemperature`.

This API was never implemented anywhere in the repository. The old `USAGE.md` said so explicitly: "Note: This API is hypothetical. Refer to the actual LapeLLM source/documentation for the real API." No such source existed in the repository. The old `README.md` contained literal placeholder brackets (e.g. `[e.g., 3.2.2]`, `[Free Pascal / Delphi]`) that were never filled in.

This is a different premise from the current goal of this repository. The old idea was "let a Lape script call an LLM." The current goal is "help an LLM (Claude or another AI coding agent) write correct Lape/Simba/WaspLib scripts." These are not the same project, and the old Host API must not be presented as if it exists, is planned, or is part of the current direction.

## Files moved to `archive/legacy/`

### `archive/legacy/USAGE.md` (formerly `USAGE.md`)

Describes the hypothetical Host API in more detail, including a "conceptual" scripting API reference, streaming example, and a troubleshooting section. Archived because it documents an API that does not exist in this repository and would mislead an AI agent into assuming it can call `Host.GetLLMInterface()` or similar functions in a real script.

### `archive/legacy/LLM-prompt.ts` (formerly `Simba/LLM-prompt.ts`)

Despite the `.ts` extension, this file is plain text: a prompt intended to prime an LLM with knowledge of the Simba scripting language. The content describes the **SRL-6 / SMART-client era** of Simba scripting (`{$DEFINE SMART}`, `{$i srl-6/srl.simba}`, functions like `FindColorTolerance(x, y, color, x1, y1, x2, y2, tolerance)`, `IntToBox`, `BitmapFromString`). This era predates the current SRL-T/WaspLib stack that this repository's `docs/` folder documents, and several of its concrete API examples do not match current SRL-T/WaspLib usage (current code uses `Mouse.Move`/`Mouse.Click`, `SRL.FindColors`, `TBox` literal syntax, etc., not the SRL-6-style calls shown in this file).

Useful idea worth keeping: priming an AI with a structured tutorial of language syntax and concepts before asking it to write code is a reasonable approach in principle. The specific content is outdated and must not be treated as a current reference. The `docs/` folder in this repository is the up-to-date replacement for this idea, verified against currently installed SRL-T/WaspLib source rather than against a 2014–2017-era tutorial.

### `archive/legacy/specification-prompt.ts` (formerly `lib/specification/specification-prompt.ts`)

Real TypeScript, but non-functional in this repository: it imports modules (`@/lib/constants/buildware-config`, `../../estimate-claude-tokens`, `../../limit-codebase-tokens`) that do not exist anywhere in this repository. It appears to be adapted, by find-and-replace, from an unrelated generic AI-coding-pipeline template, with Lape/Simba terminology substituted in. There is no build setup, no package manifest, and no surrounding pipeline code that would make this file run.

Useful idea worth keeping: the embedded prompt asks an LLM to produce a high-level **specification** (a numbered list of implementation steps) before writing actual code, explicitly excluding low-level code snippets from that specification step. This matches the "plan before code" approach already reflected in this repository's `docs/script-anatomy.md` (read the state-machine shape and existing patterns before writing a new state). The specific prompt text, however, references the legacy `RSWalker`/`RSW.GetMyPos()` positioning style, which `docs/map-walking.md` documents as outdated in favor of the modern `Map`/`Objects`/`TRSObjectV2` API. If this specification-first workflow idea is revisited, it should be rewritten against the current API documented in `docs/`, not copied from this file.

### `CONTRIBUTING.md` — removed, not archived

The old `CONTRIBUTING.md` was a generic Free Pascal/Delphi contribution guide (build instructions, IDE setup, a Pull Request checklist) with unfilled placeholder text (e.g. "[Describe the project's testing strategy...]"). It did not describe anything specific to this repository, which contains no buildable Pascal/Delphi project. It was deleted rather than archived because it carried no project-specific information worth preserving.

## What was kept and built on

- The general premise that an LLM needs structured, verified reference material to write Lape/Simba code reliably — this is the basis for the current `docs/` folder.
- The "specification/plan before code" workflow idea from `specification-prompt.ts` — reflected in the workflow guidance in the root `CLAUDE.md`/`AGENTS.md` and in `docs/script-anatomy.md`.
- The repository name and its general framing as a Lape-focused AI assistance project.

## What is still missing

This repository does not yet contain:
- Verified Lape language-level reference material (operator behavior, type coercion rules, record semantics, generics if any) distinct from SRL-T/WaspLib library usage. The `docs/` files focus on SRL-T/WaspLib API usage patterns; pure Lape language semantics not tied to a specific library call have not been separately audited.
- Any real `.simba` script examples committed to the repository (by design — see the root `README.md` for the exclusion policy). Anyone extending this repository will need to supply real script examples or point to specific WaspLib source files when documentation gaps are found.
- A formally reviewed WaspLib version/compatibility statement — the WaspLib and SRL-T projects evolve continuously, and the `docs/` files reflect a snapshot verified at the time they were written, not a guarantee of current behavior.
