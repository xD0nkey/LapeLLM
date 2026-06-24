# Camera and minimap (zoom, rotation, field of view)

This is a deep-dive that belongs together with `script-anatomy.md` (section 8, the Antiban system).
That file gives the helicopter view of Antiban as a whole; this file goes deeper specifically into
**camera control** (zoom + compass angle) and what `Minimap` can read/affect regarding the camera's
field of view. Walking/pathing (TRSWalker, clicking the minimap to walk) is NOT covered here.

Everything verified directly against the source code in:
- `SRL-T/osr/antiban.simba`
- `SRL-T/osr/mm2ms.simba`
- `SRL-T/osr/interfaces/minimap.simba`
- `SRL-T/osr/interfaces/mainscreen/mainscreen.simba`
- `WaspLib/osr/antiban/antiban.simba`
- `WaspLib/utils/input/mousezoom.simba`
- Practical examples from `Ny mapp/*.simba`, `aeroguardians.simba`, `bigaussie_gemstone_crab_slayer.simba`.

---

## 1. Zoom

### 1.1 Self.MinZoom / Self.MaxZoom on TAntiban

`TAntiban` (defined in SRL-T `antiban.simba`) has two fields:

```pascal
TAntiban = record(TSRLBaseRecord)
  ...
  Skills: array of ERSSkill;
  MinZoom, MaxZoom: Int32;     // 0..100, same scale as the Options zoom slider
  ...
end;
```

These are usually set in your own override of `TAntiban.Setup()` (or directly in the script's `Setup`
procedure if you're not overriding `Setup`). The values are on the same scale as the zoom slider in the
game's Options tab (0 = fully zoomed out, 100 = fully zoomed in).

Concrete examples from actual scripts (`Ny mapp/*.simba`):

```pascal
// gem_miner: tight zoom range, the miner stays close to its target
Antiban.MinZoom := 28; Antiban.MaxZoom := 32;

// ptk_starminer: override of TAntiban.Setup
procedure TAntiban.Setup(); override;
begin
  Self.Skills := [ERSSkill.MINING, ERSSkill.TOTAL];
  Self.MinZoom := 0;
  Self.MaxZoom := 60;
  Self.AddTask(2 * ONE_MINUTE, @Self.RandomClickTask, 0.33);
  Self.AddTask(5 * ONE_MINUTE, @Self.RandomFocusTask, 0.33);
  inherited;
end;

// wasp_enchanter / wasp_herblore
Antiban.MinZoom := 15;
Antiban.MaxZoom := 85;

// wasp_blast_furnace: very zoomed out (a lot to keep track of in the room)
Antiban.MinZoom := 0;
Antiban.MaxZoom := 10;
```

**Guidance for choosing a range:** a narrow range (e.g. 28-32) when the script constantly needs a
specific zoom level to reliably find objects (e.g. color search against a deposit box). A wide range
(e.g. 0-85) when the script mostly navigates open areas and can tolerate variation. See section 5 for
the pitfall of unreasonable ranges.

### 1.2 MM2MS.GetZoomLevel() / Options.GetZoomLevel()

`MM2MS` (the minimap-to-mainscreen projector) caches the current zoom level in `MM2MS.ZoomLevel` so
repeated calls don't need to read the Options slider every time:

```pascal
function TMM2MS.GetZoomLevel(): Integer;
begin
  if (Self.ZoomLevel = -1) then
  begin
    Self.ZoomLevel := Options.GetZoomLevel();  // reads the slider in the Options tab
  end;
  Result := Self.ZoomLevel;
end;
```

`Options.SetZoomLevel()` is overridden in SRL-T to keep `MM2MS.ZoomLevel` automatically in sync:

```pascal
function TRSOptions.SetZoomLevel(Level: Int32): Boolean; override;
begin
  Result := inherited();
  if Result then
    MM2MS.ZoomLevel := Level;
end;
```

So use `MM2MS.GetZoomLevel()` when you only need to read the current zoom (fast, no extra color
search), and `Options.SetZoomLevel(level)` when you explicitly want to set an exact level via the
Options tab (opens/interacts with the Options interface, so more expensive/visible).

### 1.3 RSMouseZoom.SetZoomLevel() (WaspLib)

WaspLib adds `RSMouseZoom`, which zooms with the **scroll wheel** instead of clicking the Options
slider — faster and looks more human. It also keeps `MM2MS.ZoomLevel` in sync:

```pascal
function TRSMouseZoom.SetZoomLevel(level: Int32): Boolean;
```

Takes a level on the same 0..100 scale as `Options.SetZoomLevel`, internally converts it to the raw
0..768 scale (`TRSMouseZoom.MAX_ZOOM = 768`, because the scroll wheel has a much finer resolution than
the slider's 0..100), and scrolls until it lands within +-4 levels of the target. This is **not 100%
exact** — it's accepted within +-4, which is fully sufficient for antiban purposes.

```pascal
RSMouseZoom.SetZoomLevel(75); // scrolls until MM2MS.ZoomLevel is within 75±4
```

WaspLib's own `TAntiban.AdjustZoom` (see 1.4) specifically uses `RSMouseZoom.SetZoomLevel`, not
`Options.SetZoomLevel`, for exactly that reason — the scroll wheel is more natural for antiban.

### 1.4 TAntiban.AdjustZoom — the override pattern

This is the built-in antiban task that periodically makes a random, but bounded, zoom adjustment. The
SRL-T base version:

```pascal
procedure TAntiban.AdjustZoom();
var
  zoom, newZoom: Int32;
  attempts: Int32;
begin
  if Self.MaxZoom = 0 then
    Self.MaxZoom := 100;               // safety net in case you forgot to set MaxZoom

  zoom := MM2MS.GetZoomLevel();
  zoom := Min(Self.MaxZoom, Max(Self.MinZoom, Options.GetZoomLevel()));

  repeat
    Inc(attempts);
    if attempts > 100 then
      Exit;                            // gives up if it can't find a "sufficiently different" level

    newZoom := SRL.SkewedRand(zoom, Self.MinZoom, Self.MaxZoom);
  until Abs(zoom - newZoom) > 15;       // requires at least 15 levels of difference, otherwise the change is pointless

  Self.DebugLn('Adjust zoom: ' + ToString(newZoom));
  Options.SetZoomLevel(NewZoom);
end;
```

WaspLib overrides this in `WaspLib/osr/antiban/antiban.simba` to use the scroll wheel (`RSMouseZoom`)
instead, and to skip the adjustment if an interface (e.g. the bank) is open:

```pascal
procedure TAntiban.AdjustZoom(); override;
var
  zoom, newZoom: Int32;
  attempts: Int32;
begin
  if Self.MaxZoom = 0 then
    Self.MaxZoom := 100;

  if RSInterface.IsOpen() then
    Exit;                              // makes no zoom change while an interface is open

  zoom := EnsureRange(MM2MS.GetZoomLevel(), 0, 100);

  repeat
    Inc(attempts);
    if attempts > 100 then
      Exit;

    newZoom := SRL.SkewedRand(zoom, Self.MinZoom, Self.MaxZoom);
  until Abs(zoom - newZoom) > 15;

  Self.DebugLn('Adjust zoom: ' + ToString(newZoom));
  RSMouseZoom.SetZoomLevel(newZoom);
end;
```

**The pattern to follow in your own script:** you normally do NOT override `AdjustZoom` yourself
(WaspLib has already done it well). What you do is set `Self.MinZoom`/`Self.MaxZoom` in your
`TAntiban.Setup()` override, and then add the task (already done automatically by WaspLib's
`SetupTasks` if `WLSettings` has `antiban.tasks.camera = true`):

```pascal
Self.AddTask(3 * ONE_MINUTE, @Self.AdjustZoom, 0.33);
```

If you want full manual control (your own script without WaspLib's `SetupTasks`), add the task
explicitly after setting Min/MaxZoom.

---

## 2. Rotation / compass angle

### 2.1 Minimap.GetCompassAngle() / SetCompassAngle()

```pascal
function TRSMinimap.GetCompassAngle(asDegrees: Boolean = True): Double;
```

Reads the compass's red pointer in the minimap orb and calculates the angle via color clustering (not
via any game API — this is "real" image analysis). Returns degrees by default, radians if
`asDegrees = False`.

```pascal
procedure TRSMinimap.SetCompassAngleEx(degrees, accuracy: Double);
procedure TRSMinimap.SetCompassAngle(degrees: Double);
procedure TRSMinimap.SetCompassAngle(minDegrees, maxDegrees: Double); overload;
```

`SetCompassAngle` controls the camera by **holding down the middle mouse button and dragging** the
mouse (`MOUSE_MIDDLE`), just like a player would. It therefore requires the setting "Middle mouse
button controls the camera" to be enabled in the game — otherwise it times out after ~6-8 seconds and
logs a warning about this. It iterates until the angle is within `accuracy` degrees (default 5) of the
target.

```pascal
Minimap.SetCompassAngle(180);                 // exact angle
Minimap.SetCompassAngle(0, 360);              // random angle within the range (Gaussian-distributed)
```

### 2.2 Antiban.RandomRotate / Antiban.SmallCameraRotation

Two separate antiban tasks with different purposes:

```pascal
// SRL-T: large, "above-restart"-style rotation
procedure TAntiban.RandomRotate();
begin
  case SRL.Dice(50) of
    True:  Minimap.SetCompassAngle(Minimap.GetCompassAngle() - SRL.TruncatedGauss(30, 360, 3));
    False: Minimap.SetCompassAngle(Minimap.GetCompassAngle() + SRL.TruncatedGauss(30, 360, 3));
  end;
end;
```

`RandomRotate` can turn the camera up to a full revolution (30-360 degrees, Gaussian-skewed toward
smaller values). It's a clear, "script-breaking" movement that a real player sometimes makes (e.g. to
look around).

```pascal
// WaspLib: small, discreet adjustment "by Flight"
procedure TAntiban.SmallCameraRotation();
begin
  Self.DebugLn('Small camera rotation');
  Minimap.SetCompassAngle(Minimap.GetCompassAngle() + Random(-15, 15));
end;
```

`SmallCameraRotation` only makes a small angle adjustment (±15 degrees) — more of a "nervous fidget"
than an actual reorientation. WaspLib combines both in a POV task:

```pascal
procedure TAntiban.RandomPOVTask();
begin
  case Random(10) of
    0..4: Self.AdjustZoom();
    5..7: Self.SmallCameraRotation();
    else  Self.RandomRotate();
  end;
end;
```

**Why rotate the camera at all — two separate reasons:**
1. **Antiban** — a game bot that never rotates the camera is a strong bot signal. Real players rotate
   and zoom constantly, often without reason.
2. **Practical/functional** — some mainscreen objects are obscured by terrain, walls, or other objects
   from the current camera angle. Rotating the camera (or zooming out) can make an otherwise invisible
   object clickable. This isn't merely cosmetic; if a script fails to find an object it knows exists
   on the minimap, a compass rotation may be the fix, not a bug in the object search.

`WalkingTasks` in WaspLib's antiban also runs `RandomRotate` (not `SmallCameraRotation`) with low
probability (~1% chance per walk step, and only if `tasks.camera` is enabled in WLSettings) while the
script walks, so the entire walk doesn't look unnaturally static.

---

## 3. How the camera's angle/zoom affects visibility

### 3.1 MainScreen.IsVisible(point)

```pascal
function TRSMainScreen.IsVisible(p: TPoint): Boolean;
function TRSMainScreen.IsVisible(tpa: TPointArray; useCenter: Boolean = True): Boolean; overload;
function TRSMainScreen.IsVisible(b: TBox; useCenter: Boolean = True): Boolean; overload;
function TRSMainScreen.IsVisible(rect: TRectangle; useCenter: Boolean = True): Boolean; overload;
function TRSMainScreen.IsVisible(cuboid: TCuboidEx; useCenter: Boolean = True): Boolean; overload;
```

Checks whether a point/area is not hidden behind the Chatbox, Minimap, or GameTabs (only relevant in
resizable mode — in fixed mode there's no overlap to worry about, so the function returns early).
**This is NOT the same thing as the object actually being visible in 3D space** — `IsVisible` only
checks against the bounds of the 2D interfaces. If the mainscreen rectangle for an object (calculated
via `MM2MS`/`PointToMSRect` given the current zoom and angle) ends up behind the camera's "hill" or
entirely outside the field of view, the mainscreen-projected point will often not even exist or will
land completely wrong — that's a separate problem solved by adjusting zoom/angle (see 3.2), not by
`IsVisible`.

Practical pattern: check `MainScreen.IsVisible(p)` AFTER you have projected a minimap point to the
mainscreen and BEFORE you try to click it, to avoid clicking straight into the chatbox or the minimap
itself.

### 3.2 Minimap.MakePointVisible / SetZoomToPoint / GetZoomToPoint

```pascal
function TRSMinimap.GetZoomToPoint(p: TPoint; randomness: Int32 = 0): Int32;
```
Calculates which zoom level would make point `p` (a minimap coordinate) visible on the mainscreen,
based on the distance from the minimap's center:

```pascal
Result := Round((73 - distance) / 0.8);
Result := Result + randomness;
```

```pascal
function TRSMinimap.SetZoomToPoint(p: TPoint; randomness: Int32 = 0): Boolean;
```
Actually sets that zoom level via `Options.SetZoomLevel`, but only if the point isn't already within
zoom range (`Self.InZoomRange(p)`).

```pascal
function TRSMinimap.MakePointVisible(p: TPoint): Boolean;
function TRSMinimap.MakePointVisible(tpa: TPointArray): Boolean; overload;
```
Combines `SetZoomToPoint` AND `FacePoint` (rotates the compass toward the point) — the default
implementation thus performs BOTH a zoom adjustment and a compass rotation to guarantee the point
becomes visible:

```pascal
function TRSMinimap.MakePointVisible(p: TPoint): Boolean;
begin
  Result := Self.SetZoomToPoint(p, Random(-5, 5)) and Self.FacePoint(p, Random(-3, 3));
end;
```

### 3.3 The override pattern: disabling automatic camera rotation

Several fielded scripts (e.g. `aeroguardians.simba`) override `MakePointVisible` and `SetZoomToPoint`
to REMOVE the rotation part entirely:

```pascal
function TRSMinimap.SetZoomToPoint(p: TPoint; randomness: Int32 = 0): Boolean; override;
begin
  Result := Self.InZoomRange(p);
  randomness := 0;
end;

// Get rid of camera rotating that bogs down *everything*
function TRSMinimap.MakePointVisible(p: TPoint): Boolean; override;
begin
  Result := Self.SetZoomToPoint(p, Random(-5, 5));
end;
```

The same comment ("Get rid of camera rotating that bogs down everything") recurs in the same file above
overrides of `TRSWalkerV2._WalkPathHelper`, `TRSMapObject._HoverHelper`, and
`TRSMapObject._WalkHoverHelper` — all places where the default behavior would otherwise trigger a
compass rotation (via `FacePoint`/`MakePointVisible`) every time the script tries to find or click an
object that isn't directly visible.

**Why you'd WANT to disable this:** every compass rotation is performed via `SetCompassAngleEx`, which
drives the mouse in a loop until the angle matches (see 2.1) — this typically takes several hundred
milliseconds up to a few seconds PER call, and is potentially called every time an object needs to be
found/clicked. In scripts that do many fast object lookups (e.g. an area-based AIO script with many
NPCs/objects per minute), this becomes a serious performance bottleneck — hence "bogs down everything."

**The trade-off:** without automatic rotation, the script may miss objects that are only visible from a
different camera angle (e.g. an object behind a wall from the current angle). This is instead solved by
manually ensuring the camera is already at an angle where everything relevant is visible (e.g. a fixed
high zoom-out + fixed angle for the entire activity area), or by explicitly calling
`Minimap.SetCompassAngle` on your own terms instead of letting it happen implicitly/unexpectedly inside
every hover/walk call. So it's a deliberate trade-off: faster, more predictable performance against
slightly reduced robustness at unusual camera angles — reasonable in scripts where the player mostly
stays within a small, well-mapped area.

---

## 4. Minimap reading tied to the camera: PointToMSRect / VectorToMSRect

```pascal
function TRSMinimap.VectorToMSRect(vector: Vector3; weSize, nsSize: Double = 1; roll: Single = $FFFF): TRectangle;
function TRSMinimap.PointToMSRect(pt: TPoint; weSize, nsSize: Double = 1; roll: Single = $FFFF): TRectangle;
function TRSMinimap.StaticToMsRect(staticMMPoint: TPoint; weSize, nsSize: Double = 1; Height: Double = 0): TRectangle;
```

These convert a minimap coordinate (2D, top-down) into a `TRectangle` on the mainscreen (a
3D-projected surface), given:
- `weSize`/`nsSize` — the rectangle's size in RS tiles (west-east / north-south), default 1x1 tile.
- `roll` — the compass angle to project with. Leaving it at `$FFFF` (default) makes the function
  automatically fetch the current `Minimap.GetCompassAngle()`. `StaticToMSRect` assumes the input
  coordinate was calculated with compass angle 0 (i.e. "north up") and rotates it to the current angle
  before projecting.

```pascal
function TRSMinimap.VectorToMSRect(vector: Vector3; weSize, nsSize: Double = 1; roll: Single = $FFFF): TRectangle;
var
  Arr: TPointArray;
begin
  if weSize <= 0 then weSize := 1;
  if nsSize <= 0 then nsSize := 1;
  // tiles are ~4 pixels tall/wide on the minimap, so we expand 2px in each direction per tile
  Arr := MM2MS.Run([Vec3(vector.X-weSize, vector.Y-nsSize, vector.z),
                    Vec3(vector.X+weSize, vector.Y-nsSize, vector.z),
                    Vec3(vector.X+weSize, vector.Y+nsSize, vector.z),
                    Vec3(vector.X-weSize, vector.Y+nsSize, vector.z)], roll);
  Result := [Arr[0], Arr[1], Arr[2], Arr[3]];
end;
```

The point: this is HOW `MM2MS` (the minimap-to-mainscreen projector) actually works internally — it
takes a minimap coordinate + current zoom + current compass angle and calculates where on screen
(mainscreen) that same physical location is. Everything that "finds an object on the minimap and clicks
it on the mainscreen" (`Minimap.GetDots`, `TRSMapObject` searches, etc.) goes through this kind of
projection under the hood. That's why zoom and angle are ALWAYS relevant before a click: change either
one and the same minimap coordinate projects to a completely different mainscreen rectangle.

Practical example (WaspLib's `HoverMSTile`, by Flight) showing the pattern in practice — fetch a dot
from the minimap, project it to the mainscreen using the current angle, and only proceed if the result
actually lands within the mainscreen bounds:

```pascal
a := Minimap.GetCompassAngle(False);
rDot := dots[Random(Low(dots), High(dots))];
msBox := Minimap.VectorToMSRect(Vec3(rDot.X + 2, rDot.Y + 2, 0), 1, 1, a).Bounds();
if MainScreen.Bounds.Contains(msBox) then
begin
  // ok to interact with msBox
end;
```

---

## 5. Common pitfalls

1. **Forgetting that zoom/angle determine whether an object is clickable before attempting to click.**
   An object can exist in `Minimap.GetDots(...)` (i.e. exist and be within minimap range) but still not
   be clickable on the mainscreen, if the current zoom/angle projects it outside `MainScreen.Bounds` or
   behind terrain. Always check the result of the projection
   (`PointToMSRect`/`VectorToMSRect` + `MainScreen.Bounds.Contains(...)` or `MainScreen.IsVisible`)
   before clicking — otherwise you click blindly at the wrong coordinate or get an uptext miss.

2. **Setting unreasonable Min/MaxZoom ranges.**
   `TAntiban.AdjustZoom` requires `Abs(zoom - newZoom) > 15` to make any change at all, and gives up
   after 100 attempts. If `MaxZoom - MinZoom < 15` (e.g. by mistake `MinZoom := 30; MaxZoom := 35`),
   `AdjustZoom` will NEVER find an acceptable new value and the task effectively becomes a no-op every
   time it runs (logs no error, just silently gives up) — the antiban zoom task exists but never does
   anything. Keep at least ~20-30 points of spread between Min and Max if you want the task to actually
   be visible.

3. **Leaving `MaxZoom = 0` (default) without thinking about it.**
   Both SRL-T's and WaspLib's `AdjustZoom` have a safety rule `if Self.MaxZoom = 0 then Self.MaxZoom := 100;`
   — if you accidentally only set `MinZoom` but forget `MaxZoom`, the range becomes `MinZoom..100`,
   which is likely much wider than you intended (it could zoom all the way out in the middle of a bank
   trip, for example).

4. **Overriding `MakePointVisible`/`SetZoomToPoint` without understanding the trade-off.**
   See section 3.3 — it's a valid, used pattern for performance, but if you copy it blindly in a script
   that covers a large or complex area, objects that are only visible from a different angle may become
   completely unfindable. Only use the pattern if you have already ensured a suitable fixed camera angle
   for the entire activity area.

5. **Assuming `SetCompassAngle` always succeeds.**
   It requires the setting "Middle mouse button controls the camera." If it's disabled, the function
   silently times out (only logs a debug line) after 6-8 seconds without changing the angle. If compass
   rotation is critical to your script's logic (not just antiban seasoning), it's worth verifying the
   setting at startup or handling the case where the angle didn't change.

6. **Confusing `Options.SetZoomLevel` and `RSMouseZoom.SetZoomLevel`.**
   Both keep `MM2MS.ZoomLevel` in sync, but they interact with the game in completely different ways
   (clicking the Options slider vs. the scroll wheel). If your script is already on a different tab than
   Options when you call `Options.SetZoomLevel`, it has to open the Options tab first — unnecessarily
   expensive if you only wanted to nudge the zoom slightly. Prefer `RSMouseZoom.SetZoomLevel` (WaspLib)
   for antiban-style minor adjustments in the middle of another activity.

---

## 6. Checklist: when writing camera-related code in a new script

1. **Set `Self.MinZoom`/`Self.MaxZoom` in your `TAntiban.Setup()` override** with at least ~20-30 points
   of spread, adapted to how tight/open the activity area is (tight color search → narrow range,
   open navigation → wide range).
2. **Let WaspLib's default antiban tasks handle zoom/rotation** unless you have a specific reason not
   to (`WLSettings` → `antiban.tasks.camera = true` gives you `AdjustZoom` + `RandomPOVTask` for free).
   Don't add your own duplicates of the same task.
3. **Before clicking anything derived from a minimap coordinate** (dot, object position, etc.), verify
   that the actual mainscreen projection (`PointToMSRect`/`VectorToMSRect`/`MM2MS`) lands within
   `MainScreen.Bounds` and is `MainScreen.IsVisible`, NOT just that it exists on the minimap.
4. **If an object isn't found even though it should exist**, ask yourself whether the current
   zoom/angle could be the culprit before suspecting the image search/color filters. Try zooming out or
   rotating to see if that resolves the issue.
5. **Only override `MakePointVisible`/`SetZoomToPoint` to disable auto-rotation** if you explicitly want
   to optimize away the performance cost of many hover/walk calls AND already have a reliable fixed
   angle for the entire work area. Comment on why (similar to
   `// Get rid of camera rotating that bogs down everything`) so future-you remembers the trade-off.
6. **Verify that "Middle mouse button controls the camera" is enabled** if the script depends on
   `SetCompassAngle`/`RandomRotate`/`SmallCameraRotation` actually succeeding, rather than just assuming
   it.
