# SRL-T reference policy

This repository treats SRL-T as a core reference for Lape script generation in the Simba ecosystem. It is not background reading. It is part of the minimum evidence set that should be checked before an AI agent claims that a symbol, helper, interface, or script pattern is valid.

## When to check SRL-T documentation

Check SRL-T documentation when a task may involve:

- base library behavior for interfaces, movement, minimap, mouse, keyboard, or client state
- Simba-facing helpers that are part of the SRL-T layer rather than WaspLib-specific wrappers
- map, object, or walker concepts that are commonly implemented in SRL-T before WaspLib adds higher-level abstractions
- inventory, banking, chat, login, logout, magic, prayer, equipment, or other interface helpers

## What belongs in SRL-T documentation here

The repository should summarize only the parts of SRL-T that matter for script generation:

- the relevant type or helper name
- the documented role of the symbol in the library
- any documented usage constraints or caveats
- the relationship to WaspLib when the symbol is part of the shared stack

## How to reference SRL-T without copying large sections

Use brief, focused summaries rather than reproducing documentation text. A good reference note should:

- name the relevant SRL-T page or module
- summarize the behavior in one or two sentences
- state whether the symbol appears to be a base-library concept or a WaspLib wrapper
- mark any remaining uncertainty instead of turning a partial observation into a rule

## How to handle missing or unclear SRL-T details

If the relevant SRL-T documentation is missing, incomplete, or ambiguous:

- say so explicitly
- do not invent a signature, import, or runtime behavior
- ask for a working example or a source reference
- record the issue in the repository's known gaps list if it blocks reliable script generation

## Relation to Lape script generation

SRL-T documentation is often the first place to confirm whether a symbol is part of the base layer or whether a higher-level WaspLib abstraction is involved. For Lape generation, that distinction matters because it affects includes, setup, maintenance, and the likelihood that a symbol will be available in a given script context.
