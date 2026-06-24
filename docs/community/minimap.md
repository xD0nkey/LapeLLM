# Minimap Notes

Community-sourced notes about minimap behavior, minimap-related debugging, and minimap-adjacent GUI overlays. See `docs/community/index.md` for the policy governing this file, and `docs/community/intake-template.md` for the format used below.

For verified minimap reference material, see `docs/camera-minimap.md` and `docs/map-walking.md`. Nothing in this file should be treated as equivalent to those.

---

## `minimap.debugtiles`

### Raw note

A community answer suggested `minimap.debugtiles` in response to a question about overlaying GUI information on the client.

### Interpretation

This appears to refer to a minimap-related debug tile overlay or debugging helper.

### Confidence

Unverified.

### Source type

Community discussion.

### Evidence

None yet. No local example, source reference, or documentation page has been found that confirms this symbol.

### What is known

- The symbol `minimap.debugtiles` was mentioned by a community member.
- The context appears related to displaying or debugging overlays.

### What is unknown

- Whether `minimap.debugtiles` is a property, method, field, command, or configuration option.
- Required object type or namespace.
- Correct capitalization.
- Required imports or includes.
- Whether it belongs to Lape, Simba, WaspLib, or a specific project wrapper.
- Whether it is still current.

### What would confirm this

- A working script using `minimap.debugtiles`.
- A reference in WaspLib source.
- A reference in official or project documentation.
- A short explanation from an experienced contributor with usage context.

### Safe usage guidance

Do not generate code using `minimap.debugtiles` unless a confirmed example or source reference is available.

It may be mentioned as a possible lead when investigating minimap or GUI overlay behavior.

### Unsafe assumptions

Do not assume it is callable.

Do not assume it is a boolean.

Do not assume it renders GUI overlays.

Do not assume it belongs to WaspLib without confirmation.

---

## Debug overlay symbols mentioned in a community discussion

### Raw snippet

```text
1. ### Kriptic(Bundle on discount)* — *00:43
Anyone remember how to overlay grid onto rsclient?
2. we lost so much stuff on discord wipe!
3. ### Fik* — *00:55
you mean map.debugheight?
4. or minimap.debugtiles
5. ### Kriptic(Bundle on discount)* — *01:02
this one, thanks
```

### Topic

Minimap or map debug overlays.

### Mentioned symbols

* `map.debugheight`
* `minimap.debugtiles`

### Interpretation

This snippet appears to be a short community exchange about finding a debug or overlay-related setting for displaying grid or tile information on the client. The discussion suggests that `map.debugheight` and `minimap.debugtiles` were mentioned as possible names for such a feature, but it does not establish what they actually do or how they are used.

### Confidence

Unverified.

### Source type

* Community discussion

### What is known

- A community discussion mentioned `map.debugheight` and `minimap.debugtiles`.
- The discussion was about overlaying a grid or related visual debugging information on the client.

### What is unknown

- Whether these are valid symbols, settings, commands, properties, or methods.
- Their exact names, namespaces, or required context.
- Whether they belong to Lape, Simba, SRL-T, WaspLib, or a specific client wrapper.
- Whether they are still current or version-specific.
- Whether they render a visible overlay, a debug grid, or something else.

### What would confirm this

- A working script or example showing one of these symbols in use.
- A source reference in WaspLib or SRL-T source.
- An official documentation page or contributor explanation.

### Safe usage guidance

Treat this note as an investigation lead only. It may be useful for searching for related debug or overlay functionality, but it should not be turned into code or documentation without confirmation.

### Unsafe assumptions

- Do not assume `map.debugheight` or `minimap.debugtiles` are available in the current environment.
- Do not assume they are callable or configurable without proof.
- Do not assume they belong to WaspLib or any specific library without source evidence.
- Do not assume they produce a visible grid overlay just because the discussion mentions overlaying a grid.
