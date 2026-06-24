# How an OSRS bot script in Simba/WaspLib is structured

This file is a structural guide based on:
- `aeroguardians (4).simba` (older style, rev 21) and `aeroguardians.simba` (modern style, rev 38) — two generations of a GotR (Guardians of the Rift) example script that we debugged together (not included in this repository)
- `bigaussie_gemstone_crab_slayer.simba` — a combat script we reviewed for antiban ideas (not included in this repository)
- Official templates and documentation from [WaspLib](https://github.com/torwent/wasplib) and [docs.waspscripts.dev](https://docs.waspscripts.dev/)

The purpose is to have a shared reference for when we later write a new script from scratch.

---

## 1. Bird's-eye view: Simba, SRL-T, and WaspLib

Three layers, in dependency order:

1. **Simba** – the program/IDE itself and the script engine ("Lape", a Pascal-like language). Provides the base types (`TPoint`, `TBox`, `TPointArray`...), input simulation (`Mouse`, `Keyboard`), image analysis (`FindColors`, `FindDTM`, etc.), and plugins (e.g. OCR via `libsimpleocr`).
2. **SRL-T** (`{$I SRL-T/osr.simba}`) – the community library layered on top of Simba: game-specific "interfaces" (`Inventory`, `Chat`, `Bank`, `Minimap`, `GameTabs`...), `TAntiban`, `TRSWalker`, login handling, etc. **Correction:** even the modern map system (`Map`, `TRSMap`, `TRSMapChunk`, `Objects`, `TRSObjectV2`, `TRSNPCV2`) actually lives in SRL-T (`osr/map/*.simba`), not WaspLib as this file previously stated — verified directly against the source code. SRL-T is the foundation all OSRS scripts build on.
3. **WaspLib** (`{$I WaspLib/osr.simba}`) – Torwent's library on top of SRL-T. Adds `TBaseScript`/`TBaseBankScript`/`TBaseWalkerScript` (ready-made script skeletons), `TScriptForm` (GUI framework), `TConfigJSON` (saved settings), webhooks, a statistics API, and extra interfaces/handlers (farming, birdhouses, teleports, etc.) on top of SRL-T's base system.

A script almost always includes both, in this order:

```pascal
{$I SRL-T/osr.simba}
{$I WaspLib/osr.simba}
```

(In older scripts like `aeroguardians (4).simba`, it is sometimes enough to include just `{$I WaspLib/osr.simba}`, since WaspLib itself includes SRL-T internally when needed — but explicitly including both is more common in newer scripts.)

---

## 2. Anatomy of the file (the top of the script)

Almost all scripts start with the same pattern:

```pascal
{$UNDEF SCRIPT_ID}{$DEFINE SCRIPT_ID := 'd367e87f-...'}
{$UNDEF SCRIPT_REVISION}{$DEFINE SCRIPT_REVISION := '38'}
program AeroGuardians;
{$DEFINE SRL_USE_REMOTEINPUT}
{$IFDEF WINDOWS}{$DEFINE SCRIPT_GUI}{$ENDIF}
{$I WaspLib/osr.simba}
```

- `SCRIPT_ID`/`SCRIPT_REVISION` – used for statistics/update checks against the WaspScripts API (`APIClient`).
- `SCRIPT_GUI` – a conditional compile flag (`{$IFDEF SCRIPT_GUI}...{$ENDIF}`) that wraps the entire GUI code, so the script can in theory run headless if the flag is removed.
- `SRL_USE_REMOTEINPUT` – turns on "RemoteInput", SRL's way of simulating real mouse/keyboard input at the OS level instead of Simba's built-in (more detectable) input simulation.

After this typically comes, in order:
1. `Const` – global settings (`NEAREND`, `FASTMODE`, `DEBUGMODE`, etc.) and static data (rune types, coordinate boxes).
2. `Type` – the script's own record types, most importantly **the script's main record** (see below).
3. `Var` – global instances, e.g. `Bot: TScript;`, `GUI: TGUI;`.
4. Lots of functions/procedures grouped by topic (setup, GUI, walking, mining, crafting, antiban, reporting...).
5. A closing `begin ... end.` that actually starts execution (shows the GUI and/or runs the script).

---

## 3. Two ways to build the script's "skeleton"

This is the most striking difference between rev 21 and rev 38 of aeroguardians, and worth understanding before we write anything new.

### 3a. The older, hand-built style (aeroguardians rev 21)

The script defines a completely custom record without inheriting anything from WaspLib:

```pascal
TScript = record
  Version: String;
  State: EState;
  ...
end;

var
  Bot: TScript;
```

All bookkeeping (time tracking, number of rounds won/lost, shutdown time, breaks/sleeps linkage) is handwritten. It works, but you have to reinvent things that already exist in WaspLib yourself (`TBaseScript`, for example, gives you `TimeRunning`, `ShouldStop()`, `DoAntiban()` for free).

### 3b. The modern style (aeroguardians rev 38, and all official templates)

The official `bank_script.simba` template shows the pattern WaspLib is built for:

```pascal
type
  EState = (
    WAIT_STATE,
    OPEN_BANK, WITHDRAW_ITEMS, DEPOSIT_ITEMS, ...
    OUT_OF_SUPPLIES, END_SCRIPT
  );

  TScript = record(TBaseBankScript)   // inherits TBaseBankScript -> TBaseWalkerScript -> TBaseScript
    State: EState;
  end;

function TScript.GetState(): EState;
begin
  if WL.Activity.IsFinished() then Exit(END_SCRIPT);
  ...
end;

procedure TScript.Run(maxActions: UInt32; maxTime: UInt64);
begin
  Self.Init(maxActions, maxTime);
  repeat
    Self.State := Self.GetState();
    Self.SetAction(ToStr(Self.State));
    case Self.State of
      WAIT_STATE: Wait(500, 800);
      OPEN_BANK: Bank.WalkOpen();
      ...
      OUT_OF_SUPPLIES, END_SCRIPT: Break;
    end;
    Self.DoAntiban();
  until Self.ShouldStop();
end;

var
  Script: TScript;
```

`record(TBaseBankScript)` means "inherit everything from `TBaseBankScript`". This gives you, for free:
- `Self.RSW` – a ready-made `TRSWalker`
- `Self.Init()` / `Self.ShouldStop()` – time-limit/action-limit handling
- `Self.DoAntiban()` – wires up the entire antiban system (tasks, breaks, sleeps) in one line
- Bank helpers: `Self.Withdraw()`, bank fields, collect-box support, etc.

**Conclusion for the next script:** start with `record(TBaseScript)` or `record(TBaseBankScript)`/`record(TBaseWalkerScript)` instead of a fully custom record. This saves a huge amount of handwritten code and avoids bug classes like "forgot to pause the right timer" (we saw exactly that kind of issue in `BreakPause`/`BreakResume` in the older aeroguardians).

---

## 4. The state machine pattern (the heart of the bot)

Both styles (and practically every WaspLib script) run the same base loop:

```
GetState() -> determines which state we're currently in, based on the game's state
Run()      -> repeat: GetState -> case statement that executes the state -> DoAntiban -> until ShouldStop
```

In `aeroguardians`, the states are e.g. `ENTER_GAME, WAITING, NEW_GAME, GATHER_FRAGMENTS, GATHER_ESSENCE, CRAFT_ESSENCE, CRAFT_RUNES, POWERUP, EXIT_ALTAR, CHANGE_WORLDS`. Each state corresponds to a function (`Self.HandleBarrier`, `Self.Mine('Fragments')`, `Self.CraftEssence`, `Self.CraftRunes`...) that does ONE thing and returns a `Boolean` for success/failure.

**Important lesson from our debugging:** each such state function usually has a long row of early-`Exit` conditions at the top (wrong state, game not logged in, wrong location, etc.) followed by the main logic. When adding something new (like pouch filling), you have to be *very* careful about **where in the order** it ends up — an `Exit`/`break` placed too early in a function permanently skips everything that comes after, even if it was only meant to skip one specific branch. That was exactly what caused the pouch bugs we chased.

---

## 5. Finding things in the game world

### Old style: `TMSObject` + local coordinates + `RSW` walker

```pascal
TMSObject = record
  Name: String;
  Colors: Array of TCTS2Color;
  UpText: TStringArray;
  Tile, WalkTile: TPoint;
end;
```
Position is read via a custom `RSW: TRSWalker` instance (`Self.RSW.GetMyPos`), and coordinates are small, "local" numbers (like `[265,218]`) that only have meaning within the script's own walker instance.

### New style: `TRSObjectV2`/`TRSNPCV2` + `Map`/`Objects`/chunks

```pascal
Obj_Workbench: TRSObjectV2;
...
Map.SetupChunk(GotR_Chunk);
Objects.Setup(Map.Objects, @Map.Walker);
Altar := Self.Altars.MapObjects.GetClosest;
Altar^.WalkClick(True, 3);
```
Position is read via the global `Map.Position` (real RuneScape world coordinates, 4-5 digits, e.g. `[7220,31038,...]`), and `Map`/`Objects` are **shared singletons** that all of WaspLib builds on (e.g. `Self.GetAltarLoc` in the new aeroguardians compares `Map.Position` against world-coordinate boxes).

**Why it matters:** the global `Map` system is more robust (pathfinding, collision data, the same map data all other WaspLib functions expect), whereas a custom `RSW` instance with local coordinates is an isolated island that has to be maintained separately. **Write new scripts against `Map`/`Objects`/`TRSObjectV2`, not against a custom walker type.**

---

## 6. Interacting: clicks, uptext, ChooseOption

Three levels of "clicking on something", from simplest to most robust:

1. **Direct click** – `Mouse.Click(box, MOUSE_LEFT)`. Only use this when you already know exactly what will happen.
2. **Hover + uptext verification** – move the mouse, check `MainScreen.IsUpText('Empty', 150)` (the yellow text in the top-left of the client that shows what a click *will* do), only click if the text matches expectations.
3. **Right-click + menu selection** – `ChooseOption.Select('Empty')` opens the right-click menu and selects an option via text matching.

**This was the entire core of the pouch bug saga:** since a 2025 game update, left-clicking rune pouches dynamically toggles between "Fill" and "Empty" depending on context. The working solution (rev 38) does **not** blindly trust that the left click does the right thing — it hovers first, reads the uptext, and only clicks if the uptext confirms the expected action:

```pascal
if Inventory.MouseItem(Pouches[i]) then
begin
  if Empty then
    if Mainscreen.IsUpText('Empty', 150) then
    begin
      Mouse.Click(MOUSE_LEFT);
      Result := True;
    end;
  ...
end;
```

**General rule for the next script:** whenever a game action might be context-dependent or ambiguous (dynamic clicks, items that change appearance/name, NPCs with multiple dialogue options), verify with uptext or `ChooseOption` before clicking instead of guessing.

---

## 7. Reading the game's state

Three main tools:

- **OCR** – `OCR.Recognize(box, TOCRColorFilter.Create([color], [tolerance]), Font)` for reading text/numbers in a fixed screen box (e.g. `Self.GetPower`, which reads the Guardian's Power meter, or `Chat.GetMessage`/`Chat.FindMessage` for chat lines).
- **Color detection** – `SRL.FindColors(TPA, CTS color filter, box)` for finding pixel clusters (e.g. `GetETypeRune`, which counts pixels of a certain color in a circle to determine which rune type an obelisk is set to).
- **Chat messages** – `Chat.FindMessage('text', [CHAT_COLOR_BLACK])`/`Chat.GetMessage(line, colors)` for failsafes ("out of ammo", "enough", "degraded", etc.) and for capturing important info (points from the "energy attuned" message in aeroguardians).

`CTS0`/`CTS1`/`CTS2` are SRL's color tolerance systems (0 = exact color, 1 = + color tolerance, 2 = + color and hue/saturation tolerance) — central to all image recognition in these scripts.

---

## 8. The antiban system

`Antiban` (a global `TAntiban` instance) has three layers:

1. **Tasks** – short, randomly scheduled behaviors: `Antiban.AddTask(ONE_MINUTE*7, @Antiban.RandomRotate);`. Run via `Antiban.DoAntiban()`/`Self.DoAntiban()`, which internally pauses and resumes all tasks' countdown timers around execution.
2. **Breaks/Sleeps** – longer pauses: `Antiban.AddBreak(interval, length, ...)`, `Antiban.AddSleep(...)`. Also triggered via `DoAntiban(checkBreaks, checkSleeps)`.
3. **Biometrics** – a per-account "personality" (`Antiban.SetupBiometrics`/`BioWait`/`BioDice`) that provides consistent but individual timing variation, so that not every run of the same script looks identical.

Important overridable hooks (set in `procedure TAntiban.Setup(); override;` or standalone override functions):
- `OnStartTask`/`OnFinishTask` – run extra logic around each task (e.g. the aeroguardians variant of the crab slayer script checks that the mouse hasn't ended up on a dangerous button after a task).
- `OnStartBreak`/`OnFinishBreak`/`OnStartSleep`/`OnFinishSleep` – pause/resume custom timers.
- `RandomChatTask` – can be overridden to a no-op if you want to disable chat-tab toggling (we did this in aeroguardians to avoid risking filtering out chat messages that the script's own failsafes read).

**Lesson:** WaspLib's default antiban (`WLSettings.json`, antiban tasks: camera/mouse/chat/gametabs/bank = `true` by default) is **already active** even if you don't add any tasks yourself — if you want to disable something specific, you must explicitly override that method, otherwise it runs in the background regardless.

---

## 9. GUI and settings

The modern style uses `TScriptForm` (base class) + a custom `record(TScriptForm)` (`TConfig`/`TGUI`), with ready-made building blocks:

```pascal
Self.CreateAccountManager(tab);     // account management
Self.CreateAntibanManager();        // antiban settings
Self.CreateBankSettings();          // bank settings
Self.CreateWaspLibSettings();       // global WaspLib settings
Self.CreateAPISettings();           // WaspScripts API/statistics
```

Custom fields (checkboxes, text fields) are created manually with `.Create(parent)`, `.SetCaption(...)`, `.SetLeft/.SetTop` (often DPI-scaled via `TControl.AdjustToDPI(...)`).

**Two ways to save settings between runs**, seen in our scripts:
- Older: manual INI reading/writing (`ReadINI`/`WriteINI` against a custom `.ini` file), as in the crab slayer script's `LoadUserSettings`/`SaveUserSettings`.
- Newer: `TConfigJSON` (`Self.Config.Setup('name'); Self.Config.Put('key', value); Self.Config.GetBoolean('key')`), as in aeroguardians rev 38. Simpler and less code.

For a new script: use `TConfigJSON` — that's the direction WaspLib is heading.

---

## 10. Inventory/Bank interaction

The most common building blocks:
- `Inventory.ContainsItem`/`ContainsAny`/`CountItem`/`CountItemStack`/`FindItem`/`FindItems`
- `Inventory.ClickItem(item, [option])` – left-click if `option` is empty, otherwise right-click + menu selection
- `Inventory.MouseItem(item)` – just hover, no click (for uptext verification, see section 6)
- `Inventory.ShiftDrop(slots, pattern)` – shift-click multiple slots in sequence (for items where shift-click = a specific quick action, e.g. drop)
- `Bank.WalkOpen`/`DepositAll`/`FindItem`/`WithdrawHelper`/search-field handling (`Bank.OpenSearch`, typing letter by letter with `Keyboard.Send`)

---

## 11. Robustness: error handling, logging, reporting

Consistent pattern across all scripts we've seen:
- `if DEBUGMODE then Self.WriteMsg('...');` – simple, conditional logging. `WriteMsg` is usually just a `WriteLn` wrapper with a prefix tag (`[Bot]:`).
- `TerminateScript('reason')` – hard stop with a clear error message, often after `Logout.ClickLogout` so as not to leave the account logged in and visible.
- `Self.TakeScreenshot('name')` – saves a screenshot on critical errors (degraded equipment, out of resources), useful for debugging after the fact.
- Discord webhooks (`Discord.Webhook.Content := '...'; Discord.SendScreenshot(False);`) – optional external notification on critical events, seen in the crab slayer script.
- `Self.CheckMessages` / `Self.Report` – a paired pattern: one function that checks whether something "reportable" has happened (chat message, round complete) and one that prints/logs the status.

---

## 12. Lesson from our debugging: the pouch bug saga in brief

A good example of why you must read *exactly* what the code does, rather than assume:

1. The game was updated so that left-clicking rune pouches dynamically selects Fill/Empty.
2. My first fix assumed that blindly left-clicking is now always correct → worked sometimes, not 9/10 times.
3. The actual solution (verified against a purchased, working version) was to **not trust the assumption** — instead determine Fill/Empty based on **where the player actually is** (`InRange(Self.GetAltarLoc, TYPEAIR, TYPEBLOOD)`) and **verify with uptext before clicking**.
4. A second, completely separate bug (the ordering between "no more fragments → Exit" and pouch filling) turned out to exist in **both** versions (the old one and the purchased, working one) — so it was probably never the actual culprit, even though it looked like a likely candidate on static reading.

**General lesson:** with this type of bot script, it's easy to find code that *looks* wrong on a read-through but in practice doesn't matter (or the reverse: code that looks correct but isn't, because you're missing the game's actual, context-dependent behavior). Compare against a known-working reference whenever possible, and be skeptical of your own "it must be here" theories until they're confirmed.

---

## 13. Recommended workflow for a new script

1. Decide which `TBase...Script` variant fits (`TBaseScript` for simple activities, `TBaseWalkerScript` if there's a lot of walking, `TBaseBankScript` if it banks regularly).
2. Copy the closest official template (`templates/bank_script.simba` or `templates/walker_script.simba` in the WaspLib repo) as a starting point instead of starting from a blank file.
3. Define `EState` for the activity and write `GetState()` before filling in the `Run()` case statement — think through states and transitions on paper first.
4. Set up `Map.SetupChunk(...)` + `Objects.Setup(...)` for the location, and define your `TRSObjectV2`/`TRSNPCV2` for the objects/NPCs you need to interact with.
5. Build individual "action" functions (one per state) that each do ONE thing and return a `Boolean`. Put early exits at the top, but pay attention to the order (section 4).
6. Add antiban (`Self.DoAntiban()` calls in the main loop, possibly custom `Antiban.AddTask`/overrides).
7. Build the GUI last, using `TConfigJSON` to save settings, and reuse `CreateAccountManager`/`CreateAntibanManager`/`CreateBankSettings`/`CreateAPISettings`.
8. Test each state in isolation where possible before trusting the full loop.

---

## 14. References

- [WaspLib on GitHub](https://github.com/torwent/wasplib) – source code, folder structure (`osr/`, `optional/`, `utils/`, `tools/`, `templates/`)
- [WaspLib documentation](https://docs.waspscripts.dev/) (also mirrored at [torwent.github.io/WaspLib](https://torwent.github.io/WaspLib/))
- [BaseScript documentation](https://torwent.github.io/WaspLib/basescript.html) – `TBaseScript`/`TBaseWalkerScript`/`TBaseBankScript`
- [TRSObjectV2 Finding & Usage (tutorial)](https://waspscripts.com/tutorials/trsobjectv-finding-and-usage-by-goobtacular)
- [Introduction to development (tutorial)](https://waspscripts.com/tutorials/introduction-to-development-by-torwent)
- [WaspScripts Discord](https://waspscripts.com) – community support, often faster than digging through the documentation yourself
- Locally: `%LocalAppData%\Simba\Includes\SRL-T` and `...\WaspLib` (path typical for a Windows installation) – read the source code directly, it is usually more up to date and precise than the prose documentation.
