# WaspLib reference policy

WaspLib is a core reference for this repository because it provides many higher-level abstractions used by modern Lape scripts. It is not a free pass to invent APIs, and it does not replace SRL-T.

## When to check WaspLib documentation

Check WaspLib documentation when a task may involve:

- WaspLib wrappers or helpers around inventory, banking, walking, GUI, OCR, config, or antiban
- base script behavior such as script setup, state handling, or common runtime helpers
- WaspLib-specific abstractions that sit on top of SRL-T
- optional modules or higher-level handlers that are not part of the base SRL-T layer

## What this repository must keep in mind

- WaspLib extends SRL-T. It builds on the same scripting ecosystem rather than replacing it.
- A symbol may be available through WaspLib even though the underlying concept is rooted in SRL-T.
- A symbol should not be attributed to WaspLib unless the documentation or a confirmed local example supports that claim.
- A symbol should not be attributed to SRL-T unless the documentation or a confirmed local example supports that claim.

## How to use WaspLib documentation conservatively

- Summarize the relevant behavior rather than copying large sections of the reference.
- Treat examples as patterns to verify, not as universal rules until a local example or source reference confirms them.
- If a WaspLib example appears to depend on a symbol whose origin is unclear, document the uncertainty instead of guessing.

## How to handle missing or unclear WaspLib details

If the documentation does not answer a question clearly:

- mark the claim as unverified or likely rather than definitive
- look for a local example or source reference
- ask for a working script when the API shape or usage pattern is not confirmed

## Relation to SRL-T and Lape generation

WaspLib and SRL-T are both relevant to reliable script generation. A script may rely on both layers at once, and the repository should help agents separate them correctly rather than assuming that all symbols belong to one library or the other.
