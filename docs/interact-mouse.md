# Interaction and click patterns (Mouse, uptext, ChooseOption, object/NPC)

This file is solely about **the interaction/click itself** — not about walking to the object (walking/pathing is covered in the mapping file). Focus: how to make sure a click actually does what you think it will before pressing the mouse button, and how SRL-T/WaspLib already builds this into its object/NPC methods.

See also `script-anatomy.md` for the bigger picture of how a script is structured (layers, script skeleton, GUI). This file goes deeper into the click layer specifically.

Sources verified against actual code (not just memory):
- `SRL-T/utils/input/mouse.simba` (Mouse.Move/Click/Position/Speed/MissChance/Distribution/CanIdle)
- `SRL-T/osr/interfaces/mainscreen/mainscreen.simba` (IsUpText, GetUpText, DidRedClick)
- `SRL-T/osr/interfaces/chooseoption.simba` (ChooseOption.Open/Select/HasOption/Close)
- `SRL-T/osr/map/objects.simba` (TRSMapObject / TRSObjectV2 / TRSNPCV2 — Click/WalkClick/Hover/WalkHover/Find)
- `WaspLib/osr/walker/objects/rsobjects.simba`, `rsnpcs.simba` (concrete object/NPC instances built on top of the above)
- Real scripts: `aeroguardians (4).simba`, `wasp_blast_furnace.simba`, `wasp_herblore.simba`, `students_mhomes_+farm_bhruns.simba`, among others.

---

## 1. The Mouse module: core functions and humanization

`Mouse` is a global `TMouse` variable (record) that is already initialized when the script starts (`Mouse.Setup()` runs automatically). You **never** move/click using raw Simba input (`MoveMouse`/`ClickMouse` directly) in an SRL-T/WaspLib script — always go through `Mouse`.

### Core functions

```pascal
Mouse.Move(P: TPoint);                 // move the mouse to a point, "human-ish" path (WindMouse algorithm)
Mouse.Move(Box: TBox);                 // move to a randomized point within a box (respects Distribution)
Mouse.Move(Center: TPoint; Radius: Int32);
Mouse.Click(MOUSE_LEFT);               // click at the CURRENT mouse position
Mouse.Click(P: TPoint, MOUSE_LEFT);    // = Move(P) + Click — moves AND clicks in one call
Mouse.Click(Box: TBox, MOUSE_LEFT);
Mouse.Position(): TPoint;              // read the current mouse position
Mouse.Teleport(P: TPoint);             // NOT human-like, jumps directly — only for special cases (debug, certain interface clicks)
```

Buttons: `MOUSE_LEFT`, `MOUSE_RIGHT`, `MOUSE_SCROLL`, `MOUSE_EXTRA_1`, `MOUSE_EXTRA_2`.

Important: `Mouse.Click(Box, MOUSE_LEFT)` moves the mouse **and** clicks immediately — meaning there is NO built-in pause between "hover" and "click" if you use these overloads as-is. If you need to verify uptext before clicking (see section 2), you must split it yourself into `Mouse.Move(...)` followed by an uptext check, and only then `Mouse.Click(MOUSE_LEFT)` (without a point argument, i.e. click at the current position).

```pascal
// WRONG when uptext must be verified: this clicks immediately without checking what happens
Mouse.Click(myBox, MOUSE_LEFT);

// CORRECT: separate hovering and clicking
Mouse.Move(myBox);
if MainScreen.IsUpText('Fill') then
  Mouse.Click(MOUSE_LEFT);
```

### Humanization — usually set ONCE at script start

```pascal
Mouse.Speed       := 12;      // default 12. Lower = faster/more robotic, higher = slower/more human.
Mouse.MissChance  := 15;      // default 15 (%). Chance that the mouse deliberately "misses" the target slightly before correcting.
Mouse.Distribution := EMouseDistribution.MOUSE_DISTRIBUTION_ROWP; // default. Where in a TBox the mouse aims.
Mouse.CanIdle     := True;    // default True. Allows Mouse.Idle() (random pauses) based on IdleInterval.
Mouse.IdleInterval := 0;      // default 0 = off. Set to e.g. 1.0-3.0 if you want periodic "thinking pauses".
```

`EMouseDistribution` options:
- `MOUSE_DISTRIBUTION_RANDOM` — a completely random point in the box.
- `MOUSE_DISTRIBUTION_GAUSS` — weighted toward the center of the box.
- `MOUSE_DISTRIBUTION_SKEWED` — weighted toward the current mouse position.
- `MOUSE_DISTRIBUTION_ROWP` — like SKEWED but with a "rounder" distribution (default, most natural).

These four (`Speed`, `MissChance`, `Distribution`, `CanIdle`) are normally set once during the script's setup phase (e.g. in `TScript.Setup` or equivalent), not per click. If you want to temporarily make an extra precise/fast click (e.g. in a context menu), copy `Mouse` into a local `tmpMouse: TMouse` variable, adjust that copy, and use `tmpMouse.Move/.Click` — this way global humanization is unaffected. This is exactly what SRL-T's own `ChooseOption.Select` does internally:

```pascal
// From SRL-T's chooseoption.simba (TRSChooseOption.Select) — pattern worth copying
var tmpMouse: TMouse;
begin
  tmpMouse := Mouse;            // copy the whole record
  tmpMouse.MissChance := 0;     // no misses in a small menu row
  tmpMouse.IdleInterval := 0;   // no idling in the middle of a menu selection
  tmpMouse.Move(SRL.RandomPointEx(from, b));
  tmpMouse.Click(MOUSE_LEFT);
end;
```

`Mouse.DragTo(P)` exists for drag interactions (e.g. dragging items in the inventory) and automatically keeps the button held down during the movement.

---

## 2. Uptext verification — the core pattern for safe clicks

**Uptext** is the text in the upper-left corner of the mainscreen that shows what a left click will do (e.g. "Chop down Tree", "Talk-to Banker", "Fill"). This is the OSRS client's own feedback, and SRL-T reads it via OCR.

```pascal
function TRSMainScreen.GetUpText(): String;
function TRSMainScreen.IsUpText(Text: TStringArray; Timeout: Int32 = -1): Boolean;
function TRSMainScreen.IsUpText(Text: String; Timeout: Int32 = -1): Boolean; overload;
```

- `GetUpText()` reads and returns the text directly (a single OCR pass).
- `IsUpText(text, timeout)` polls repeatedly until the text matches **or** the timeout expires, and additionally requires two consecutive positive reads (50ms apart) before returning `True` — this protects against uptext "flickering" between frames. The default timeout, if you don't specify one, is a short randomized value (~100-250ms).
- Matching is **substring**-based ("text[i] in upText"), so `IsUpText('Tree')` matches both "Chop down Tree" and "Cut Tree".
- `Text` can be a `TStringArray` — returns `True` if **any** of the strings match. Useful for objects with multiple valid names.

### The complete pattern: hover, check uptext, only click if correct

This is the single most important rule in this file. **Never blindly trust that a left click on an item/object does what you expect** — context menus, dynamic item actions, and gate-like objects (which may have "Open"/"Close" that toggles) mean the same point on screen can mean different things depending on the game's state.

```pascal
Mouse.Move(targetBox);              // hover WITHOUT clicking
if MainScreen.IsUpText('Chop down') then
  Mouse.Click(MOUSE_LEFT)
else
begin
  // uptext didn't match — do NOT perform the click. Log it and handle per points 6/7.
  WriteLn('Uptext mismatch, expected "Chop down", got: ', MainScreen.GetUpText());
end;
```

For inventory items, the same principle applies with `Inventory.MouseItem` (hovers without clicking):

```pascal
if Inventory.MouseItem('Rune pouch') then
  if MainScreen.IsUpText('Fill', 150) then
    Mouse.Click(MOUSE_LEFT);
```

### A real bug we fixed: Fill/Empty on rune pouches (2025 update)

OSRS was updated in 2025 so that left-clicking e.g. rune pouches **dynamically toggles** between "Fill" and "Empty" depending on whether the pouch is already full, whether the inventory has room, and other context. A script that blindly left-clicks a pouch risks doing the opposite of what it intended (filling when it meant to empty, or vice versa), which in the worst case drops runes on the floor or gets stuck in a loop.

The robust solution, implemented in `aeroguardians (4).simba` → `TScript.HandlePouches`:

```pascal
// Left-click dynamically swaps between Fill/Empty depending on pouch + inventory state (2025 update) -
// verify via uptext which action is actually about to happen before clicking, since we're at an altar iff we want to Empty
Empty := InRange(Self.GetAltarLoc, TYPEAIR, TYPEBLOOD);

for i to High(Pouches) do
begin
  if Inventory.MouseItem(Pouches[i]) then   // (1) hover the item WITHOUT clicking
  begin
    if Empty then
      if Mainscreen.IsUpText('Empty', 150) then   // (2) verify that uptext says what we expect
      begin
        Mouse.Click(MOUSE_LEFT);                  // (3) click ONLY if uptext confirms
        Result := True;
      end;
    if (not Empty) then
      if (not Mainscreen.IsUpText('Empty', 150)) then  // i.e. uptext says "Fill" (the opposite of Empty)
      begin
        Mouse.Click(MOUSE_LEFT);
        Result := True;
      end;

    if Result then Wait(70,130);
  end;
end;
```

The lesson to generalize: **whenever a click's meaning can vary with the game's state** (filled/empty containers, doors that may be open/closed, items that may be on/off, NPCs whose default action changes depending on quest state) — always hover-verify-click, never `Mouse.Click(box, MOUSE_LEFT)` directly.

---

## 3. ChooseOption — right-click menus

`ChooseOption` (global `TRSChooseOption` variable) handles the context menu that opens on right-click.

```pascal
function ChooseOption.IsOpen(): Boolean;
function ChooseOption.IsOpen(WaitTime: Int32; Interval: Int32 = -1): Boolean; overload;
function ChooseOption.Open(): Boolean;                      // right-clicks IF it's not already open, waits up to 3000ms
function ChooseOption.HasOption(text: TStringArray; out option: TRSChooseOption_Option;
                                 caseSensitive: Boolean = True; closeIfNotFound: Boolean = True): Boolean;
function ChooseOption.Select(text: TStringArray; mouseAction: Int32 = MOUSE_LEFT;
                              caseSensitive: Boolean = True; closeIfNotFound: Boolean = True): Boolean;
function ChooseOption.Hover(text: TStringArray; caseSensitive: Boolean = True;
                             closeIfNotFound: Boolean = True): Boolean;   // = Select with MOUSE_MOVE, doesn't click
function ChooseOption.Close(): Boolean;
```

Important details:
- `Open()` right-clicks **only if the menu isn't already open** — safe to call multiple times.
- `Select(text, ...)` opens the menu if necessary (via the internal `HasOption` call), searches through all rows with OCR, and only clicks if the text is actually found. If the text matches a submenu arrow (`' >'`), it automatically navigates into the submenu.
- `closeIfNotFound` (default `True`) automatically closes the menu if the text wasn't found — otherwise you can get stuck with an open menu blocking the next state.
- `Select`/`Hover` accept a `TStringArray` — if, for example, you're not sure of the exact wording ("Empty" vs "Empty pouch"), you can pass multiple alternatives.

```pascal
// Typical pattern: right-click and select a specific option, close if it doesn't exist
if ChooseOption.Select(['Empty', 'Empty all']) then
  WriteLn('Selected Empty')
else
  WriteLn('Option not found, menu closed automatically');

// Just hover (to read what's available) without clicking:
ChooseOption.Hover('Cast');
```

`ChooseOption.Select(option, mouseAction)` (the variant taking an already-looked-up `TRSChooseOption_Option`) internally uses a `tmpMouse` copy with `MissChance := 0` and `IdleInterval := 0` — i.e. deliberately less "humanized" since the target area is small and you don't want to miss and click the wrong row in a menu.

---

## 4. Object interaction: TRSObjectV2 / TRSMapObject (WaspLib)

In WaspLib, `TRSObjectV2` and `TRSNPCV2` inherit from a common base, `TRSMapObject` (`SRL-T/osr/map/objects.simba`). All the real click/hover methods live on the base and work identically for objects and NPCs.

```pascal
function TRSMapObject.Find(out atpa: T2DPointArray): Boolean;
function TRSMapObject.IsVisible(): Boolean;
function TRSMapObject.Hover(attempts: Int32 = 2): Boolean;
function TRSMapObject.WalkHover(attempts: Int32 = 2): Boolean;     // walks to the object if necessary, then hovers
function TRSMapObject.Click(leftClick: Boolean = True; attempts: Int32 = 2): Boolean;
function TRSMapObject.WalkClick(leftClick: Boolean = True; attempts: Int32 = 2): Boolean;
function TRSMapObject.SelectOption(action: TStringArray; attempts: Int32 = 2): Boolean;
function TRSMapObject.WalkSelectOption(action: TStringArray; attempts: Int32 = 2): Boolean;
```

`.Click`/`.WalkClick` **already** perform the entire uptext-verification chain internally — which is exactly why these methods are preferable to writing your own `Mouse.Move`+`IsUpText`+`Mouse.Click` code when the object is already defined as a `TRSObjectV2`/`TRSNPCV2`:

1. `Hover`/`WalkHover` calls `_HoverHelper`/`_WalkHoverHelper`, which:
   - If a `ChooseOption` menu is already open from before, tries to find the object's name there, or closes the menu (see pitfall in section 7).
   - Calls `Self.Find(atpa)` to find the object's pixels on the mainscreen, moves the mouse there.
   - Verifies with `MainScreen.IsUpText(Self.Name)` that the hover actually shows the correct uptext.
   - Rotates the camera on the last attempt if the object wasn't found (it may be obscured).
2. `Click`/`WalkClick` = `Hover`/`WalkHover` **and then** `_ClickHelper`, which:
   - If `RedClicked` has already been registered (from an earlier successful click detection), returns `True` immediately.
   - If a `ChooseOption` menu is open, tries to select the object's name in it (otherwise closes the menu and fails).
   - Otherwise: `Mouse.Click(MOUSE_LEFT)` and checks `MainScreen.DidRedClick()`.
   - If `leftClick = False` (or the left click didn't produce a matching uptext), the right-click menu is opened via `ChooseOption.Select(Self.Name)` instead.

```pascal
// Practical example: click a bank object, with built-in uptext verification and 3 attempts
if RSObjects.GEBank.WalkClick(True, 3) then
  WriteLn('Successfully clicked the bank')
else
  WriteLn('Failed after 3 attempts — see section 6');

// SelectOption for objects that require a specific right-click option rather than the default left-click
RSObjects.Get('Furnace').WalkSelectOption(['Smelt']);
```

`.Find(out atpa: T2DPointArray)` is what you call if you **only** want to know whether/where the object appears on the mainscreen without touching the mouse at all — useful for a pure visibility check before committing to an interaction (e.g. in a `GetState()` function in a state machine, see section 6).

### Older, manually written pattern: TMSObject (found in older scripts, e.g. aeroguardians rev 21)

Before `TRSObjectV2`/WaspLib existed (or in scripts that chose not to use them), it was common to build your own small record for static objects (`TMSObject` in `aeroguardians (4).simba` — this is NOT an SRL-T/WaspLib type name, but a script-specific, hand-written struct). The pattern is still worth recognizing since it's the manual implementation of exactly the same idea that `TRSMapObject` automates:

```pascal
TMSObject = record
  Name      : String;
  Colors    : Array of TCTS2Color;
  UpText    : TStringArray;
  Tile, WalkTile, MidTile: TPoint;
  // ...
end;

function TMSObject.Find: Boolean;
begin
  // If an old context menu is left open, clean it up first
  if Inventory.GetSelectedSlot >= 0 then
    ChooseOption.Select('Cancel');

  // (a) Is uptext already correct without us having moved the mouse? (e.g. mouse already on the object)
  Result := MainScreen.IsUpText(Self.UpText, 75);
  if Result then Exit(Result);

  // (b) Are we in the middle of another menu ("->")? Cancel it.
  if MainScreen.IsUpText('->', 75) then
    ChooseOption.Select('Cancel');

  // (c) Find the object's pixels via color (TCTS2Color) within the tile box, move the mouse there
  Pt := GetObjPt;   // internal helper function: FindObject with Colors within the tile rectangle
  if Pt.X < 5 then Exit;
  Mouse.Move(Pt);

  // (d) Verify AFTER moving that uptext is now correct
  Result := MainScreen.IsUpText(Self.UpText, 75);
end;

function TMSObject.Interact(MouseMove: Boolean = True): Boolean;
begin
  if not Self.IsReachable then Exit;          // see the section on walking/mapping
  if WaitUntil(Self.Find, 75, 300) then        // try to find+hover within 300ms
  begin
    Mouse.Click(MOUSE_LEFT);
    Result := MainScreen.DidRedClick;          // verify AFTER the click that it registered
    if Result then Exit;
  end;
  // ... fallback: walk there and try again
end;
```

Three things to take away from this regardless of which library you use:
1. Check whether uptext already matches **before** moving the mouse (saves time if the mouse happens to already be in the right place).
2. Clean up old `->`/context menus **before** attempting a new hover.
3. Verify **both** before the click (uptext) and after the click (`DidRedClick`) — a double check.

---

## 5. NPC interaction: TRSNPCV2

`TRSNPCV2` inherits from `TRSMMDotV2`, which inherits from `TRSMapObject` — the same `.Click`/`.WalkClick`/`.Hover`/`.WalkHover`/`.Find` API as objects (section 4), plus minimap-dot detection (`ERSMinimapDot.NPC`) as a complement to color detection on the mainscreen.

The difference from static objects: NPCs move, and there are usually **several** of the same type on screen at once. `Find` already returns its results sorted by distance to the player (`SortFrom(MainScreen.GetPlayerBox().Center())` internally in `FindEx`), but when you collect NPC candidates yourself (e.g. to pick the "nearest free target" among several potential NPCs of the same type) you sort manually with `SortFrom`:

```pascal
var
  atpa: T2DPointArray;
  closest: TPointArray;
begin
  if NPCs.Find(atpa) then
  begin
    atpa := atpa.SortFrom(MainScreen.Center);  // sort clusters by distance to the screen's center
    closest := atpa[0];                         // nearest NPC cluster
    Mouse.Move(closest.RandomValue());
    if MainScreen.IsUpText(NPCs.Name) then
      Mouse.Click(MOUSE_LEFT);
  end;
end;
```

In practice, `NPCs.WalkClick()` used directly is usually enough — the internal `Find`/sorting+uptext verification is already done. Manual `SortFrom` sorting becomes relevant when you have **several different** NPC definitions to choose between (e.g. "attack whichever enemy is closest among these three monster types") and merge the results yourself before sorting:

```pascal
var all: T2DPointArray;
begin
  if Goblin.Find(atpa1) then all += atpa1;
  if Orc.Find(atpa2)    then all += atpa2;
  all := all.SortFrom(MainScreen.Center);
  // all[0] = nearest enemy regardless of type
end;
```

`Minimap.Center` is used the same way when you sort minimap dots instead of mainscreen clusters (see e.g. `WaspLib/optional/handlers/combathandler.simba`: `dots.Cluster(6).SortFrom(Minimap.Center)`).

---

## 6. Retry pattern: why interaction code almost always loops

Almost all click/hover code in SRL-T/WaspLib (and in every script reviewed) loops 2-8 attempts rather than trying just once. The reason: any individual step can temporarily fail for purely timing/rendering reasons without anything being fundamentally wrong — the camera may have rotated, another object may momentarily obscure the target, the client may have lagged a frame, OCR may fail to read the uptext on a single occasion. A single failure does NOT mean the target is unreachable.

The built-in methods already have `attempts` parameters (default usually `2`):

```pascal
function TRSMapObject.Click(leftClick: Boolean = True; attempts: Int32 = 2): Boolean;
function TRSMapObject.WalkClick(leftClick: Boolean = True; attempts: Int32 = 2): Boolean;
```

Increase `attempts` for objects known to be hard to find (obscured, small, moving) — e.g. `RSObjects.Get('...').WalkClick(True, 5)`.

A custom retry pattern when writing code on top of these (common in every script reviewed, e.g. `students_mhomes_+farm_bhruns.simba`):

```pascal
var attempts: Int32;
begin
  for attempts := 0 to 8 do      // "to 8" = max 9 attempts (0..8 inclusive)
  begin
    if SomeExitCondition then
      Break;                      // leave the loop as soon as the goal is achieved

    if MyObject.Hover(8, False) then
      MyObject.Click(True, 3);    // note: nested retry — Click has its OWN 3 attempts inside the loop's attempt

    WaitUntil(SomeExitCondition, 315, 8000);  // wait for the effect before the next iteration
  end;
end;
```

And the simplest pattern, `for...do...break`, for when you just want to "try N times, stop on first success":

```pascal
var i: Int32;
  success: Boolean;
begin
  for i := 1 to 3 do
  begin
    success := MyObject.WalkClick();
    if success then Break;
    Wait(SRL.TruncatedGauss(200, 600));  // short pause before the next attempt, avoid click spamming
  end;

  if not success then
  begin
    // All attempts failed — what now?
    // 1. Log clearly (with context: what we tried, what the uptext/state was at the time of failure)
    WriteLn('ERROR: could not interact with MyObject after 3 attempts. UpText was: ', MainScreen.GetUpText());
    // 2. Try an alternative plan if one exists (e.g. switch to another equivalent node/NPC/bank booth)
    // 3. If no alternative exists and this is critical to the script's continued execution: terminate in a controlled manner
    TerminateScript('MyObject interaction failed after retries — cannot continue safely.');
  end;
end;
```

Three principles:
1. **Never an infinite loop without a pause** — always put a `Wait()` between attempts, otherwise you'll either spam-click or burn CPU in a tight loop while nothing changes (which is also a bot-detectable pattern).
2. **Escalate on the last attempt** — several of the scripts reviewed rotate the camera (`Minimap.SetCompassAngle`) or walk a short distance (`WebWalkEx`) specifically on the last attempt in a loop, since if the earlier attempts failed for visibility reasons, a simple retry won't fix the problem.
3. **Give up clearly** — if all attempts fail: log with enough context to debug afterward (what was attempted, what the uptext/state was), and either (a) switch to an alternative plan, or (b) terminate the script in a controlled manner (`TerminateScript`/`Self.Fatal`) instead of continuing blindly in an unknown state.

---

## 7. Common pitfalls

**1. Blindly trusting a left click when the action is context-dependent.**
Concrete real bug we ran into: rune pouches (and similar items) dynamically toggle between "Fill"/"Empty" on left click depending on the game's state (the 2025 update). Solution: hover, verify with `IsUpText`, only click on a match (see section 2). The same risk class applies to doors (Open/Close), certain machines (Start/Stop), and NPCs whose default action changes depending on quest progress.

**2. Clicking without waiting for the previous animation/movement to finish.**
If you `Mouse.Click()` a new target while the player is still mid-movement or mid-animation from a previous action, the click can land on the wrong uptext (the player hasn't gotten where you think, or an interface is about to open/close). Wait for a clearly finished state before the next interaction, e.g.:
```pascal
WaitUntil(not Minimap.IsPlayerMoving(), 100, 5000);
// or specifically for animations/skills, depending on the interface
```
Just inserting a fixed `Wait(2000)` "to be safe" works but is both slow and not robust to variation — prefer `WaitUntil` against a concrete condition when one is available.

**3. Not handling a ChooseOption menu that was already open from a previous interaction.**
If a previous step left a context menu open (e.g. a failed attempt, or the player right-clicked by mistake) and you then try to hover/click a new target, the menu interferes with everything — the mouse movement happens "behind" or "through" the menu. SRL-T's own `Hover`/`_HoverHelper` handles this automatically (checks `ChooseOption.IsOpen()` first), but if you write your own low-level click code, you must check this yourself in your state machine, exactly as in `wasp_blast_furnace.simba`/`wasp_herblore.simba`:
```pascal
if ChooseOption.IsOpen() then
  Exit(EMyState.CLOSE_CONTEXT_MENU);  // handle this as its OWN state, before anything else
// ... and in the execution:
EMyState.CLOSE_CONTEXT_MENU: ChooseOption.Close();
```
Make this the FIRST check in your `GetState()` function, not an afterthought.

**4. Forgetting to verify the click afterward too, not just before.**
`MainScreen.DidRedClick(time)` determines whether the click gave red (valid) or yellow/no (invalid) feedback. The uptext check before tells you what the click WILL do; `DidRedClick` after confirms it WAS ACTUALLY registered by the client (the mouse may have landed on the wrong pixel, the object may have disappeared right before the click, etc.). Both checks are needed — see `TMSObject.Interact` in section 4 for an example that does both.

**5. Too high `Mouse.MissChance`/too aggressive humanization on narrow target areas.**
The default `MissChance := 15` is fine for large mainscreen objects but can cause you to miss a 15px-tall row in a `ChooseOption` menu. This is exactly why SRL-T's own `ChooseOption.Select` temporarily zeroes `MissChance`/`IdleInterval` on a `tmpMouse` copy for that specific click (see section 1). Do the same yourself for other narrow target areas (e.g. spell icons, small interface buttons).

**6. Assuming `Find`/`IsVisible` returns the same result repeatedly within the same frame without re-hovering.**
If the camera rotates or the player moves between a `Find()` call and a later `Click()`, the coordinates may be stale. Prefer the composite methods (`Click`/`WalkClick`) that perform `Find`+hover+click as one continuous sequence, rather than caching the result of an earlier `Find()` and clicking on it much later.

---

## 8. Checklist before writing interaction code in a new script

1. **Does a `TRSObjectV2`/`TRSNPCV2` (or an `RSObjects.Get(...)` entry) already exist for the target?** If yes — use `.Click`/`.WalkClick`/`.SelectOption` directly. Don't write your own `Mouse.Move`+`IsUpText`+`Mouse.Click` code for something the library already solves.
2. **Is the click's meaning context-dependent?** (item may be full/empty, object may be on/off, NPC's default action may vary) — if yes, hover-verify-click manually with `IsUpText` before clicking; don't rely on the default left click. See section 2 and pitfall 1.
3. **Do I need a specific right-click option rather than the default action?** — use `ChooseOption.Select(['text'])` or `.SelectOption(['text'])` on the object/NPC, not a manual right-click+OCR.
4. **Do I have a retry loop with a reasonable number of attempts (2-5 normally) and a `Wait()` between each?** No infinite loops, no tight spam loop without a pause.
5. **What happens if all attempts fail?** Decide explicitly: log + alternative plan, or log + controlled termination. Don't leave the script in an undefined state.
6. **Does my state machine check for an already-open `ChooseOption` menu FIRST, before any other logic?** (if the script is built on a state machine rather than `TRSMapObject`'s built-in handling)
7. **Do I also verify the click afterward** (`MainScreen.DidRedClick`) when writing low-level click code manually, not just beforehand (uptext)?
8. **Are the humanization settings (`Mouse.Speed`/`MissChance`/`Distribution`/`CanIdle`) set once globally at start**, and only temporarily overridden via a `tmpMouse` copy for narrow target areas (menus, small buttons) — not permanently reconfigured mid-script?
