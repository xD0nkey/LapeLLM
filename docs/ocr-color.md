# OCR and color detection in SRL-T / WaspLib

This is a self-instruction: when image-recognition code (OCR or color detection) needs to be written
for an OSRS bot script in Simba/Lape, read this file FIRST and copy the patterns from here
instead of guessing signatures. See `script-anatomy.md` for how a complete script is structured
(includes, TBaseScript, etc.) — this file goes deeper specifically on the image-analysis part.

Everything verified against actual source code in (path typical for a Windows installation):
- `%LocalAppData%\Simba\Includes\SRL-T\osr\ocr\ocr.simba`
- `%LocalAppData%\Simba\Includes\SRL-T\utils\math\color.simba`
- `%LocalAppData%\Simba\Includes\SRL-T\utils\geometry\tpointarrays.simba`
- `%LocalAppData%\Simba\Includes\SRL-T\utils\wrappers.simba`
- as well as concrete usages in roughly 20 WaspLib scripts and two example scripts ("aeroguardians",
  "gemstone crab slayer") that were examined during the research but are not included in this repo.

---

## 1. Basic OCR pattern

The OCR instance is called `OCR` (global, declared in `ocr.simba`, type `TSimpleOCR`).
It is loaded via a plugin (`{$loadlib ../../plugins/libsimpleocr/libsimpleocr}`),
which means that `TSimpleOCR` and `TOCRColorFilter` are NOT Lape source code I can
read line by line in SRL-T — their exact internal implementation lives in a
compiled plugin. I learn the signatures from how existing code USES them, not
from finding the class declaration.

The basic pattern for reading text from a fixed screen box:

```pascal
var
  s: String;
begin
  s := OCR.Recognize(box, TOCRColorFilter.Create([color]), RS_FONT_X);
end;
```

`TOCRColorFilter.Create` takes:

```pascal
TOCRColorFilter.Create([color1, color2, ...]);
TOCRColorFilter.Create([color1, color2, ...], [tolerance1, tolerance2, ...]);
```

- First array: one or more colors (decimal int or `$RRGGBB` hex) that the text
  can have. Multiple colors are used when the text has antialiasing/shading or can appear
  in more than one color (e.g. white OR yellow depending on state).
- Second array (optional): matching tolerances, one per color, in the SAME order. If it
  is omitted, a built-in default tolerance is used.

Example from real code (`login.simba`, `antiban.simba`):

```pascal
// One color, no explicit tolerance:
Self.WhiteOCRFilter  := TOCRColorFilter.Create([$FFFFFF]);
Self.YellowOCRFilter := TOCRColorFilter.Create([$00FFFF]);

// Two elements in the same array = [color, tolerance] for ONE color:
OCR.LocateText(B, Name, RS_FONT_BOLD_12, TOCRColorFilter.Create([$00FFFF, 0]), 0.85);

// Multiple colors at once (e.g. world list that can be white or gray):
OCR.RecognizeNumber(ListBox, TOCRColorFilter.Create([61680, 14737632]), RS_FONT_PLAIN_12);
```

Note that `TOCRColorFilter.Create([$00FFFF, 0])` above does NOT mean "two
colors" — there, `0` is the tolerance for the single color `$00FFFF` written as a flat
array. Both forms (`[color, tolerance]` flat, and `[colors...], [tolerances...]`
as two separate arrays) occur in the codebase. The safest approach is to copy exactly the same
form that similar existing code for the same part of the UI uses.

### Fonts (`RS_FONT_*`)

Declared in `ocr.simba`, loaded from files in `SRL-T/osr/ocr/fonts/`:

| Constant                  | Typical usage (observed in the codebase) |
|---------------------------|---------------------------------------------|
| `RS_FONT_PLAIN_11`        | Item stack counts, small numbers, GE prices, login fields |
| `RS_FONT_PLAIN_12`        | General interface text (chat reply text, GE search results, item names in lists) |
| `RS_FONT_BOLD_12`         | Chat dialog names/headers, GE titles, world numbers, bank PIN digits |
| `RS_FONT_BOLD_12_SHADOW`  | Bold text with shadow (less commonly used directly in scripts) |
| `RS_FONT_QUILL_8`         | Quest/dialog-like text in the chatbox (NPC dialog), combat level text, skill names in the stats tab |
| `RS_FONT_QUILL`           | Larger variant of Quill, used less often |

Which font is "correct" is in practice **trial-and-error or copied from
existing code that reads the same UI element**. There is no reliable
general rule ("chatbox = Quill, interface = Plain") — for example, both
`chat.simba` and `stats.simba` use `RS_FONT_QUILL_8` for text in their respective boxes,
while `RS_FONT_PLAIN_12`/`RS_FONT_BOLD_12` are used broadly across GE, login, and
gametabs. When writing new code: search the SRL-T/WaspLib source for OCR calls against
the same UI surface (e.g. grep for the same interface name) and reuse that font.

---

## 2. `Recognize` vs `RecognizeNumber` vs `RecognizeLines` vs `LocateText`

All four exist as methods on the `OCR` instance (`TSimpleOCR`):

```pascal
function TSimpleOCR.Recognize(box: TBox; filter: TOCRColorFilter; font: TFontSet): String;
function TSimpleOCR.RecognizeNumber(box: TBox; filter: TOCRColorFilter; font: TFontSet): Int32;
function TSimpleOCR.RecognizeLines(box: TBox; filter: TOCRColorFilter; font: TFontSet): TStringArray;
function TSimpleOCR.RecognizeLines(box: TBox; filter: TOCRColorFilter; font: TFontSet; out boxes: TBoxArray): TStringArray;
function TSimpleOCR.LocateText(box: TBox; text: String; font: TFontSet; filter: TOCRColorFilter; minMatch: Single): Int32;
```

- **`Recognize`** — reads ONE line of text, returns `String`. Use when you know that
  the box contains exactly one line of text (item name, dialog header, a single button label).
- **`RecognizeNumber`** — reads an integer directly as `Int32`, avoiding manual
  `StrToInt`/parsing. Use for stack counts, prices, world numbers, XP, etc.
  Example (`misc.simba`, item stack count with color coding for k/M suffixes):
  ```pascal
  Result := OCR.RecognizeNumber(area, TOCRColorFilter.Create([RS_ITEM_YELLOW_STACK]), RS_FONT_PLAIN_11);
  ```
- **`RecognizeLines`** — reads MULTIPLE lines at once, returns `TStringArray`
  (one string per line). There is an overload that also outputs a `TBoxArray` with
  the box for each line found (`out Boxes: TBoxArray`) — use that one when you subsequently
  need to click on a specific line, e.g. a search result in the GE list:
  ```pascal
  Strings := OCR.RecognizeLines(Self.Bounds, TOCRColorFilter.Create(colors), RS_FONT_QUILL_8, Boxes);
  ```
- **`LocateText`** — use when you ALREADY KNOW which text you're looking for and just
  want to know IF it exists and WHERE. Returns the number of matches (`Int32`, 0 if nothing
  was found), and can take an `out`/`var` box to get back where the match is located:
  ```pascal
  Result := OCR.LocateText(Self.Bounds, ToString(World), RS_FONT_BOLD_12, TOCRColorFilter.Create([$000000]), B) = 1;
  ```
  The last parameter (e.g. `0.85` or `1`) is `minMatch` — how exact the match
  must be (1 = exact, lower = more lenient for e.g. player names that may have
  varying capitalization/special characters).

Rule of thumb: if you know EXACTLY what the text should be → `LocateText`. If you want to read
UNKNOWN content (a name, a price, an amount) → `Recognize`/`RecognizeNumber`/`RecognizeLines`.

---

## 3. Color detection: CTS0 / CTS1 / CTS2

Defined in `SRL-T/utils/math/color.simba`:

```pascal
function CTS0(Color: Int32; Tolerance: Int32 = 0): TCTS0Color;
function CTS1(Color, Tolerance: Int32): TCTS1Color;
function CTS2(Color, Tolerance: Int32; HueMod: Double = 0.2; SatMod: Double = 0.2): TCTS2Color;
```

- **`CTS0(color, tolerance)`** — exact color match + a simple numeric tolerance
  (RGB distance). Fastest, but most sensitive to light/shadow variation. Good for
  fully static UI elements (interface text, fixed icons) where the color is always
  identical pixel-for-pixel.
  ```pascal
  if SRL.CountColor(CTS0(766, 0), Self.BossInterface.Brazier.Current) > 0 then ...
  ```
- **`CTS1(color, tolerance)`** — same as CTS0 but with a different/broader
  tolerance calculation ("color tolerance", more forgiving toward antialiasing pixels at
  the edge of an object). Use when CTS0 misses pixels due to slight edge smoothing.
  ```pascal
  if SRL.FindColors(tpa, CTS1(39167, 0), b) = 0 then ...
  ```
- **`CTS2(color, tolerance, hueMod, satMod)`** — the most robust variant: matches
  in HSV space, so `hueMod` (hue tolerance) and `satMod` (saturation tolerance) let
  it handle lighting differences (e.g. the same NPC in sun vs shadow, water with
  rippling light reflections) much better than CTS0/1. This is the default for
  object/NPC colors on the mainscreen in modern scripts (`aerofisher`, `wasp_blast_furnace`,
  `wasp_wintertodt` have dozens of examples):
  ```pascal
  FlyingFishCol := CTS2(10983034, 8, 0.09, 1.10);
  Self.Brazier.Finder.Colors := [CTS2(6051923, 23, 0.33, 0.16), CTS2(5562530, 23, 0.17, 1.21)];
  ```
  In practice, the `hueMod`/`satMod` values are derived using Simba's Color Picker tool
  (see the checklist below) rather than calculated by hand.

The most common calls that take a CTS color:

```pascal
function TSRL.FindColors(out TPA: TPointArray; Color: TCTS0Color/TCTS1Color/TCTS2Color; Area: TBox): Int32;
function TSRL.CountColor(Color: TCTS0Color/TCTS1Color/TCTS2Color; Area: TBox): Int32;
```

`SRL.FindColors(out TPA, filter, box)` gives you ALL matching pixels as a
`TPointArray` — use when you need the positions (to click, calculate the
mean point, filter further). `SRL.CountColor(filter, box)` gives only the NUMBER of
matching pixels — use when you just want to know "is the color there?" or "how
much of this color is present?" (e.g. a power/progress meter), without caring
exactly where they are located. `CountColor` is internally just `FindColors` that discards
the TPA, so `FindColors` is never "more expensive" to use if you already have the TPA
lying around somewhere — but write `CountColor` when the TPA is never needed, it makes
the code clearer.

There are also global (non-CTS) shortcuts `CountColor(color, box)` and
`CountColorTolerance(color, box, tol)` in `wrappers.simba` — an older/simpler API without
CTS objects, roughly equivalent to `SRL.CountColor(CTS0(color, tol), box)`. Newer code
prefers SRL.FindColors/CountColor with an explicit CTS object because it is
self-documenting which CTS level is being used.

---

## 4. Filtering noise out of a `TPointArray`

After `SRL.FindColors` you often get more points than you want (background noise,
other objects with a similar color). The most common filters:

```pascal
function TPointArray.FilterDist(MinDist, MaxDist: Double; Mx, My: Int32): TPointArray; constref;
function TPointArray.FilterBox(b: TBox): TPointArray; constref;
procedure FilterPointsBox(var TPA: TPointArray; x1, y1, x2, y2: Int32);   // mutates TPA in place
procedure FilterPointsDist(var TPA: TPointArray; MinDist, MaxDist: Double; Mx, My: Int32); // mutates in place
```

`FilterDist`/`FilterPointsDist` is a **circle filter**: keeps only points
whose distance from `(Mx, My)` is between `MinDist` and `MaxDist`. Typical
usage: only counting pixels within a circle around the player/minimap center (a
round "meter" or radius check), or conversely filtering out everything WITHIN a
radius (e.g. excluding the player's own character from an NPC search).

Concrete example — check if a "portal" is active by counting the exact number of
color pixels within the player's circle (`aeroguardians (4).simba`):

```pascal
function TScript.IsPortalActive(): Boolean;
var
  Col: TCTS2Color := CTS2(3785983, 17, 0.06, 0.01);
  TPA: TPointArray;
begin
  if SRL.FindColors(TPA, Col, Self.PCircle.Bounds) > 0 then
  begin
    TPA    := TPA.FilterDist(0, Self.PCircle.Radius, Self.PCircle.X, Self.PCircle.Y);
    Result := TPA.Len = 267;  // exact pixel count == "ground truth" for active portal
  end;
end;
```

Note the pattern: search within a large `.Bounds` (rectangle, cheap), then filter
down to an exact circle with `FilterDist` (the circle test is more expensive per pixel,
so it's done AFTER the simple rectangle boxing, not instead of it).

Another common pattern — finding the center of a rock/NPC cluster and picking only
points near the center (for natural mouse hovering), `gem_miner (1).simba`:

```pascal
middle := tpa.Mean();
filteredTPA := tpa.FilterDist(0, 8, middle.X, middle.Y);
Mouse.Move(filteredTPA.RandomValue);
```

`FilterBox`/`FilterPointsBox` is the same idea but with a rectangle (`TBox`) instead
of a circle — use when only an axis-aligned area is relevant, e.g. "remove
all points within the player's own tile" (`aeroguardians`):

```pascal
FilterPointsBox(DelTPA, 1, 1, Self.PBox.X2, Self.PBox.Y2);
ResTPA := ClearTPAFromTPA(TPA, DelTPA);  // TPA minus DelTPA
```

---

## 5. DTM (`FindDTM`/`FindDTMs`/`DTMFromString`)

DTM ("Deformable Template Match") is a bitmap-like template that matches a
specific visual shape (e.g. an NPC's minimap dot or icon) regardless of minor
color/position variation. You practically NEVER write a DTM string by
hand — it is generated with Simba's built-in **DTM Editor** tool (opened from
the Simba IDE, you paint/click out the template against a screenshot), which spits out a
base64-like string. That string is pasted into the code and loaded with:

```pascal
function DTMFromString(const Str: String): Int64;
```

The signatures for the search itself (from `SRL-T/utils/wrappers.simba`):

```pascal
function FindDTM(const DTM: Integer; var x, y: Integer; const SearchBox: TBox): Boolean;       // ONE match, outputs x,y
function FindDTMs(const DTM: Integer; var TPA: TPointArray; const SearchBox: TBox): Boolean;    // ALL matches, outputs TPA
```

**MUST always be followed by `FreeDTM(dtmHandle)`** when you're done — `DTMFromString`
allocates memory in the Simba engine that is not cleaned up automatically. If you forget this,
the memory leaks every time the function is called (in a long bot run this can become
thousands of unreleased DTMs). The standard pattern is `try...finally` so that
`FreeDTM` always runs even if the search throws an error:

Real example, `bigaussie_gemstone_crab_slayer (3).simba` — a custom
NPC detector that looks for 7 different DTM variants of the same minimap dot
(the NPC can look slightly different depending on direction/animation), merges all
matches, and manually filters out duplicates (points closer to each other than 8px count as
the same dot):

```pascal
function GetEnhancedNPCDots(): TPointArray;
const
  NPC_DTM1: Int64 := DTMFromString('mQwAAAHicY2ZgYGhnguAOIA4G8kOBOASI374FEgyMUIwAjKiiANXeBHs=');
  NPC_DTM2: Int64 := DTMFromString('mQwAAAHicY2ZgYKhnguA6IA4A8gMZIPTdu0CCgRGKEYARVRQAyRcENg==');
  // ... NPC_DTM3..NPC_DTM7 likewise
var
  TempPoints, AllPoints: TPointArray;
  SearchArea: TBox;
  I, J: Integer;
  TooClose: Boolean;
begin
  Result := [];
  SearchArea := Minimap.Bounds.Expand(-15);

  try
    if FindDTMs(NPC_DTM1, TempPoints, SearchArea) then AllPoints := AllPoints + TempPoints;
    if FindDTMs(NPC_DTM2, TempPoints, SearchArea) then AllPoints := AllPoints + TempPoints;
    // ... same for DTM3..DTM7

    for I := 0 to High(AllPoints) do
    begin
      TooClose := False;
      for J := 0 to High(Result) do
        if AllPoints[I].DistanceTo(Result[J]) < 8 then
        begin
          TooClose := True;
          Break;
        end;
      if not TooClose then
        Result := Result + [AllPoints[I]];
    end;
  finally
    FreeDTM(NPC_DTM1); FreeDTM(NPC_DTM2); FreeDTM(NPC_DTM3); FreeDTM(NPC_DTM4);
    FreeDTM(NPC_DTM5); FreeDTM(NPC_DTM6); FreeDTM(NPC_DTM7);
  end;
end;
```

Note: `NPC_DTM1` etc. are declared as `const ... : Int64 := DTMFromString(...)`
directly in the function's const section — they are thus created anew EVERY time
the function is called and freed in that same call's `finally`. This is a deliberate
trade-off (simplicity, no global state to keep track of) at the cost of
creating/freeing the DTMs over and over again. For DTMs used in a tight loop
(called hundreds of times per minute), it is more common to create them ONCE in
a global/`Setup` block and free them ONCE in the script's terminate handling,
instead of per-call.

DTM is a good choice when color detection (CTS0/1/2) is not sufficient — e.g. when the shape is
what matters (a specific minimap dot icon) rather than a single color click, or
when several different NPCs/objects have similar colors but different shapes.

---

## 6. How it's combined in practice — three examples

### a) Power/progress meter via color counting (state, not an exact number)

`wasp_wintertodt.simba` — the brazier's status is determined by counting specific
indicator colors in a fixed box, rather than by reading any number:

```pascal
function TWintertodt.GetBrazierState(): EBrazierState;
begin
  if SRL.CountColor(CTS0(766, 0), Self.BossInterface.Brazier.Current) > 0 then
  begin
    Self.Burning := False;
    Exit(EBrazierState.DEAD);
  end;

  if SRL.CountColor(CTS0(7829367, 0), Self.BossInterface.Brazier.Current) > 0 then
  begin
    Self.Burning := False;
    Exit(EBrazierState.BROKEN);
  end;

  if SRL.CountColor(CTS0(85981, 0), Self.BossInterface.Brazier.Current) > 0 then
    Exit(EBrazierState.LIT);

  Self.Burning := False;
  Result := EBrazierState.UNLIT;
end;
```

### b) OCR for a percentage value in a fixed box

Same script, HP/Warmth percentage is read as text and parsed apart with
`.ExtractNumber()` (string helper method in SRL-T) rather than `RecognizeNumber`,
because the string contains a `%` character that must be validated/stripped:

```pascal
function TWintertodt.GetWarmth(): Int32;
var
  b: TBox;
  str: String;
begin
  b := Self.BossInterface.Warmth;
  b.X1 += 100;
  b.X2 -= 10;

  str := OCR.Recognize(b, TOCRColorFilter.Create([0]), RS_FONT_PLAIN_11);
  if Str.Contains('%') then Result := str.ExtractNumber(0);
end;
```

Note the box adjustment (`b.X1 += 100; b.X2 -= 10;`) — the original interface box
is wider than just the text field (it contains e.g. an icon or margin), so it is
trimmed before OCR is run, otherwise you risk reading garbage pixels into the result.

### c) Progress bar in pixel width (GE offer), with an explicit error value

`grandexchange.simba` — a progress bar is measured by the width of a contiguous
color TPA, converted to a percentage. Note the default value of 0 (no ground truth found
does not give an error, just an untouched `Result`) and a secondary check that sets -1
as an explicit error value when the bar is "full/overflow":

```pascal
function TRSGrandExchange.GetProgress(B: TBox; BarSize: Int32): Int32;
var
  TPA: TPointArray;
begin
  if SRL.FindColors(TPA, [1664168, 18944], B) then
    Result := Round(TPA.Bounds.Width() / BarSize * 100)
  else
  if SRL.CountColor(111, B) > BarSize then
    Result := -1;
end;
```

---

## 7. Common pitfalls

1. **The wrong font doesn't produce an error — it silently produces garbage or an empty string.**
   `OCR.Recognize` with the wrong `RS_FONT_*` does not throw any exception; it just
   matches poorly and returns `''` or partially incorrect text (e.g. "0" instead of
   "1000", or only every other character). If OCR "isn't working," try FIRST
   switching the font before suspecting the wrong box/color — that's the most common culprit.

2. **The box must be EXACTLY right, otherwise the wrong pixels are read.**
   A box that is 2px too wide can pick up a frame/icon edge that disrupts the
   color filter. A box that is 2px too narrow can cut off a digit. Copy
   exact box coordinates from similar existing code for the same UI element
   instead of guessing/measuring by hand in a screenshot tool — UI coordinates
   in OSRS are pixel-sensitive and vary with client size/layout mode
   (fixed/resizable/fullscreen).

3. **Handle empty/negative OCR results explicitly.** Many functions in
   the codebase deliberately set `Result := -1` (or let `Result` remain an
   unset default, often `0` for numeric types) precisely in order to distinguish
   "nothing found" from "found the value 0." ALWAYS write a check for this
   before using the return value further (`if value = -1 then ...`), otherwise
   a "nothing found" state sneaks in as a valid 0 value in your bot logic.

4. **`LocateText`/`FindColors` return the number of matches, not a boolean —
   but are often compared directly against a number.** `OCR.LocateText(...) = 1` is common
   for "exactly one match exists," but if you expect multiple matches (or
   don't know how many), you should check `> 0` instead, otherwise you miss
   valid cases where the text matches 2+ times.

5. **Don't forget `FreeDTM`.** See section 5 — every `DTMFromString` call without
   a matching `FreeDTM` is a memory leak. Use `try...finally`.

6. **CTS0 is fragile against light/shadow variations.** If a color detector works in
   some areas/times but not others (e.g. the same NPC in shadow), CTS0 is often
   the culprit — try CTS2 with a reasonable `hueMod`/`satMod` instead of just raising
   the tolerance on CTS0 (a higher tolerance on CTS0 tends to start matching TOO much,
   e.g. background colors, before it fixes the lighting problem).

7. **`TOCRColorFilter.Create([color, tolerance])` vs `Create([color1, color2])` look
   syntactically identical but mean completely different things** (one color plus its
   tolerance, versus two separate colors without an explicit tolerance). Always read
   how neighboring code in the same file uses the constructor before assuming which
   interpretation applies.

---

## 8. Checklist: new OCR/color code in a new script

1. **Identify the UI element** you need to read (which interface class/box does it
   belong to — gametab, mainscreen overlay, chatbox, etc).
2. **Search the SRL-T/WaspLib source** for existing code that already reads the same
   or a similar element (`grep` for the interface name or a nearby
   method). Reuse the font, CTS level, and box logic if something similar already exists
   — don't reinvent the wheel.
3. **Determine exact color values:**
   - Open Simba's built-in **Color Picker** (or the equivalent debug overlay in
     SRL-T, often accessible via SRL's debug image window) to click the pixel and
     read off the exact RGB/hex value, rather than guessing.
   - If a CTS2 detector is needed (object on the mainscreen with lighting variation), test
     it in Simba's DTM/Color tool or via a small test loop that prints
     `SRL.CountColor` for different `hueMod`/`satMod` combinations against a
     screenshot, until the match count is stable across multiple screenshots.
4. **Determine the exact box:** run a small debug procedure that draws the box
   (`box.Draw` or the equivalent SRL debug function) on top of a live screenshot
   to verify pixel-for-pixel that it encloses EXACTLY the text field/element
   and nothing else, before hooking up OCR.
5. **Write the reading function** with the correct `Recognize` variant (see section 2) and
   explicit handling of the "nothing found" case (section 7, item 3).
6. **If it's a DTM:** generate the template with the DTM Editor tool in the Simba IDE,
   paste in the string, and ensure `try...finally` with `FreeDTM`.
7. **Test in isolation** (a small standalone loop that just prints the
   result via `WriteLn`) before wiring the function into the bot's main loop —
   image-recognition bugs are much harder to debug when they are embedded in
   the rest of the bot logic.
