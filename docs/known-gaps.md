# Known gaps

This file records repeated uncertainties that still block reliable script generation. The entries here are intentionally conservative and should be updated when the missing information is confirmed.

## Current gaps

- Some community-sourced symbols or shorthand names remain unconfirmed because no local example or reference source has been found.
- A few WaspLib helper modules may require working examples before they can be documented as reusable patterns.
- Some optional or version-specific helpers are not yet covered by a verified local example.
- Exact signatures for some plugin-backed or library-provided helpers remain unclear without a source reference.
- Quest-locked locations (e.g. the Lumbridge basement bank chest unlocked by Recipe for Disaster) are often missing entirely from BOTH SRL-T's modern per-chunk object/NPC cache AND WaspLib's legacy RSObjects/RSRegions catalog - presumably because whatever process built those caches never had that content unlocked. Don't assume "not found in either cache" means "wrong search" - it may mean the location genuinely isn't catalogued anywhere, and the only way to get a working coordinate is `Map.Position()` against a real, logged-in account that has it unlocked (see `map-debugging.md`).

## What would resolve these gaps

- a working script excerpt
- a source reference in SRL-T or WaspLib documentation
- a contributor explanation tied to an actual example

## Guidance

Do not treat these items as confirmed documentation. Treat them as investigation targets until evidence is available.
