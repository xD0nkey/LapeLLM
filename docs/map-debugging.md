# Debugging a map/chunk setup before wiring it into a script

This file is a companion to `map-walking.md`: that file covers the `Map`/`Objects`/`NPCs`
API as used inside a real script. This file covers the *workflow for figuring out which
chunk box to pass to `Map.SetupChunk(s)` in the first place*, and how to visually confirm
it loaded the right area before trusting it in actual bot logic.

Sources: `SRL-T/osr/map/maploader.simba` and `SRL-T/osr/map/map.simba` (read directly,
function signatures confirmed against the installed source), plus a working debug
snippet and a third-party lookup site shared directly in conversation.

---

## 1. `map.orkabase.com` — a third-party chunk/coordinate lookup site

A community member pointed to <https://map.orkabase.com/> as a way to visually look up
map chunk coordinates and world coordinates for a given in-game area.

**This is a third-party, community-run site, not part of WaspLib/SRL-T/OSRS, and this
repository has not been able to verify its content directly** (an automated fetch of the
page was blocked by the site itself). Treat it the same way as any other secondary,
unverified source per the community-notes policy (`docs/community/index.md`): a
convenience lookup/lead, not a substitute for actually loading the chunk and confirming it
in-game with `Map.Debug()` (section 3) or `Map.Position()` (section 4).

---

## 2. `Chunk(box, plane)` — defining a one-off chunk without touching `ERSChunk`

`ERSChunk` (`SRL-T/osr/map/rschunk.simba`) only covers areas someone already added to the
enum. For anything else (a dungeon, a minigame area, a spot you only need once), build a
`TRSMapChunk` directly with the global `Chunk` function (`SRL-T/osr/map/maploader.simba`):

```pascal
function Chunk(b: TBox; plane: Int32): TRSMapChunk; overload;
function Chunk(b: TBox; planes: TIntegerArray): TRSMapChunk;
```

This is in fact exactly what `ERSChunk.Get()` itself does internally for every entry in
the enum, e.g. (`rschunk.simba`):

```pascal
ERSChunk.AL_KHARID: Result := Chunk(Box(50,51,53,48), 0);
```

So `Chunk(...)` isn't a workaround — it's the same primitive the official enum is built
from, just used directly. A real example shared in conversation, for a dungeon not in
`ERSChunk`:

```pascal
Map.SetupChunks([
    Chunk([46,147,48,145], 0),  // some dungeon, plane 0
    Chunk([46,47,48,45], 0)    // the area above it, plane 0
]);
```

**The `TBox` here is in CHUNK coordinates, not world coordinates** — see `map-walking.md`
pitfall 4. Each chunk covers 64x64 tiles; getting world coordinates and chunk coordinates
mixed up is the single most common reason a chunk setup "doesn't work."

---

## 3. `Map.Debug()` — seeing what actually got loaded

Confirmed overloads (`SRL-T/osr/map/map.simba`):

```pascal
procedure TRSMap.Debug(map: ERSMapType = ERSMapType.NORMAL; graph: Boolean = False);
procedure TRSMap.Debug(debugPoints: T2DPointArray = []);
procedure TRSMap.Debug(npc: TRSNPCV2); overload;
```

Calling `Map.Debug()` with no arguments opens a debug image of the chunk(s) you just
loaded. The `graph: Boolean` parameter (on the `ERSMapType` overload) additionally draws
the webgraph/walker nodes on top — useful for seeing whether the area you loaded actually
has path-finding data where you expect it, before you ever try to walk there with a real
script.

A minimal, standalone way to test a chunk setup before putting it in a real script
(no `TBaseScript`, no antiban, nothing else needed) — a real working example shared in
conversation:

```pascal
{$I WaspLib/osr.simba}

begin
  Map.SetupChunk(Chunk([57,161,59,159], 1));
  Map.Debug();
end.
```

Run this on its own, look at the debug image, and only once it visually matches the area
you intended, move the chunk box into the real script.

---

## 4. Add a buffer chunk — undersized boxes can give the wrong position

Practical guidance from conversation: **if the chunk box is too tight around the area you
actually need, `Map.Position()` can return a wrong/inaccurate position** — the usual fix
is to pad the box by one extra chunk on each side rather than sizing it exactly to the
area of interest.

This is a practical, experience-based tip, not something independently re-derived from
source in this repository — but it's consistent with how `Map.Position()` works (matching
the minimap against the loaded chunk image, per `map-walking.md` section 1b): a tightly
cropped chunk image gives the matcher less surrounding context to disambiguate against,
especially near the edge of the loaded area. Default to one chunk of padding on every
side; only tighten it back up if you've confirmed (via `Map.Debug()`/`Map.Position()`)
that the smaller box is still giving accurate positions.

---

## 5. Reading a confirmed real position, instead of guessing one

Once a chunk is loaded, the most reliable way to get a real, correct coordinate for a
specific in-game spot is to stand on it and print it — not to reverse-engineer it from
cached NPC/object coordinate data (see the "known gaps" note below).

```pascal
WriteLn(Map.Position());
WriteLn(Map.Position().DistanceTo([4432, 29402]));  // distance to a known point, for sanity-checking
```

`Map.Position` (without parentheses) and `Map.Position()` are equivalent — see
`map-walking.md` section 7.

---

## 6. Checklist: setting up a new/custom map area

1. Identify the area in-game. Optionally cross-check chunk coordinates against
   `map.orkabase.com` (section 1) as a lead — not as a confirmed source.
2. Build the chunk box in CHUNK coordinates (`Chunk([x1,y1,x2,y2], plane)`), padded by
   one extra chunk on each side (section 4) unless you've already confirmed a tighter box
   works.
3. `Map.SetupChunk(s)` with that chunk (or array of chunks).
4. `Map.Debug()` to visually confirm the loaded area matches what you intended, optionally
   with `graph := True` to also check webgraph coverage for the route you'll actually walk.
5. Stand at the specific spot(s) you need in-game and `WriteLn(Map.Position())` to get a
   real, confirmed world coordinate — don't derive one from cached map data and assume
   it's pixel/tile-perfect.
6. Only after 1-5 succeed, wire the chunk box and any specific coordinates into the real
   script.

---

## Known gap

Reverse-engineering a specific real-world location purely from the `coordinates` arrays
cached in SRL-T's map data files (`osr/map/files/npcs.zip`/`objects.zip`) is unreliable —
those files cover wide areas with multiple, sometimes visually similar, named clusters
(e.g. several different "Goblin" spawn groups, several "Gate" objects where only one
actually has a `Pay-toll` action). This was tried during this repository's own research
and got the wrong location more than once before being corrected. Prefer the workflow in
this file (load the chunk, `Map.Debug()`, stand on the real spot and read
`Map.Position()`) over coordinate-clustering guesses whenever a script needs to target a
specific location.
