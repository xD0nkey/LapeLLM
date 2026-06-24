# Quality review

Date of review: 2026-06-24

## Files reviewed

- [README.md](../README.md)
- [CLAUDE.md](../CLAUDE.md)
- [AGENTS.md](../AGENTS.md)
- [docs/README.md](README.md)
- [docs/community/index.md](community/index.md)
- [docs/script-anatomy.md](script-anatomy.md)
- [docs/map-walking.md](map-walking.md)
- [docs/interfaces.md](interfaces.md)
- [docs/camera-minimap.md](camera-minimap.md)
- [docs/interact-mouse.md](interact-mouse.md)
- [docs/antiban.md](antiban.md)
- [docs/gui-config.md](gui-config.md)
- [docs/ocr-color.md](ocr-color.md)
- [docs/items-bank.md](items-bank.md)
- [docs/failsafes.md](failsafes.md)
- [docs/legacy-notes.md](legacy-notes.md)
- [docs/community/minimap.md](community/minimap.md)

## SRL-T areas checked

- base interface concepts and interface-related helpers
- minimap and mapping concepts
- navigation and walker-related concepts
- inventory, banking, chat, and login-related helpers
- mouse and keyboard interaction patterns

## WaspLib areas checked

- higher-level wrappers around interfaces and base script behavior
- configuration and GUI helpers
- antiban and script structure patterns
- walker, minimap, and helper modules described by the external documentation index

## Repository documentation issues found

- The repository already described WaspLib as a secondary reference, but it did not yet give SRL-T and WaspLib equally explicit roles in the main documentation flow.
- The repository did not yet have dedicated policy files for SRL-T, WaspLib, library relationship, script generation workflow, quality review, or known gaps.
- The main instructions and README did not yet make the workflow for checking both libraries as explicit as it should be for conservative script generation.

## Corrections made

- Added policy documents for SRL-T and WaspLib reference use.
- Added a library-relationship document explaining the SRL-T/WaspLib stack and symbol-origin concerns.
- Added a script-generation workflow for AI agents.
- Added a known-gaps document for unresolved or repeatedly uncertain topics.
- Updated the main repository instructions and README to treat SRL-T and WaspLib as core references and to require explicit uncertainty handling.
- Clarified in the community notes documentation that community notes are leads, not proof.

## Remaining gaps

- Some specific symbols and helper usages still need local examples or source confirmation before they can be promoted from community notes or uncertainty lists into primary documentation.
- The repository still does not contain a full, exhaustive reference for all SRL-T and WaspLib modules.

## Recommended next documentation priorities

- Add more verified examples for interface-heavy modules and common script setup patterns.
- Add source-confirmed notes for any frequently used WaspLib helper that currently appears only in community notes or in vague form.
- Continue to update known-gaps.md as more examples arrive.

## Conflicts between repository docs and external references

No direct conflict was found in the reviewed material. The main improvement was to make the repository's policy more explicit rather than relying on an implicit assumption that WaspLib alone was the relevant external reference.

## Areas that still need user-supplied examples

- specific WaspLib helper usage patterns that are not yet covered by local examples
- any SRL-T or WaspLib symbol whose exact signature or ownership remains unclear
