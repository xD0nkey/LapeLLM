# Positioning and movement (Map, Objects, Walker)

This file is a self-instruction for how to write correct walking/mapping code
in Simba scripts built on SRL-T + WaspLib. Sources: roughly 20 WaspLib scripts and two generations
of an example GotR script (called "aeroguardians" in the research, old vs. new style) as well as a large
combat script ("gemstone crab slayer") that was examined during the research but is not included in
this repo (see the `.simba` policy in the root `README.md`), and — most importantly — the actual source code in
`%LocalAppData%\Simba\Includes\SRL-T` and `...\WaspLib` (verified by grepping
function signatures directly, not just reading script examples).

See also `script-anatomy.md` for a high-level overview of the entire
script architecture (state machines, TBaseScript, antiban, GUI). That file is not repeated here —
this document goes deeper specifically on positioning/movement.

**Important correction to the task description:** `Map`, `TRSMapChunk`, `Objects`, `TRSObjectV2`,
`TRSNPCV2`, and `TRSWalkerV2` live in **SRL-T** (`SRL-T/osr/map/*.simba` and `SRL-T/osr/walker.simba`),
NOT in WaspLib. WaspLib only adds extra layers on top (e.g. `WL` helpers, `TBaseWalkerScript`,
POH-specific stuff). Both `{$I SRL-T/osr.simba}` and `{$I WaspLib/osr.simba}` are usually included in
scripts, so in practice you usually have access to everything anyway — but if I only want walking/mapping,
SRL-T alone is enough.

---

## 1. Old style vs. new style — which one should I use?

There are **two completely separate, parallel systems** in the installed codebase. Both work and
load, but they are incompatible with each other (different coordinate systems, different types).

### 1a. Old style: `RSW: TRSWalker` + local/image coordinates

File: `SRL-T/osr/walker/walker.simba` (the type `TRSWalker`, often as a field `RSW` in the script's record).
Positioning relies on loading a PNG image of the map (`RSW.Setup('world')` or
`RSW.SetupRegions(...)`), comparing the minimap against that image, and coordinates are **pixel positions in the
loaded image** — not real RuneScape coordinates. If you load a different map, the same
player position gets a different number.

Example from `students_ore_buyer.simba` (typical for the whole `students_*` family and `aerofisher`,
`gem_miner`, `aeroguardians (4).simba`):

```pascal
type
  TScript = record
    RSW: TRSWalker;
    ShopTile, BankTile: TPoint;
  end;

procedure TScript.Setup();
begin
  Self.RSW.ScreenWalk := True;
  Self.RSW.SetupRegions([[10308, 1406, 10559, 1642]]);
end;

function TScript.WalkToShop(): Boolean;
begin
  if not Self.RSW.AtTile(Self.ShopTile, 15) then
    Result := Self.RSW.WalkBlind(Self.ShopTile);
end;
```

Objects are found here either with the even older `TMSObject` type (`Tile`/`WalkTile`/`Colors`/`UpText` +
manual hover/click logic) or with WaspLib's older `TRSObject`/`TRSWalkerObjects`
(`WaspLib/osr/walker/objects/walkerobjects.simba`) — yet another separate system, with its own
`PRSWalkerObject` pointer.

### 1b. New style: `Map` / `Objects` / `TRSMapChunk` / `TRSObjectV2`

File: `SRL-T/osr/map/map.simba` + `SRL-T/osr/walker.simba` (the type `TRSWalkerV2`, global singleton
`Map: TRSMap`). No local image map — `Map` is read from real **world coordinates** (the four-/
five-digit RuneScape coordinates, e.g. `[3664, 30578]` or `[7220, 31038]`). Map data is loaded in
"chunks" (rectangles in chunk coordinates, 1 chunk = 64x64 tiles) which are fetched/cached automatically —
you never have to keep track of a PNG file yourself.

Example from `wasp_blast_furnace.simba`:

```pascal
procedure TBlastFurnace.Init(maxActions: UInt32; maxTime: UInt64); override;
begin
  inherited;
  Map.SetupChunk(ERSChunk.BLAST_FURNACE);
  Objects.Setup(Map.Objects(), @Map.Walker);

  Self.BarDispenser := TRSObjectV2.Setup(7, [[3664, 30578]]);
  Self.BarDispenser.Walker := @Map.Walker;
end;
```

**Conclusion: in NEW scripts you should always use `Map`/`Objects`/`NPCs`/`TRSObjectV2`/`TRSNPCV2`,
never your own `RSW: TRSWalker` instance or `TMSObject`.** The new style gives you real
world coordinates (shared by all WaspLib functions, transport systems, bank locations, etc.),
built-in path-finding (webgraph), collision data, and a height map for free.

### Flagging: which of the 20 scripts are outdated on this point?

Grepping for `: TRSWalker;` (field declaration, old style) gave hits in:
`aerofisher (2).simba`, `gem_miner (1).simba`, `students_fossil_island_chopper (4).simba`,
`students_mhomes_+farm_bhruns.simba`, `students_only_farm_and_bhruns.simba`, `students_ore_buyer.simba`,
`studentscollector_+_farm&bhruns.simba`, `studentsorebuyer (1).simba` — **all of these use the
outdated `RSW` pattern**, despite several having edit dates in 2025. If I'm asked to maintain
or extend any of these, I should be aware that they don't use `Map`/`Objects`, but I
don't need to automatically migrate them — just not mix in the `Map` API in a file built on `RSW`.

`bigaussie_gemstone_crab_slayer.simba` is a special case: it has **both** `Map.SetupChunkEx(...)`
+ `TRSObjectV2`/`TRSNPCV2` (new style, used for the most part) **and** a leftover field
`RSWWalker: TRSWalker` that appears to be unused cruft/legacy from an earlier version. If I work in that
file: trust `Map`/`Objects`, ignore `RSWWalker` if it isn't actively used anywhere.

Scripts that correctly use the new style throughout: `wasp_blast_furnace.simba`,
`wasp_jewelry_smelter.simba`, `wasp_wintertodt.simba`, `wasp_ardougne_knights.simba`,
`wasp_enchanter.simba`, `wasp_herblore.simba`, `wasp_tab_maker.simba`, as well as `aeroguardians.simba` rev 38.

---

## 2. How to set up a map

`Map` is a global singleton (`var Map: TRSMap;` in `map.simba`) — it already exists, you should not
declare your own. Setup is done once, usually in the script's `Init` override (if you inherit
`TBaseScript`/`TBaseWalkerScript`) or in your own `Setup` procedure.

### The recommended method: predefined chunks

```pascal
Map.SetupChunk(ERSChunk.BLAST_FURNACE);
```

`ERSChunk` (in `SRL-T/osr/map/rschunk.simba`) is an enum with common locations already measured
(`AL_KHARID`, `ARDOUGNE`, `VARROCK`, `LUMBRIDGE`, `FOSSIL_ISLAND`, `WINTERTODT`, ... ). Each
`ERSChunk.Get()` returns a `TRSMapChunk` (`record Chunk: TBox; Planes: TIntegerArray; end`) with
chunk coordinates and which plane(s)/floor(s) (0–3) should be loaded, e.g.:

```pascal
ERSChunk.LUMBRIDGE: Result := Chunk(Box(49,51,50,49), [0,1,2]);  // 3 planes (basement, ground level, upper floor)
```

### Custom chunk coordinates (location not present in `ERSChunk`)

```pascal
Map.SetupChunkEx([18, 49, 27, 47], [0, 1, 2]);   // Box in CHUNK coordinates, not world coordinates!
Map.SetupChunksEx([box1, box2], [0, 1]);          // multiple boxes at once
```

Seen in `bigaussie_gemstone_crab_slayer.simba`:

```pascal
Map.SetupChunkEx([18, 49, 27, 47], [0, 1, 2]);
Objects.Setup(Map.Objects(), @Map.Walker);
```

### Right after `Map.Setup*`: hook in `Objects`/`NPCs`

```pascal
Objects.Setup(Map.Objects(), @Map.Walker);
NPCs.Setup(Map.NPCs(), @Map.Walker);   // only if you need NPC lookup by name
```

`Map.Objects()`/`Map.NPCs()` return a `TJSONArray` with all the object/NPC data the map loader has fetched
for the chunks you've set up. `Objects`/`NPCs` are global `TRSObjectJSONParser`/`TRSNPCJSONParser`
singletons (declared in `SRL-T/osr/map/mapobjectarray.simba`) that you query by name/ID instead of
looking up coordinates and colors yourself.

**Don't forget `Objects.Setup(...)` — without it, `Objects.Get(...)`/`Objects.GetAll(...)` crashes with
"doesn't exist on the loaded maps", even though the map itself loaded fine.** See section 8.

### Extra: loading more map data afterward

If you already have a `Map.Setup...` and need to add more area without reloading everything:
`Map.AddChunk(...)`, `Map.AddChunkEx(...)`, etc. Avoid this if you can set up everything in a single
`SetupChunk(s)` call from the start — the `Add` variants are slower because they repeat expensive steps.

---

## 3. Objects: `TRSObjectV2` vs. the older `TMSObject`

### Modern: `TRSObjectV2`

The type (in `SRL-T/osr/map/mapobject.simba`) has, among others, the fields:

```pascal
TRSObjectV2 = record(TRSMapObject)
  ObjType: Int32;
  Rotations: TSingleArray;
end;

TRSMapObject = record
  ID: Int32;
  Name: String;
  Category: Int32;
  UpText, Actions: TStringArray;
  Size: Vector3;
  Coordinates: TPointArray;     // WORLD coordinates
  Finder: TRSObjectFinder;      // CTS2 colors for image recognition
  Offset: Vector3;
  Walker: PRSWalkerV2;          // MUST be pointed at @Map.Walker, otherwise nil crash
  Filter: record
    Walker, Minimap, Finder, UpText: Boolean;
  end;
end;
```

**Two ways to get a `TRSObjectV2`:**

1. **Look it up from the map's JSON data** (recommended if the object is already recognized by the
   map data, e.g. bank booths, trees, ore rocks that are already cataloged):

   ```pascal
   Self.MeltingPot := Objects.Get('Melting Pot');
   Self.BankChest  := Objects.Get('Bank chest');
   Self.ConveyorBelt := Objects.Get('9100');  // can also look up by ID as a string
   ```

   `Objects.Get(name)` searches the JSON that `Map.Objects()` exposes and builds a ready-made
   `TRSObjectV2` with the correct `Coordinates`, `Finder.Colors`, `Size`, `Walker` pointer, etc. automatically.

2. **Define it manually** (when the object is not present in the map data, or you simply want to point
   to an exact world coordinate yourself):

   ```pascal
   Self.BarDispenser := TRSObjectV2.Setup(7, [[3664, 30578]]);   // Setup(height, coordinates)
   Self.BarDispenser.SetupUpText('Bar dispenser');
   Self.BarDispenser.Finder.Colors += CTS2(7434872, 9, 0.28, 0.10);
   Self.BarDispenser.Walker := @Map.Walker;                      // DON'T FORGET THIS
   ```

   Or with an explicit size: `TRSObjectV2.Setup(size, height, coordinates)`, or
   `SetupEx(size: Vector3; coordinates: TPointArray)` for non-square objects with rotation.

   The NPC equivalent: `TRSNPCV2.Setup(radius, size, height, coordinates)`, seen in
   `wasp_tab_maker.simba`:

   ```pascal
   Self.Phials := TRSNPCV2.Setup(10, 1, 6, [[7704, 37582]]);
   ```

### Fetching many objects at once: `Objects.GetAll`

```pascal
function TRSObjectJSONParser.GetAll(name: String): TRSObjectV2Array;
function TRSObjectJSONParser.GetAll(names: TStringArray): TRSObjectV2Array; overload;
function TRSObjectJSONParser.GetAllByAction(action: String): TRSObjectV2Array;
function TRSObjectJSONParser.GetNearest(names: TStringArray; point: TPoint; ...): TRSObjectV2;
```

Use `Objects.GetAll('Rocks')` when several physical objects share a name (e.g. multiple ore rocks) and you
want all the coordinates collected in a `TRSObjectV2Array`, or `Objects.GetNearest(...)` when you only
want the closest instance relative to a given point.

### The filter flags control HOW the search is performed

```pascal
Filter: record
  Walker:  Boolean;  // search via world coordinates + Map.Walker (recommended, robust)
  Minimap: Boolean;  // (for TRSNPCV2/TRSMMDotV2) filter minimap dots
  Finder:  Boolean;  // color-based search over the whole mainscreen without coordinates
  UpText:  Boolean;  // verify uptext before a click counts as successful
end;
```

The default after `Objects.Get`/`TRSObjectV2.Setup` is all `True`. If you set `Self.X.Filter.Finder :=
False` (seen in `mapobjectarray.simba`'s bank handling), you force the search to rely solely on
`Coordinates` + `Walker`, which is faster and more predictable if you already know exactly where the object
is.

### Older: `TMSObject` (dead API, avoid in new scripts)

```pascal
TMSObject = record
  Name: String;
  Colors: Array of TCTS2Color;
  UpText: TStringArray;
  Tile, WalkTile: TPoint;   // LOCAL coordinates relative to a self-built RSW map
end;
```

No hits for `TMSObject` in the 20 scripts in `Ny mapp` (good — suggests that variant is already
extinct in the current collection), but it is mentioned in the task's source material (the
`aeroguardians (4).simba` style) and shows up in older tutorials. If I encounter it: it's the same "device"
that `TRSObjectV2` fills today, just with local pixel coordinates and without built-in path-finding/hover
verification. Mentally migrate to `TRSObjectV2` + `Map` if I'm asked to build further on such code.

---

## 4. NPCs: `TRSNPCV2`

Same basic pattern as objects, but `TRSNPCV2` adds `DotType`/`DotFilters` to filter
minimap dots (since NPCs move, unlike objects):

```pascal
TRSNPCV2 = record(TRSMapObject)
  Level: Int32;
  DotType: ERSMinimapDot;
  DotFilters: TRSDotFilterArray;
end;
```

Practical example from `bigaussie_gemstone_crab_slayer.simba`:

```pascal
var
  GemStoneCrabNorth: TRSNPCV2;
begin
  GemStoneCrabNorth := NPCs.Get('Gemstone crab');     // or manually via TRSNPCV2.Setup
  GemStoneCrabNorth.DotType := ERSMinimapDot.NPC;
  GemStoneCrabNorth.AddFilter(SomePolygon, True);      // restrict the search to an area
end;
```

`NPCs` is the global parser (analogous to `Objects`): `NPCs.Get(name)`, `NPCs.GetAll(name)`,
`NPCs.GetNearest(name, point)`, `NPCs.GetAllByAction(action)`. Just as with objects, `NPCs.Setup(Map.NPCs(),
@Map.Walker)` MUST be run before you can look up NPCs by name.

`ERSMinimapDot` is the same enum that drives `Minimap.GetDots(dotType)` (`PLAYER`, `NPC`, `ITEM`, etc.) —
if an NPC for some reason doesn't show dots on the minimap (rare, but happens for certain
invisible/cleaned-up NPC types), set `Filter.Minimap := False` so the search instead relies
entirely on `Walker` (world coordinates) or `Finder` (color search).

---

## 5. Movement functions: `WalkBlind`, `WalkClick`, `WalkHover`, `Click`

These exist at two levels: directly on `Map.Walker` (a `TRSWalkerV2`) for "go to a coordinate," and
on `TRSObjectV2`/`TRSNPCV2` instances for "go to and interact with this object/NPC."

### `Map.Walker.WalkBlind(destination, waitUntilDistance)`

```pascal
function TRSWalkerV2.WalkBlind(Destination: TPoint; WaitUntilDistance: Int32 = 0): Boolean;
```

Draws a straight line from the player's position to `Destination` (a world coordinate) and walks it, without
path-finding/webgraph. Use it when you already know the path is clear (open rooms, short distances within a
chunk) — e.g. `aeroguardians.simba`: `Map.Walker.WalkBlind([10372, 12478]);`. `WaitUntilDistance`
acts as a radius: `0` waits until you are exactly at the destination, `20` returns as soon as you're within
20 pixels.

### `Map.Walker.WebWalk(destination, ...)` / `WebWalkEx`

The path-finding variant — uses the built-in webgraph data (nodes, doors, collisions) to walk
around obstacles. Prefer it over `WalkBlind` for longer/complex distances, especially if the map has
doors or walls in the way. `TRSMapObject.WalkHover`/`WalkClick` already use `WebWalk` internally
(see the next paragraph), so you rarely need to call it manually if you're working against objects/NPCs.

### `obj.Hover` / `obj.WalkHover` / `obj.Click` / `obj.WalkClick` (on `TRSObjectV2`/`TRSNPCV2`)

```pascal
function TRSMapObject.Hover(attempts: Int32 = 2): Boolean;
function TRSMapObject.WalkHover(attempts: Int32 = 2): Boolean;
function TRSMapObject.Click(leftClick: Boolean = True; attempts: Int32 = 2): Boolean;
function TRSMapObject.WalkClick(leftClick: Boolean = True; attempts: Int32 = 2): Boolean;
function TRSMapObject.SelectOption(action: TStringArray; attempts: Int32 = 2): Boolean;
function TRSMapObject.WalkSelectOption(action: TStringArray; attempts: Int32 = 2): Boolean;
```

- **`Hover`**: tries to hover the object if it's already visible on the mainscreen. Does NO
  movement — if the object isn't visible right now (outside the field of view/too far away), it returns `False`.
- **`WalkHover`**: like `Hover`, but first walks (`WebWalk`) toward the object until it becomes visible/within
  reach, then hovers. This is the one you almost always want for "walk up to and interact."
- **`Click`/`WalkClick`**: `Hover`/`WalkHover` + a click, with built-in uptext verification if
  `Filter.UpText = True`.
- **`SelectOption`/`WalkSelectOption`**: like `Click`/`WalkClick` but right-click + menu selection
  (`ChooseOption.Select(action)`) instead of left-click — use this when the action you want isn't
  the default click (e.g. `Self.Coffer.WalkSelectOption(['Empty'])`).

Practical examples:

```pascal
if Self.MeltingPot.WalkClick() then                       // walk up and left-click
  Result := WaitUntil('Ore' in Chat.GetChat(), 100, 2000);

Clicked := Self.Obj_WestPortal.WalkClick(True, 2);          // True = left-click, 2 = attempts

if not Self.BarDispenser.WalkHover() then Exit;             // just walk up + hover, click separately
```

### Low level: `Map.Walker.Click(minimapPoint, randomness)`

The internal click function that `WalkPath`/`WalkBlind` use for each sub-step while walking.
You almost never call it directly yourself, but if you need to override click behavior during
movement (e.g. for antiban), this is where it hooks in.

### Summary: which function when?

| Situation | Function |
|---|---|
| Go to a known world coordinate, short/simple distance | `Map.Walker.WalkBlind(point)` |
| Go to a known world coordinate, complex distance/doors | `Map.Walker.WebWalk(point)` |
| Interact with an object that's already visible | `obj.Hover` / `obj.Click` |
| Interact with an object you might need to walk up to | `obj.WalkHover` / `obj.WalkClick` |
| Interact but with a non-default option (right-click menu) | `obj.WalkSelectOption(['Action'])` |

---

## 6. Waiting for and verifying movement

```pascal
function  TRSMinimap.HasFlag(): Boolean;
function  TRSMinimap.HasFlag(waitTime: Int32): Boolean; overload;
procedure TRSMinimap.WaitFlag(UntilDistance: Int32 = 0);
function  TRSMinimap.IsPlayerMoving(MinShift: Integer = 500): Boolean;
procedure TRSMinimap.WaitPlayerMoving(MinShift: Integer = 500; Timeout: Int32 = 20000);
procedure TRSMinimap.WaitMoving();
```

- **`Minimap.HasFlag()`** — true if the red destination flag is currently visible on the minimap
  (i.e. a click for movement was registered). `HasFlag(waitTime)` polls for up to `waitTime` ms.
- **`Minimap.WaitFlag(untilDistance)`** — blocks until the flag disappears (you have arrived) or
  until it comes within `untilDistance` pixels of the minimap center. Has a built-in timeout
  (`SRL.TruncatedGauss(4000, 6000)` ms) so it doesn't hang permanently if the flag never disappears.
- **`Minimap.IsPlayerMoving(minShift)`** — compares pixel shift around the minimap center over time; true if
  the player is moving (animation/movement causes pixel movement even if the flag is already gone).
- **`Minimap.WaitPlayerMoving(minShift, timeout)`** — blocks until `IsPlayerMoving` becomes false.
- **`Minimap.WaitMoving()`** — the one most commonly used in practice (`wasp_jewelry_smelter.simba`:
  `Minimap.WaitMoving();` right after a click) — internally combines timeout + countdown logic, so
  it handles both "flag exists but the player has already stopped" and short bounces in motion detection.

Typical pattern after a click-based action that makes the player move (e.g. opening an interaction
that triggers a short movement):

```pascal
if Self.MeltingPot.WalkClick() then
begin
  Minimap.WaitMoving();
  Result := WaitUntil('Ore' in Chat.GetChat(), 100, 2000);
end;
```

Note: `WalkHover`/`WalkClick` on `TRSObjectV2` already handle their own waiting/path-following internally
via `WebWalk`/`WalkPath` — you usually only need `Minimap.WaitMoving()` after the LAST bit of
movement (e.g. after clicking an NPC for dialogue, or a bank booth to open an interface), not after every small step.

---

## 7. Position reading and location checks

### Read the current position

```pascal
Map.Position();          // function TRSMap.Position(): TPoint — world coordinate
Map.Position;             // same thing without parentheses (Lape allows both)
Map.FullPosition();       // TRSPosition — TPoint + Z (height) + Plane
Map.Similarity;           // 0.0–1.0, how confident the match was (for debugging)
```

There is **no** `Self.RSW.GetMyPos` in the new style — that was the old `TRSWalker` method.
The equivalent in the `Map` system is called `Map.Position()`. (`TRSWalkerV2` doesn't even have its own
`GetMyPos`/`Position` implementation; `Position` is a **function pointer field** that is set up by
`TRSMap.InternalSetup` to point at `@Self.Position` on `TRSMap` itself — so `Map.Walker.Position()`
and `Map.Position()` are, in practice, the same call.)

### Building location checks

Two main patterns, both seen repeated multiple times in `bigaussie_gemstone_crab_slayer.simba` and
`aeroguardians.simba`:

**`TBox.Contains` / `InBox`** — for rectangular areas:

```pascal
const
  CIVITAS_BOX: TBox = [2572, 37822, 2756, 37930];
  TAL_TEKLAN_BOX: TBox = [776, 38038, 848, 38094];
begin
  if WaitUntil(Map.Position.InBox(CIVITAS_BOX), 65, CIVITAS_TELEPORT_TIMEOUT) then ...
  if Map.Position.InBox(TAL_TEKLAN_BOX) then ...
end;
```

(`TBox.Contains(p)` and `p.InBox(box)` are the same comparison, just with subject/object reversed — use
whichever reads more naturally.)

**`SRL.PointInPoly`** — for non-rectangular areas (e.g. an irregular bank zone or a room):

```pascal
const
  TEMPLEBOUNDS: TPointArray = [[...], [...], ...];  // polygon corners in world coordinates
begin
  Result := SRL.PointInPoly(Map.Position, TEMPLEBOUNDS);
end;
```

seen identically in `wasp_ardougne_knights.simba`:

```pascal
if not SRL.PointInPoly(Map.Position(), Self.BankBounds) then ...
```

**Rule:** define location boundaries as named constants (`XXXBOUNDS`/`XXX_BOX`) at the top of the script,
not hardcoded boxes scattered throughout the logic — this makes it much easier to adjust boundaries later
without searching through the entire file.

---

## 8. Common pitfalls

1. **Mixing world coordinates with local/image coordinates.** If part of the script uses
   `Map`/`TRSObjectV2` (world coordinates, 4–5 digits) and another part happens to reference an old
   `RSW: TRSWalker` instance (local image-pixel coordinates), all distance calculations and
   `WalkBlind` calls will be wrong without Simba complaining — both types are `TPoint`, so the compiler sees
   no error. Symptom: the player walks in a completely wrong direction, or `AtTile`/`InRange` checks are always
   false. Stick to ONE walker source per script (`Map.Walker`), and if you migrate an old
   script, convert ALL coordinates at the same time — not gradually.

2. **Forgetting `Objects.Setup(Map.Objects(), @Map.Walker)` (or `NPCs.Setup(...)`) before
   `Objects.Get`/`GetAll`/`GetNearest` is used.** Without this setup, `Objects.Data` (the internal
   `TJSONArray`) is empty or points to the wrong data, and you get `TerminateScript('Object ... doesn't exist on
   the loaded maps.')` even though the object exists on the map visually. Run setup right after
   `Map.SetupChunk(...)`, never conditionally/lazily.

3. **The `Walker` pointer is `nil` on a manually created `TRSObjectV2`.** If you build the object yourself
   with `TRSObjectV2.Setup(height, coordinates)` instead of `Objects.Get(...)`, the `Walker`
   field is NOT set automatically — you must set `obj.Walker := @Map.Walker;` yourself afterward. If you forget
   it, you get `TerminateScript('[TRSMapObject]:[Fatal]: X has no walker pointer set.')` as soon as you
   call `WalkHover`/`WalkClick`/`Hover` with `Filter.Walker = True` (which is the default).

4. **Chunk coordinates and world coordinates are NOT the same scale.** `Map.SetupChunkEx`/
   `ERSChunk.Get` take coordinates in **chunk units** (each chunk = 64x64 tiles), while
   `TRSObjectV2.Setup`/`Map.Position`/your boundary boxes are in **world coordinates** (tile units).
   `Box(49,51,50,49)` (a chunk box) should not be confused with `[7220, 31038, 7300, 31100]`
   (a world-coordinate box). If a location doesn't seem to load the right map, first check whether you
   accidentally sent world coordinates to a chunk function or vice versa.

5. **Assuming `WalkClick`/`Click` succeeded based solely on the return value, without considering
   uptext context.** `_ClickHelper`/`_SelectHelper` already try to verify uptext before a click if
   `Filter.UpText = True` (default), but if you set `Filter.UpText := False` yourself for performance,
   you lose that safety mechanism — a click can then hit the wrong object if several color-matching
   things overlap on screen. Only turn off the `UpText` filter if you really know the uptext
   string is unreliable for that specific object.

6. **Confusing `Hover`/`Click` (no movement) with `WalkHover`/`WalkClick` (movement
   included).** Accidentally using the non-walking variant on an object that is out of
   sight just gives `False` with no clear error indication unless you log/check the return value —
   it looks like "the object wasn't found," even though it actually just never tried to walk there.

7. **Relying on `WalkBlind` over longer distances with obstacles.** `WalkBlind` draws a straight line and has
   no collision awareness if the path is blocked by walls/objects along the way — it's made for short,
   open distances. Use `WebWalk`/`WalkHover` (which already path-finds via the webgraph) for anything that might
   have obstacles in the way.

8. **Dead/unused source files in the same directory can be misleading.** `SRL-T/osr/map/objects.simba`
   defines an almost identical but incompatible `TRSMapObject`/`TRSObjectV2` compared to
   `SRL-T/osr/map/mapobject.simba` — but `osr.simba` (the main includer) only loads `mapobject.simba`
   (line: `{$IFNDEF SRL_MAPOBJECT_INCLUDED} {$I osr/map/mapobject.simba}`), and both files guard
   themselves with the same `{$DEFINE SRL_MAPOBJECT_INCLUDED}` guard. `objects.simba` is therefore never
   included by the normal chain. If I (Claude) accidentally read `objects.simba` to understand
   "how `TRSObjectV2` works," I risk citing fields/behaviors that do NOT exist in the
   actually-running code (e.g. the `Filter.Minimap` names and `ERSMapObjectType.MMDOT` differ slightly
   between the files). **Always verify against `mapobject.simba`, not `objects.simba`, when citing
   `TRSObjectV2`/`TRSMapObject` fields.**

---

## 9. Checklist for walking code in a new script

1. Include `{$I SRL-T/osr.simba}` (and `{$I WaspLib/osr.simba}` if you need extra WaspLib functions).
2. `Map.SetupChunk(ERSChunk.XXX)` or `Map.SetupChunkEx(box, planes)` — do this ONCE, early
   (in `Init`/`Setup`), not conditionally in the middle of the main loop.
3. Right after: `Objects.Setup(Map.Objects(), @Map.Walker);` and if you need NPC lookup:
   `NPCs.Setup(Map.NPCs(), @Map.Walker);`.
4. Declare your `TRSObjectV2`/`TRSNPCV2` fields. For each one: either `Objects.Get('Name')`/
   `NPCs.Get('Name')`, or manually `TRSObjectV2.Setup(height, [[x,y]])` + `obj.Walker := @Map.Walker;`
   (do NOT forget the walker pointer on manual objects).
5. Define location boundaries as named `TBox`/`TPointArray` constants (`XXXBOUNDS`/`XXX_BOX`) if
   the script needs to know "am I in area X" — use `Map.Position.InBox(...)` or
   `SRL.PointInPoly(Map.Position, ...)`.
6. For movement: `WalkHover`/`WalkClick`/`WalkSelectOption` on an object/NPC when the target is something
   you're going to interact with; `Map.Walker.WalkBlind`/`WebWalk` on plain coordinates when you're only
   moving without interacting.
7. After a click that triggers movement: `Minimap.WaitMoving()` (or `Minimap.WaitFlag()` if you
   specifically want to wait for the flag to disappear/get close) before trusting that the player has arrived.
8. Double-check that no part of the code accidentally references an old `RSW: TRSWalker` instance or
   `TMSObject` — if you inherit/copy from an older script, fully convert coordinates and calls
   to the `Map` style instead of mixing.
