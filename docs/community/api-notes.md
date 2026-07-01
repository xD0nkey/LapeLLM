# API Notes

Community-sourced notes about specific Lape/Simba/SRL-T/WaspLib symbols, functions, methods, properties, or constants that do not fit cleanly into `gui.md`, `minimap.md`, or `debugging.md`, and have not yet been verified well enough to belong in a primary `docs/` topic file.

See `docs/community/index.md` for the policy governing this file, and `docs/community/intake-template.md` for the entry format.

This file is a holding area, not a reference. A symbol documented here has not been confirmed. Once confirmed, move or copy the relevant information into the correct topic file under `docs/` (for example `docs/interfaces.md`, `docs/antiban.md`, `docs/items-bank.md`, `docs/ocr-color.md`) and update or remove the entry here.

---

## `ArcTan2`/`TPoint.AngleBetween` for computing a camera-facing angle to a destination point

### Raw snippet

> By the way, Pascal has trigonometry functions. I believe if you use ArcTan2 you just
> need to inform current coordinates and destination coordinates and it will give you the
> exact angle between the two points. You'd need to then convert it to SRL-T camera angle
> degrees which start North at 0 degrees and increases anti-clockwise.

### Topic

Pathfinding / camera-angle math.

### Mentioned symbols

`ArcTan2`, and (found while checking this note) `TPoint.AngleBetween`.

### Plain English interpretation

The idea: compute the angle from the player's position to a destination point using
trigonometry, then convert that into SRL-T's compass-angle convention so the camera can be
rotated to face the destination.

### Confidence

Likely.

### Source type

User provided example; WaspLib source.

### Evidence

- `ArcTan2` is genuinely used in installed SRL-T source (confirmed via grep across
  `SRL-T/utils/math/random.simba`, `SRL-T/utils/geometry/tpointarrays.simba`,
  `SRL-T/utils/geometry/trectangle.simba`, `SRL-T/utils/geometry/tpoint.simba`,
  `SRL-T/osr/interfaces/minimap.simba`) — it is a real, available function, not invented.
- `SRL-T/utils/geometry/tpoint.simba` already has a ready-made wrapper that does exactly
  what the snippet describes:
  ```pascal
  function TPoint.AngleBetween(other: TPoint): Double; constref;
  begin
    Result := SRL.Modulo(Degrees(ArcTan2(other.Y - self.Y, other.X - self.X)) - 90, 360);
  end;
  ```

### What is known

- `ArcTan2` exists and is used elsewhere in SRL-T.
- `TPoint.AngleBetween(other)` exists, returns a `Double`, and its body matches the
  general shape the snippet describes (angle between two points, with a `-90` offset and
  `Modulo 360` normalization — consistent with converting a standard math angle into a
  compass-style bearing).

### What is unknown

- Whether `TPoint.AngleBetween`'s output, used as-is, already matches SRL-T's own compass
  convention (North = 0, increasing anti-clockwise) closely enough to pass directly into
  something like `Minimap.SetCompassAngle` — this has not been cross-checked against a
  real script that actually does that, only read in isolation.
- Whether `AngleBetween` is the function actually intended for this (vs. computing it by
  hand with raw `ArcTan2`, as the snippet suggests) — both are real options found in
  source, not distinguished further here.

### What would confirm this

A real script (or a small test) that calls `TPoint.AngleBetween` (or raw `ArcTan2`) and
feeds the result into `Minimap.SetCompassAngle`/`Minimap.GetCompassAngle` and confirms the
camera actually faces the intended destination.

### Safe usage guidance

Safe to mention `ArcTan2`/`TPoint.AngleBetween` as real, existing functions for this kind
of angle math (their existence is confirmed). Not yet safe to assert that
`TPoint.AngleBetween`'s output can be used as a drop-in compass angle without checking it
against a real camera-rotation call first.

### Unsafe assumptions

- Do not assume the `-90`/`Modulo 360` adjustment inside `AngleBetween` was specifically
  designed to match SRL-T's compass convention — it matches the *shape* of what's needed,
  but that hasn't been independently confirmed against `Minimap`'s actual angle convention.

---

## `TRSObjectV2` and `TRSNPCV2`: `TrackTarget`, `SetupEx` parameter forms, `Filter` array assignment, and standalone usage pattern

### Raw snippets

ObjectV2 example:

```pascal
{$I WaspLib/osr.simba}
var
  obj: TRSObjectV2;
begin
  RSClient.RemoteInput.EnableRealInput;
  Map.SetupChunk(ERSChunk.VARROCK);
  Options.SetZoomLevel(30);
  //Objects.Setup(Map.Objects, @Map.Walker);
  obj.SetupEx([1.5, 1.5, 7], [[8794, 36744]]);
  obj.SetupUpText('Tree');
  obj.finder.Colors += [CTS2(1065022, 9, 0.12, 5.10)];
  obj.Walker := @Map.Walker;
  obj.TrackTarget := True;
  repeat
    debug(obj);
    //obj.WalkClick();
    sleep(100);
  until false;
end.
```

NPCV2 example:

```pascal
{$DEFINE SRL_USE_REMOTEINPUT}
{$I SRL-T/osr.simba}

var
  Wizard: TRSNPCV2;

begin
  Map.SetupChunk(Chunk([48,49,48,49], 0));
  Wizard.Walker := @Map.Walker;
  Wizard.SetupEx([100], [1,1,7], [[8352,37746]]);
  Wizard.TrackTarget := True;
  Wizard.Finder.Colors += CTS2(9264409, 21, 0.09, 1.47);
  Wizard.SetupUpText('Wizard');
  Wizard.Filter := [True, True, True, True];
  repeat
    Debug(Wizard);
    wait(100);
  until false;
end.
```

Source: Discord community discussion, shared as a demonstration of minimal standalone object/NPC detection.

### Topic

Map objects / NPCs — `TRSObjectV2`/`TRSNPCV2` configuration, standalone detection loop, and debug overlay.

### Mentioned symbols

`TRSObjectV2`, `TRSNPCV2`, `TRSObjectV2.SetupEx`, `TRSNPCV2.SetupEx`, `TRSMapObject.TrackTarget`,
`TRSMapObject.SetupUpText`, `TRSMapObject.Finder`, `TRSObjectFinder.Colors`, `TRSMapObject.Filter`,
`TRSMapObject.Walker`, `Map.SetupChunk`, `ERSChunk`, `Chunk`, `debug`, `Debug`,
`RSClient.RemoteInput.EnableRealInput`, `Options.SetZoomLevel`, `CTS2`.

### Plain English interpretation

The snippets demonstrate a minimal, self-contained loop for developing object/NPC detection without wrapping a full script. Key patterns not already shown in `docs/map-walking.md`:

1. **`TrackTarget := True`** — a field on `TRSMapObject` (parent of both `TRSObjectV2` and `TRSNPCV2`). Both examples set it. Its exact effect is not stated in the snippet and is not currently documented anywhere in `docs/`.

2. **`TRSObjectV2.SetupEx` with Vector3 size** — the snippet calls `obj.SetupEx([1.5, 1.5, 7], [[8794, 36744]])`, showing the first parameter is a three-element array (presumably X size, Y size, height in tiles) rather than a single scalar. `docs/map-walking.md` section 3 mentions `SetupEx(size: Vector3; coordinates: TPointArray)` but gives no concrete example with actual values.

3. **`TRSNPCV2.SetupEx` with radius array and Vector3 size** — the NPC snippet calls `Wizard.SetupEx([100], [1,1,7], [[8352,37746]])`, showing a three-parameter form: radius array, Vector3 size, coordinates. `docs/map-walking.md` only shows the scalar `TRSNPCV2.Setup(10, 1, 6, [[...]])` form; this array-radius variant is not currently documented.

4. **`Filter := [True, True, True, True]`** — assigns all four filter booleans (Walker, Minimap, Finder, UpText) at once using an array literal, rather than setting each field individually. The `docs/` only shows per-field assignment (`Filter.Finder := False`).

5. **Standalone pattern without `Objects.Setup`** — both examples skip the `Objects.Setup(Map.Objects(), @Map.Walker)` call entirely. Instead they set `obj.Walker := @Map.Walker` directly. This works for ad-hoc single-object detection without needing the global JSON parser. The ObjectV2 snippet has `Objects.Setup` commented out, suggesting this is intentional.

6. **`Colors += CTS2(...)` without brackets** — the NPC snippet uses `Wizard.Finder.Colors += CTS2(...)` with no surrounding `[]`, while the ObjectV2 snippet uses `obj.finder.Colors += [CTS2(...)]` with brackets. Both are from the same source. Unclear if both forms are accepted or if one is a typo.

7. **`Map.Objects` without `()`** in the ObjectV2 snippet's commented-out line: `//Objects.Setup(Map.Objects, @Map.Walker)`. The primary docs and all other examples use `Map.Objects()` with parentheses. This single appearance without parentheses may be a typo in the snippet, or it may indicate `Objects` is a property rather than a method call. Do not treat it as a confirmed alternative form without source verification.

8. **`debug(obj)` / `Debug(Wizard)`** — calling the built-in `debug` procedure on a `TRSObjectV2` or `TRSNPCV2` draws a debug overlay. Referenced in `docs/community/debugging.md` (check that file for more detail), but not currently shown in `docs/map-walking.md` in this context.

### Confidence

**Likely** — the snippets are complete, named examples that appear to compile and run. The symbols that are already confirmed in `docs/` are consistent with their documented usage. The unknown items (`TrackTarget`, the exact `SetupEx` signatures, `Filter` array literal syntax) are plausible but have not been independently verified against the SRL-T source.

### Source type

Community discussion; User provided example.

### Evidence

Both snippets shared directly as working code examples showing how to approach object/NPC detection in Simba. No independent source verification has been performed against the installed SRL-T or WaspLib source for the items marked unknown below.

### What is known

- `TRSObjectV2.SetupEx` exists and is mentioned (without a concrete example) in `docs/map-walking.md` section 3.
- `TRSNPCV2.Setup(radius, size, height, coordinates)` (scalar form) is documented in `docs/map-walking.md` section 3.
- `obj.SetupUpText(...)`, `obj.Finder.Colors +=`, and `obj.Walker := @Map.Walker` are all documented in `docs/map-walking.md` section 3.
- `Filter` fields (Walker, Minimap, Finder, UpText) are documented in `docs/map-walking.md` section 3.
- `Map.SetupChunk(ERSChunk.*)` and `Map.SetupChunk(Chunk([...], plane))` are both documented in `docs/map-walking.md` section 2 and `docs/map-debugging.md`.
- The standalone pattern (skip global `Objects.Setup`, set `obj.Walker` directly) is a valid approach for ad-hoc use — this is consistent with how `Walker` is described as a required pointer, not tied to the global parser.

### What is unknown

- **`TrackTarget`**: what it does. Does it cause the object/NPC to be continuously tracked across frames (e.g. for moving NPCs)? Is it required for `TRSNPCV2` but optional for `TRSObjectV2`? Does leaving it `False` (the default) silently break NPC detection in a loop? None of this is stated or verifiable from the snippet alone.
- **`TRSObjectV2.SetupEx` exact signature**: is the first parameter truly a `Vector3` (`[x, y, z]` = X size, Y size, height)? Is there a variant with a separate scalar radius like the NPC form? What do the fractional values `1.5` actually represent (tiles? pixels?)?
- **`TRSNPCV2.SetupEx` exact signature**: is the first parameter a `TIntegerArray` for multiple radius values (and if so, what does multiple radii mean)? Is the `[100]` a proximity radius in pixels, tiles, or something else?
- **`Filter := [True, True, True, True]`**: whether Lape supports assigning a record from an array literal in this way, and whether the field order is guaranteed to match (Walker, Minimap, Finder, UpText in that order). This could be a Lape-specific feature; do not assume it works without verification.
- **`Colors += CTS2(...)` without `[]`**: whether the type of `Finder.Colors` allows direct `+= T` (single element) as well as `+= [T]` (array literal), or whether one of the two forms in these snippets is a typo.
- **`Map.Objects` without `()`**: whether this is a valid property access or a typo.

### What would confirm this

- Read `SRL-T/osr/map/mapobject.simba` and grep for `TrackTarget` to find its declaration and any comment explaining its purpose.
- Read `SRL-T/osr/map/mapobject.simba` for the exact signatures of `TRSObjectV2.SetupEx` and `TRSNPCV2.SetupEx`.
- Search SRL-T source for the `Filter` record field ordering to confirm the array assignment order.
- Grep `Finder.Colors` assignments in working scripts to confirm whether both `+= CTS2(...)` and `+= [CTS2(...)]` forms appear in source.
- A confirmed real script that sets `TrackTarget := True` and works correctly end-to-end.

### Safe usage guidance

- Safe to use `obj.SetupEx([x, y, z], [[wx, wy]])` as the ObjectV2 form — it matches the documented pattern shape, and the example shows a specific working call.
- Safe to use `Wizard.SetupEx([radius], [x, y, z], [[wx, wy]])` as the NPCV2 form — treat the radius as a single-element array for now; do not invent multi-radius behavior.
- **Do not use `TrackTarget` in generated code without first verifying its declaration in `SRL-T/osr/map/mapobject.simba`.** Its presence in both examples is a strong signal it is a real field, but its default value and effect are unknown — omitting it or setting it incorrectly could change detection behavior silently.
- **Do not use `Filter := [True, True, True, True]`** in generated code without verifying Lape supports this record-from-array assignment syntax. Use per-field assignment (`Filter.Walker := True` etc.) instead, which is already confirmed in `docs/`.
- For `Colors +=`: use the `[CTS2(...)]` bracket form (already confirmed in `docs/map-walking.md` section 3). Do not use the no-bracket form until it is confirmed.

### Unsafe assumptions

- Do not assume `TrackTarget` is required for detection to work, or that it is safe to always set to `True`, without reading its definition.
- Do not assume the `SetupEx` parameter names or types match Pascal/Delphi conventions for `Vector3` — verify against Lape/SRL-T source.
- Do not assume the `Filter` record fields are always in Walker/Minimap/Finder/UpText order in an array literal — the order could differ between SRL-T versions.
- Do not assume `Map.Objects` (no parentheses) is equivalent to `Map.Objects()` — treat it as an unconfirmed variant until source inspection confirms it.
