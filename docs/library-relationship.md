# Library relationship

This repository targets Lape scripts that run in the Simba ecosystem with SRL-T and WaspLib together. The two libraries are related, but they are not interchangeable.

## What SRL-T is in this repository

SRL-T is the base library layer for common script helpers, interface wrappers, map and object concepts, and low-level client interaction patterns. It provides the shared foundation that many scripts rely on.

## What WaspLib is in this repository

WaspLib is a higher-level layer built on top of SRL-T. It adds many convenience wrappers, base script patterns, configuration helpers, and task-oriented abstractions that are common in modern scripts.

## Relationship between the two

WaspLib extends SRL-T. A script may rely on both layers at once, and the repository should help AI agents understand which layer provides a symbol before they generate or modify code.

## What AI agents must not assume

- Do not assume a symbol belongs to WaspLib just because it appears in a modern script.
- Do not assume a symbol belongs to SRL-T just because it appears in a low-level helper or interface wrapper.
- Do not assume that a symbol's origin is obvious from its name alone.

## Why symbol origin matters

Symbol origin affects:

- includes and setup expectations
- which documentation to consult first
- how a script should be maintained over time
- how uncertainty should be documented when the origin is unclear

## Uncertainty handling

When the source of a symbol is unclear, the repository should document that uncertainty explicitly rather than presenting a guess as a confirmed fact.
