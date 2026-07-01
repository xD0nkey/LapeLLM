# Docs index: Simba / SRL-T / WaspLib reference

This folder is a knowledge base for writing correct Lape code for OldSchool RuneScape bot scripts built on SRL-T + WaspLib, so the same ground has to be re-verified from scratch each time. Everything here is checked against actually installed SRL-T/WaspLib source code (typically under `%LocalAppData%\Simba\Includes\` on Windows) — not just against prose documentation — and against real WaspLib scripts examined during research (not included in this repository; see the root `README.md` for why `.simba` files are not committed).

**Read first:** [`script-anatomy.md`](script-anatomy.md) — a high-level overview of the entire script structure (file anatomy, state machine, the `TBaseScript` hierarchy, recommended workflow for new scripts). The files below go deeper on individual topics and assume that overview.

## Files in this folder

| File | Topic |
|---|---|
| [map-walking.md](map-walking.md) | Positioning & movement: `Map`/`Objects`/`TRSMapChunk`/`TRSObjectV2`/`TRSNPCV2` (modern) vs `RSW: TRSWalker`/`TMSObject` (legacy), `WalkBlind`/`WalkClick`/`Minimap.WaitFlag` |
| [map-debugging.md](map-debugging.md) | Workflow for finding/verifying a chunk box before using it: `Chunk()`, `Map.Debug()`, buffer chunks, reading a confirmed `Map.Position()` instead of guessing one |
| [interfaces.md](interfaces.md) | Fixed UI elements: `GameTabs`, `Inventory`, `Equipment`, `Bank`, `DepositBox`, `Chat`/`ChatButtons`, `Login`/`Logout`, `Magic`, `Prayer`, `ChooseOption` |
| [camera-minimap.md](camera-minimap.md) | Zoom (`MinZoom`/`MaxZoom`/`AdjustZoom`), rotation/compass angle, `MainScreen.IsVisible`, `PointToMSRect` |
| [interact-mouse.md](interact-mouse.md) | The `Mouse` module, uptext verification before clicking, `ChooseOption`, object/NPC interaction (`.Click`/`.WalkClick`/`.WalkHover`) |
| [antiban.md](antiban.md) | `TAntiban`: tasks/breaks/sleeps/biometrics, WaspLib defaults, overrides, world hopping |
| [gui-config.md](gui-config.md) | `TScriptForm`, controls, WaspLib's `Create*` building blocks, `TConfigJSON` for saved settings |
| [ocr-color.md](ocr-color.md) | OCR (`TOCRColorFilter`, `RS_FONT_*`), color detection (`CTS0/1/2`), `FindColors`/`FindDTM` |
| [items-bank.md](items-bank.md) | `TRSItem`/`TRSItemArray`, bank loadouts, withdraw retry with search field, deposit patterns |
| [failsafes.md](failsafes.md) | Logging, `TerminateScript`, timeouts (`TCountdown`/`WaitUntil`), chat-based failsafes, screenshots, Discord webhooks |
| [srl-t-reference-policy.md](srl-t-reference-policy.md) | When and how to consult SRL-T documentation while generating or reviewing scripts |
| [wasplib-reference-policy.md](wasplib-reference-policy.md) | When and how to consult WaspLib documentation while generating or reviewing scripts |
| [library-relationship.md](library-relationship.md) | How SRL-T and WaspLib relate in this repository and why symbol origin matters |
| [script-generation-workflow.md](script-generation-workflow.md) | A conservative workflow for AI agents working on Lape script tasks |
| [quality-review.md](quality-review.md) | Review notes from the repository audit against SRL-T and WaspLib documentation |
| [known-gaps.md](known-gaps.md) | Current uncertainties and missing examples that still need confirmation |
| [script-anatomy.md](script-anatomy.md) | Full overview: file anatomy, state machine, `TBaseScript` hierarchy, recommended workflow for new scripts |
| [legacy-notes.md](legacy-notes.md) | What was carried over from the previous version of this repository, and why |

## Key cross-cutting corrections and lessons from this research

- **`Map`/`Objects`/`TRSMapChunk`/`TRSObjectV2`/`TRSNPCV2` live in SRL-T, not WaspLib** (`osr/map/*.simba`). WaspLib builds on SRL-T's map system but does not define its foundation.
- **`TMSObject` is not a library type name** — it is a script-specific, hand-written record found in an older example script (referred to as "aeroguardians" in this research), not something defined in SRL-T/WaspLib. Do not confuse it with `TRSMapObject`/`TRSObjectV2`.
- **`SRL-T/osr/map/objects.simba` contains a near-identical but dead `TRSObjectV2` definition** that is never actually loaded (the include chain uses `mapobject.simba` instead). Do not trust field names cited from that file without cross-checking against `mapobject.simba`.
- **`.Bounds` is a field, not a method** on every `TRSInterface`-based type (`Chat.Bounds`, `MainScreen.Bounds`, `Minimap.Bounds`, etc.) — `.Bounds()` with parentheses is a common, real, recurring mistake. Note: some OTHER types (`TPointArray`, `TCuboid`) DO have a legitimate `.Bounds()` METHOD — distinguish the interface field from the array method.
- **WaspLib's default antiban (camera/mouse/chat/gametabs/bank tasks) is active by default**, even in scripts that add no tasks of their own (see `wasplib.json`). To disable one, e.g. the chat task, you must explicitly override the method to a no-op — otherwise it still runs in the background.
- **`TOCRColorFilter`/`TSimpleOCR` are defined in a compiled plugin** (`libsimpleocr`), not in readable Lape source — exact parameter orderings are inferred from how the library actually calls them in practice, not from a formal type declaration.
- Script age does not guarantee a modern style — several recently edited scripts examined during this research still used the older `RSW: TRSWalker` style. Always check the actual code, not the filename or date.
- **On plane > 0, `Map.Position()`/object coordinates are X-offset by `RSTranslator.MapWidth() * Plane` (13056 per plane)** relative to the plane-0-equivalent tile. Confirmed with live `Map.Position()` readings across 3 floors of Lumbridge Castle plus a cached-vs-live object coordinate comparison — see `map-walking.md` section 7. The raw cached object/NPC JSON stores the plane-0-equivalent coordinate; the live API does not.
- **There are two unrelated, identically-named `WebWalk` methods.** `TRSWalker.WebWalk` (old style) pathfinds over a static, hand-curated `TWebGraph` (edited with the `WaspLib/tools/webber.simba` tool). `TRSWalkerV2.WebWalk` (`Map.Walker.WebWalk`, new style) pathfinds over a `TWebGraphV2` auto-generated per plane from collision data every time you `Map.SetupChunk(s)` — no tool/curation needed, inspect it with `Map.Debug(ERSMapType.NORMAL, True)` instead. Neither graph connects across planes (no stairs/ladders modeled) — see `map-walking.md` section 8 pitfall 9 for the practical fix (find the real staircase object, click it explicitly, wait for the plane to change).

## How to use these files

Before writing code for a new WaspLib script: read `script-anatomy.md` for the full picture, then the specific topic file(s) above for exact syntax and pitfalls in the relevant area. If a real script appears to contradict a file here (the library is continuously updated), verify against the installed SRL-T/WaspLib source before trusting the older document, and update the file if it turns out to be outdated. See the root `CLAUDE.md`/`AGENTS.md` for the full operating rules.
