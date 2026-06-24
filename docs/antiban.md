# The Antiban system (`TAntiban`, SRL-T + WaspLib)

This file goes deeper into the antiban layer than `wasplib-script-anatomy.md` §8 (a short introduction there). The goal here: concrete recipes for adding, overriding, and debugging antiban behavior in a new script.

Sources this is based on: `SRL-T/osr/antiban.simba` (base implementation), `WaspLib/osr/antiban/antiban.simba` (overrides + default tasks), `WaspLib/utils/biometrics.simba` (BioHash/BioWait/BioDice), `WaspLib/Configs/wasplib.json` (default settings), as well as the reviewed scripts `aeroguardians (4).simba`/`aeroguardians.simba` (old hand-built style) and `bigaussie_gemstone_crab_slayer.simba` (rich, modern antiban code: world hopping, custom break overrides, `HandleFinishTask` safety check).

---

## 1. The basic flow: Tasks, Breaks, Sleeps and `DoAntiban`

`TAntiban` (global instance `Antiban: TAntiban`, defined in `SRL-T/osr/antiban.simba`) has three raw data types:

```pascal
TAntibanTask = record
  Method: TAntibanMethod;   // procedure of object, e.g. @Antiban.HoverSkills
  Interval: Double;
  StdVar: Double;           // "randomness" - relative standard deviation
  Countdown: TCountDown;
end;

TBreakTask = record
  Interval, Length, LogoutChance, StdVar: Double;
  NextAtTime, PrevAtTime: Double;
end;

TSleepTask = record
  Time: String;              // 'HH:MM:SS', TTimeFormat.Time_Bare
  Length, Randomness, LogoutChance: Double;
  NextAtTime: Double;
end;
```

You add them like this:

```pascal
// Interval in ms, Method = pointer to a procedure of object, Randomness = relative std. deviation (default 0.2)
Antiban.AddTask(15 * ONE_MINUTE, @Antiban.HoverSkills);
Antiban.AddTask(7  * ONE_MINUTE, @Antiban.RandomRotate, 0.33);

// Interval, Length in ms, Randomness (default 0.2), LogoutChance 0.0-1.0 (default 0.5)
Antiban.AddBreak(30 * ONE_MINUTE, 5 * ONE_MINUTE);                  // 30 min interval, 5 min break
Antiban.AddBreak(CUSTOMBREAKINTERVAL * ONE_MINUTE, CUSTOMBREAKDURATION * ONE_MINUTE, 0.33, 0.15);

// Time as 'HH:MM:SS', Length in ms, Randomness, LogoutChance
Antiban.AddSleep('01:30:00', 8 * ONE_HOUR, 0.1, 0.8); // approximately 01:30 runtime, sleeps ~8h, 80% chance of logging out
```

**None of this does anything by itself.** Tasks/breaks/sleeps are merely scheduled — they are ONLY triggered when you call:

```pascal
function TAntiban.DoAntiban(CheckBreaks: Boolean = True; CheckSleeps: Boolean = True): Boolean;
```

in the main loop, on a regular basis. Most commonly via the base class's shortcut:

```pascal
Self.DoAntiban();              // TBaseScript.DoAntiban -> Antiban.DoAntiban(True, True)
// or directly:
Antiban.DoAntiban(True, True);
```

**The most common beginner bug in the entire system: forgetting to call `DoAntiban` in the loop.** If you never call it, it doesn't matter how many `AddTask`/`AddBreak`/`AddSleep` calls you've set up — the countdown timers tick internally (`GetTimeRunning()`/`TCountDown`), but nothing actually *executes* until `DoAntiban` checks and triggers them. The standard pattern (see `templates/bank_script.simba`, `templates/walker_script.simba`):

```pascal
procedure TScript.Run(maxActions: UInt32; maxTime: UInt64);
begin
  Self.Init(maxActions, maxTime);
  repeat
    Self.State := Self.GetState();
    case Self.State of
      ... // handle state
    end;
    Self.DoAntiban();           // <-- once per loop iteration, always
  until Self.ShouldStop();
end;
```

You can temporarily disable breaks/sleeps during sensitive sequences with `Antiban.DoAntiban(False, False);` (only tasks run, no risk of a break triggering in the middle of, e.g., a bank transaction or combat) and then make a separate, full call `Antiban.DoAntiban;` (equivalent to `True, True`) at a safe point. This pattern appears throughout `aeroguardians.simba`:

```pascal
while Self.GetPower = 100 do
begin
  if not RSClient.IsLoggedIn then Exit;
  Antiban.DoAntiban(False, False);   // tasks only, no break in the middle of a power-wait
  WaitEx(300, 40);
end;
...
WaitEx(2500, 150);
Antiban.DoAntiban;                   // now OK for a full check (break/sleep may be triggered)
```

the same script also manipulates `NextAtTime` directly to nudge a break forward to a convenient point in time:

```pascal
if Self.TakeBreaks then
  if (Antiban.Breaks[0].NextAtTime - GetTimeRunning()) < 600000 then
    Antiban.Breaks[0].NextAtTime := GetTimeRunning(); // makes the break "ready now" instead of in 10 min, in the middle of the next round
```

---

## 2. WaspLib's default antiban is ON even if you do nothing

This is the most important insight in this entire file and a common source of misunderstanding.

`WaspLib/osr/antiban/antiban.simba` defines `procedure TAntiban.SetupTasks();`, which adds a whole set of tasks (camera, mouse, chat, gametabs, bank) **automatically**, controlled by `wasplib.json`:

```json
"antiban": {
  "tasks": { "camera": true, "mouse": true, "chat": true, "gametabs": true, "bank": true, "enabled": true },
  "sleep": { "enabled": false, "hour": "03:32:17", "length": "7.79", "biohash": true },
  "breaks": false
}
```

```pascal
procedure TAntiban.SetupTasks();
begin
  if Self.Tasks <> [] then Exit;   // <-- guard, see below

  if WLSettings.GetObject('antiban').getJSONObject('tasks').getBoolean('camera') then
  begin
    Self.AddTask(3  * ONE_MINUTE, @Self.AdjustZoom, 0.33);
    Self.AddTask(7  * ONE_MINUTE, @Self.RandomPOVTask, 0.33);
  end;
  if WLSettings.GetObject('antiban').getJSONObject('tasks').getBoolean('mouse') then
    Self.AddTask(8  * ONE_MINUTE, @Self.RandomMouseTask, 0.33);
  if WLSettings.GetObject('antiban').getJSONObject('tasks').getBoolean('chat') then
    Self.AddTask(9  * ONE_MINUTE, @Self.RandomChatTask, 0.33);
  if WLSettings.GetObject('antiban').getJSONObject('tasks').getBoolean('mouse') then
    Self.AddTask(10 * ONE_MINUTE, @Self.LoseFocus, 0.33);
  Self.AddTask(11 * ONE_MINUTE, @Self.RandomKeyboard, 0.33);
  if WLSettings.GetObject('antiban').getJSONObject('tasks').getBoolean('gametabs') then
    Self.AddTask(12 * ONE_MINUTE, @Self.RandomGameTabTask, 0.33);
  if WLSettings.GetObject('antiban').getJSONObject('tasks').getBoolean('bank') then
    Self.AddTask(13 * ONE_MINUTE, @Self.RandomBankTask, 0.33);
  if WLSettings.GetObject('antiban').getJSONObject('tasks').getBoolean('gametabs') then
    Self.AddTask(18 * ONE_MINUTE, @Self.HoverSkills, 0.33);

  Self.OnStartTask := @OnStartAntibanTask;
end;
```

**Note the default values in `wasplib.json`:** `tasks.enabled = true` and all subtasks (`camera`/`mouse`/`chat`/`gametabs`/`bank`) `= true`, but `breaks = false` and `sleep.enabled = false`. In practice this means: a script that doesn't touch the antiban settings at all automatically gets camera/mouse/chat/gametabs/bank antiban tasks, but NO breaks or sleeps unless the user enables it in the GUI (`CreateAntibanManager`).

`SetupTasks` is called from `procedure TAntiban.Setup();` (same file), which in turn is called once from `TBaseScript.Init` (`WaspLib/osr/basescript.simba`):

```pascal
procedure TBaseScript.Init(maxActions: UInt32; maxTime: UInt64);
begin
  ...
  if Self.IsSetup then Exit;
  Self.IsSetup := True;
  ...
  Antiban.Setup();   // runs ONCE, the first time Init is called
  ...
end;
```

**Consequence:** if your script is built on `TBaseScript`/`TBaseWalkerScript`/`TBaseBankScript` (recommended, see `wasplib-script-anatomy.md` §3b) you get WaspLib's default antiban tasks for free, without writing a single line of code. If you want to disable a specific category, there are two paths:

1. **Globally via settings** — set `wasplib.json`/the GUI (`WLSettings`) `antiban.tasks.chat = false`, etc. This is the intended path and requires no code.
2. **Override the method to a no-op** — if you want to disable exactly one task type in code (e.g., because it conflicts with the script's own chat reading), override the method it points to:

```pascal
// Disables ALL RandomChatTask activity, regardless of what the GUI/JSON says,
// because AddTask only stores a METHOD POINTER - it executes the actual
// code in the method when the countdown expires, and if the method is empty nothing happens.
procedure TAntiban.RandomChatTask(); override;
begin
  Exit;
end;
```

This pattern is exactly what `bigaussie_gemstone_crab_slayer.simba` does (with the comment "Disablechat antiban becaUse of chatbot and like who does this" — the chat tab must not be toggled away, because the script's own failsafes read the chat).

**The `if Self.Tasks <> [] then Exit;` guard in `SetupTasks` (and the corresponding one in `SetupBreaks`/`SetupSleep`):** this makes the methods idempotent — if `Self.Tasks` already contains something (e.g., because YOU already ran your own `Antiban.AddTask` calls BEFORE `Antiban.Setup()`/`SetupTasks()` ran), WaspLib's default list skips itself entirely. The call order therefore matters:

- If you put your own `AddTask` calls in a `procedure TAntiban.Setup(); override;` that calls `inherited` (which internally runs `SetupTasks`), your `AddTask` calls must come **before** `inherited` if you want the default list to be skipped entirely, or **after** if you want to add your own ON TOP of the default list.
- The official templates (`bank_script.simba`, `walker_script.simba`) place their customizations (`Self.Skills`, `MinZoom`/`MaxZoom`) before `inherited` and let the default tasks run as usual on top.
- If you want **only** your own tasks (none of WaspLib's defaults), either set all `wasplib.json` flags to `false`, or override `Setup` entirely without `inherited` (see the `herbiboar_hunter` example in §3) — but then you must remember the `Mouse.Speed`/`Gravity`/`Wind`/`MissChance` lines yourself, since they are otherwise set by the base `Setup`.

---

## 3. `procedure TAntiban.Setup(); override;` — your hook into the system

The usual, recommended place to configure antiban for your script. Runs once, automatically, from `TBaseScript.Init`.

Pattern A — **add on top of** WaspLib's defaults (most common, from `templates/bank_script.simba`):

```pascal
procedure TAntiban.Setup(); override;
begin
  Self.Skills  := [ERSSkill.TOTAL, ERSSkill.MINING];  // which skills HoverSkills/OpenSkills may choose from
  Self.MinZoom := 15;                                  // bounds AdjustZoom respects
  Self.MaxZoom := 40;

  inherited;   // runs WaspLib's TAntiban.Setup -> SetupTasks/SetupBreaks/SetupSleep + Mouse.Speed/Gravity/Wind/MissChance
end;
```

Pattern B — add YOUR OWN breaks/hooks ON TOP OF the default tasks (from `bigaussie_gemstone_crab_slayer.simba`, note `inherited` runs FIRST here since the intent is for the default tasks to already exist before potentially clearing `Self.Breaks`):

```pascal
procedure TAntiban.Setup(); override;
begin
  inherited;

  Self.Skills  := [ERSSkill.TOTAL, ERSSkill.ATTACK, ERSSkill.STRENGTH, ERSSkill.DEFENCE, ERSSkill.HITPOINTS];
  Self.MinZoom := 0;
  Self.MaxZoom := 15;

  Self.OnStartBreak  := @OnBreakStart;
  Self.OnFinishBreak := @OnBreakFinish;
  Self.OnStartSleep  := @OnSleepStart;
  Self.OnFinishSleep := @OnSleepFinish;
  Self.OnFinishTask  := @Self.HandleFinishTask;

  if OVERRIDEBREAKS then
  begin
    Self.Breaks := [];   // clears WaspLib's default breaks (which "inherited" just set up)
    Self.AddBreak(CUSTOMBREAKINTERVAL * ONE_MINUTE, CUSTOMBREAKDURATION * ONE_MINUTE, 0.33, 0.15);
  end;
end;
```

Pattern C — **entirely custom** tasks, ignoring WaspLib's defaults (old hand-built style in `aeroguardians.simba`, which doesn't inherit `TBaseScript` at all but calls `SetupAntiban` manually from its own `Init`):

```pascal
procedure TScript.SetupAntiban();
begin
  Antiban.Skills += ERSSKILL.RUNECRAFTING;
  Antiban.Skills += ERSSKILL.MINING;

  Antiban.AddTask(ONE_MINUTE*2,  @Mouse.RandomMovement);
  Antiban.AddTask(ONE_MINUTE*4,  @Antiban.SmallCameraRotation);
  Antiban.AddTask(ONE_MINUTE*6,  @Antiban.HoverMSPlayers);
  Antiban.AddTask(ONE_MINUTE*7,  @Antiban.RandomRotate);
  Antiban.AddTask(ONE_MINUTE*8,  @Antiban.HoverMSNPCs);
  Antiban.AddTask(ONE_MINUTE*25, @Antiban.HoverSkills);
end;
```

Pattern D — override `Setup` WITHOUT `inherited` (from the `herbiboar_hunter` script): this completely skips WaspLib's `SetupTasks`/default task list. Only your own `SetupBreaks`/`SetupSleep` overrides (if you write them) or manual `AddBreak`/`AddSleep` calls run:

```pascal
procedure TAntiban.SetupBreaks(); override;
begin
  if Self.Breaks <> [] then Exit;
  Self.AddBreak(StrToIntDef(Config.GetString('Antiban_BreakAfter'), 60) * ONE_MINUTE,
                StrToIntDef(Config.GetString('Antiban_BreakFor'), 15) * ONE_MINUTE);
  Self.OnBreaking := @OnBreakingTask;
end;

procedure TAntiban.Setup(); override;   // NO inherited!
begin
  Mouse.Speed      := 35 + Self.GetBehavior(EBioBehavior.MOUSE_SPEED);
  Mouse.Gravity    := 9  + Round(Self.GetBehavior(EBioBehavior.MOUSE_GRAVITY) / 2);
  Mouse.Wind       := 3  + Round(Self.GetBehavior(EBioBehavior.MOUSE_WIND) / 2);
  Mouse.MissChance := Self.GetBehavior(EBioBehavior.MOUSE_MISS);

  if Bot.CachedBreaksEnabled then Self.SetupBreaks();
  if Bot.CachedSleepsEnabled then Self.SetupSleep();

  if not InRange(MM2MS.GetZoomLevel(), Self.MinZoom, Self.MaxZoom) then
    Self.AdjustZoom();
end;
```

Result: no camera/mouse/chat/gametabs/bank tasks at all, regardless of what `wasplib.json` says, since `SetupTasks` (where they are added) is never called. This is a deliberate, valid choice — but easy to do by accident if you copy a `Setup` override and forget `inherited` (see §8).

**Summary of ordering rules:**
- Set `Self.Skills`/`MinZoom`/`MaxZoom` **before** `inherited` if you want the base class's `AdjustZoom` check in `Setup` (`if not InRange(MM2MS.GetZoomLevel(), Self.MinZoom, Self.MaxZoom) then Self.AdjustZoom();`) to use YOUR bounds immediately at startup.
- Set your own `OnStart*`/`OnFinish*` hooks anywhere in the method — they merely overwrite variables, and execution order doesn't matter except that they must be set before the first `DoAntiban` call (which they always are, since `Setup` runs in `Init` before the `Run` loop).
- If you want to clear/replace WaspLib's default lists (`Self.Breaks := []`), do it **after** `inherited` (otherwise the defaults are added again on top of your clearing the next time, although that normally doesn't happen due to the `<> []` guard — but the order `inherited` -> clear -> add your own is the safest and clearest).

---

## 4. How `DoAntiban`/`TakeBreak`/`TakeSleep` pause and resume timers

`TAntiban.DoAntiban` (`SRL-T/osr/antiban.simba`) does, every time it is called:

1. Fetches all **active** tasks (`GetActiveTasks` — those whose `Countdown` is not already paused by something else, e.g., an ongoing break).
2. Pauses their countdowns.
3. Runs each task whose countdown has expired (`OnStartTask` -> `Method()` -> new `Countdown.Init` -> `OnFinishTask`).
4. Resumes all task countdowns.
5. If `CheckBreaks`/`CheckSleeps`: checks whether any `TBreakTask`/`TSleepTask` should be triggered (`DoBreak`/`DoSleep`), which in turn calls `TakeBreak`/`TakeSleep`.

**`TakeBreak`/`TakeSleep` THEMSELVES do the same pause-everything pattern, but for the ENTIRE duration of the break:**

```pascal
procedure TAntiban.TakeBreak(var task: TBreakTask);
var
  activeTasks: PAntibanTaskArray;
begin
  activeTasks := Self.GetActiveTasks();
  for i := 0 to High(activeTasks) do
    activeTasks[i]^.countdown.Pause();          // <-- all tasks are paused before the break

  ... // OnStartBreak, possible logout, wait countdown.TimeRemaining()...

  for I := 0 to High(activeTasks) do
    activeTasks[i]^.countdown.Resume();         // <-- and resumed AFTER the break

  // Offset NextAtTime for all other breaks by exactly the time the break took,
  // so that a 30-minute break doesn't "eat" the time of a parallel 45-minute break.
  for i := 0 to High(Self.Breaks) do
    Self.Breaks[i].NextAtTime += GetTickCount() - (countdown.Timeout - countdown.Length);
end;
```

**Practical consequence: as a rule you do NOT need to write your own pause/resume logic for your antiban tasks around a break.** The system handles it itself — a 7-minute task timer that was 3 minutes into its countdown when a 10-minute break started continues from there once the break is over; it does not tick down during the break.

What you OFTEN DO want your own hooks for, on the other hand, is **your own, parallel timers** that are not `TAntibanTask` countdowns — e.g., a custom `TrueRunTime: TStopWatch` meant to represent "actual active playtime, excluding breaks" for statistics/shutdown logic. That's what `OnStartBreak`/`OnFinishBreak`/`OnStartSleep`/`OnFinishSleep` are for:

```pascal
procedure OnBreakStart(Task: PBreakTask);
begin
  GemStoneCrabBot.ActiveTimer.Pause();   // CUSTOM timer, not managed by TAntiban
  WL.Activity.Pause();                   // WaspLib's "activity detector" (aborts the script on excessive inactivity)
end;

procedure OnBreakFinish(Task: PBreakTask);
begin
  GemStoneCrabBot.ActiveTimer.Resume();
  WL.Activity.Resume();
end;
```

the same pattern in the older `aeroguardians.simba` (`BreakPause`/`BreakResume`/`SleepPause`/`SleepResume`), wired up in `SetupAntiban`:

```pascal
if Self.TakeBreaks then
begin
  Antiban.OnStartBreak  := @BreakPause;
  Antiban.OnFinishBreak := @BreakResume;
end;
```

And the `TBaseScript.DoAntiban` override itself in `bigaussie_gemstone_crab_slayer.simba` additionally pauses/resumes the script's OWN `TimeRunning` stopwatch and WaspLib's activity/API timer around the **entire** `DoAntiban` call (not just around breaks), since otherwise even short tasks would be counted into "time played":

```pascal
function TBaseScript.DoAntiban(checkBreaks: Boolean = True; checkSleeps: Boolean = True): Boolean; override;
begin
  Antiban.DismissRandom();
  Self.TimeRunning.Pause();
  ...
  Result := Antiban.DoAntiban(checkBreaks, checkSleeps);
  ...
  Self.TimeRunning.Resume();
end;
```

(Note: this is an override of `TBaseScript.DoAntiban`, NOT of `TAntiban.DoAntiban` — it calls `Antiban.DoAntiban` directly instead of `inherited`, which works equivalently here since `TBaseScript.DoAntiban`'s only job normally is exactly to forward the call.)

---

## 5. Biometrics: `BioHash`, `SetupBiometrics`, `BioWait`, `BioDice`

`WaspLib/utils/biometrics.simba` gives each account a consistent but unique "personality" via a global `BioHash: Double` (0.0–1.0), derived from the username (FNV-like hash) — the same account always yields the same BioHash between runs, different accounts yield different values.

```pascal
procedure TAntiban.SetupBiometrics();
```
Lazily initialized automatically — `GetBehavior`/`GetChance`/`BioDice` call `Self.SetupBiometrics()` internally if `BioHash = 0`. You normally do NOT need to call it manually in the script's `Setup`. **The exception:** GUI code that wants to display/use BioHash-dependent values BEFORE an account is selected/logged in (e.g., previewing sleep time in a combo box), or right after the user switches accounts in the GUI — in that case it must be called explicitly, since the hash would otherwise still point to the previous account. See `WaspLib/utils/forms/scriptform.simba`, which calls `Antiban.SetupBiometrics();` right after account selection in the GUI.

```pascal
Antiban.SetupBiometrics();  // only necessary manually on account switch in the GUI or similar edge cases
```

`BioWait`/`BioDice` are used to scale wait times/probabilities consistently per account, instead of completely randomly each time:

```pascal
procedure TAntiban.BioWait(time: UInt32);
procedure TAntiban.BioWait(min, max: UInt32; weight: EWaitDir = wdMean); overload;

function TAntiban.BioDice(): Boolean;
function TAntiban.BioDice(behaviour: EBioBehavior): Boolean; overload;
function TAntiban.BioDice(chance: Double): Boolean; overload;
```

Example from WaspLib's own code:

```pascal
Self.BioWait(500, 7000, wdLeft);              // wait 500-7000ms, BioHash-skewed
if Self.BioDice(EBioBehavior.FKEY_CHANCE) then // should this account "tend" to use F-keys?
  ... use FKeyOpen ...
```

`EBioBehavior` (same file) is an enum of behaviors BioHash can govern: `MOUSE_SPEED`, `MOUSE_GRAVITY`, `MOUSE_WIND`, `MOUSE_MISS`, `FKEY_CHANCE`, `ESCAPE_CHANCE`, `KEYBOARD_CHAT_CHANCE`, `REACTION_SPEED`, `SPAM_CLICK_CHANCE`, `DROP_PATTERN`, `CONSUME_IN_BANK`, `USES_STAR_BUTTONS`, `TENDS_TO_LIKE`. `Antiban.GetBehavior(EBioBehavior.X)`/`GetChance(EBioBehavior.X)` retrieve a number from BioHash tied to that specific trait (same account -> same value every time -> consistent "personality").

WaspLib's default `TAntiban.Setup()` in fact sets the mouse's base behavior directly from BioHash:

```pascal
Mouse.Speed      := 15 + Self.GetBehavior(EBioBehavior.MOUSE_SPEED);
Mouse.Gravity    := 9  + Round(Self.GetBehavior(EBioBehavior.MOUSE_GRAVITY) / 2);
Mouse.Wind       := 3  + Round(Self.GetBehavior(EBioBehavior.MOUSE_WIND) / 2);
Mouse.MissChance := 11 + Self.GetBehavior(EBioBehavior.MOUSE_MISS);
```

which is why two different accounts running exactly the same script still move the mouse at different speeds/precision.

`Antiban.GetSleepHour()`/`GetSleepLength()` use BioHash in the same way to give each account a consistent but individual sleep time/length if `wasplib.json` -> `antiban.sleep.biohash = true` (default).

---

## 6. The `HandleFinishTask` safety pattern (from the crab slayer script)

Antiban tasks move the mouse/camera/UI in ways the script's OWN logic doesn't control. The risk: a task leaves the mouse on a dangerous button (e.g., the world-switcher globe, or a "Logout" button), or triggers/misses a system message the script should react to. `bigaussie_gemstone_crab_slayer.simba` solves this with an `OnFinishTask` hook that runs after EVERY antiban task:

```pascal
procedure TAntiban.HandleFinishTask(Task: PAntibanTask);
var
  MousePos: TPoint;
  GlobeButton: TBox;
  YellowChatbox: TPointArray;
begin
  MousePos := Mouse.Position();
  GlobeButton := ([715, 120, 745, 148]);   // coordinates for the world-switcher globe

  if GlobeButton.Contains(MousePos) then
  begin
    WriteLn('[ANTIBAN] Mouse detected on globe button, moving to mainscreen');
    Mouse.Move(Mainscreen.Bounds);          // move the mouse away from the dangerous zone
  end;

  // Check whether a yellow chatbox warning appeared on the minimap (common with system messages)
  SRL.FindColors(YellowChatbox, CTS2(10551295, 1, 0.01, 0.01), Minimap.Bounds);
  if Length(YellowChatbox) > 2000 then
  begin
    WriteLn('[ANTIBAN] Yellow chatbox detected on minimap, waiting 2 seconds');
    Wait(2000);
  end;
end;
```

wired up in `Setup`:

```pascal
Self.OnFinishTask := @Self.HandleFinishTask;
```

**General recipe:** if an antiban task in your script moves the mouse freely across the screen (which `RandomMouseTask`/`RandomRightClick`/`SmallRandomMouse` do), and your script has ONE OR MORE dangerous clickable zones (logout, world switcher, a button that spends resources), add an `OnFinishTask` that checks `Mouse.Position()` against those zones and moves the mouse away if it ended up there. This is *cheap* to write and prevents an entire class of "a task happened to click something dumb on the next loop iteration" bugs.

---

## 7. World hopping as antiban behavior

`bigaussie_gemstone_crab_slayer.simba` implements world hopping entirely outside `TAntiban` (custom fields on the script's record, no `TAntibanTask`), but in the same humanized spirit. The pattern:

```pascal
TScript = record(...)
  NextWorldHopTime: UInt64;
  WorldHopsCompleted: Int32;
  LastWorldHopTime: Int64;
end;

function TScript.GetRandomWorldHopTime(): UInt64;
var
  BaseInterval: UInt64;
  RandomVariation: Integer;
begin
  BaseInterval := WORLDHOPINTERVAL * 60000;
  RandomVariation := Random(-10, 10);                       // +-10% humanized variation
  Result := BaseInterval + Round(BaseInterval * (RandomVariation / 100.0));
end;

function TScript.ShouldHopWorld(): Boolean;
var
  TimeSinceLastCombat, RequiredCombatCooldown, TimeToWait: UInt64;
begin
  if not ENABLEWORLDHOPPING then Exit(False);
  if Self.InCombat or Self.IsAttacking then Exit(False);     // NEVER hop in the middle of combat
  if GetTickCount() < Self.NextWorldHopTime then Exit(False);

  TimeSinceLastCombat := GetTickCount() - Self.LastHealthCheck;
  RequiredCombatCooldown := Random(20000, 30000);             // require 20-30s outside combat

  if TimeSinceLastCombat < RequiredCombatCooldown then
  begin
    TimeToWait := RequiredCombatCooldown - TimeSinceLastCombat;
    Wait(TimeToWait);                                         // wait out the cooldown before we hop
  end;

  Result := True;
end;
```

and is called AFTER antiban has already run, at a safe point in the loop:

```pascal
Self.DoAntiban(True, True);

// Hop AFTER we break/sleep etc
if Self.ShouldHopWorld() then
begin
  Self.DoWorldHop();
  Exit(False);
end;
```

`DoWorldHop` itself checks again that the player is not in combat (double safety), selects a RANDOM target among the account's configured worlds (`availableWorlds[Random(Length(availableWorlds))]`, not always "the next" world in sequence), and resets the script's internal combat/cave state after a successful hop.

**General recipe if you want to add world hopping to a new script:**
1. Compute the next hop time with a base + randomized percentage variation (`+-10%` is a reasonable benchmark), not a fixed interval.
2. Require N seconds outside combat/sensitive activity before a hop is actually performed (`Random(20000, 30000)` in the example) — otherwise it looks like the player teleports away in the middle of a fight.
3. Choose the target world randomly among available options, not sequentially.
4. Run the hop AFTER `DoAntiban`, not instead of or in the middle of it.
5. Handle a failed hop with a short retry delay (the script sets `NextWorldHopTime := GetTickCount() + 120000` on error) rather than crashing.

---

## 8. Common pitfalls

- **Forgetting to call `DoAntiban` regularly.** Tasks/breaks/sleeps are scheduled but completely inert without a periodic `Self.DoAntiban()`/`Antiban.DoAntiban()` call in the main loop. This is by far the most common culprit when "antiban doesn't seem to do anything."

- **Overriding a method but forgetting `inherited` when the intent was only to ADD behavior.** `procedure TAntiban.Setup(); override; begin ... end;` WITHOUT `inherited` NEVER runs `SetupTasks`/`SetupBreaks`/`SetupSleep` and does not set the mouse's BioHash-based `Speed`/`Gravity`/`Wind`/`MissChance`. Result: no default tasks at all, and mouse movements may look more robotic/identical across accounts. Always write `inherited;` unless you DELIBERATELY want to replace the entire behavior (as in §3 Pattern D — valid, but a conscious choice, not a forgotten line).

- **Thinking a task is disabled just because it was never added manually — but the WaspLib default exists anyway.** If you never wrote `Antiban.AddTask(..., @Antiban.RandomChatTask, ...)` yourself, that does NOT mean chat antiban is off. `SetupTasks` (which runs automatically via `Setup`/`inherited`) adds it if `wasplib.json` -> `antiban.tasks.chat = true` (default). If you want to verify what's actually scheduled, log `Length(Antiban.Tasks)` after `Init`, or read `wasplib.json`/the GUI's antiban tabs — not just your own script file.

- **Overriding a built-in task method to a no-op and thinking it's now "removed."** `procedure TAntiban.RandomChatTask(); override; begin Exit; end;` disables the BEHAVIOR, but `SetupTasks` still adds it to the `Self.Tasks` list (the countdown ticks, `DoAntiban` "runs" it, but the method does nothing). This is harmless in practice (a no-op costs essentially nothing), but don't confuse it with the task never having been scheduled.

- **Writing your own pause/resume logic for antiban tasks around your own break implementation, even though `TakeBreak`/`TakeSleep` already do it for you.** If you use `Antiban.AddBreak`/`AddSleep` (the normal way), ALL active `TAntibanTask` countdowns are automatically paused/resumed around the break/sleep (see §4). Custom pausing code is only needed for your OWN, parallel timers (a `TStopWatch` for "true active time," activity detectors, API timers) — wire them up via `OnStartBreak`/`OnFinishBreak`/`OnStartSleep`/`OnFinishSleep`, not by manually looping over `Antiban.Tasks`.

- **Calling `DoAntiban(False, False)` everywhere "to be safe" and forgetting a full call.** If breaks/sleeps never get the chance to trigger (every call disables them), the script never takes breaks even if they are configured. Make sure at least one regular, "safe" point in the loop makes a full `DoAntiban(True, True)`/`DoAntiban()` call.

- **Setting `MinZoom`/`MaxZoom` AFTER `inherited` when you wanted the startup zoom check in the base `Setup` to respect them.** The base `Setup` contains `if not InRange(MM2MS.GetZoomLevel(), Self.MinZoom, Self.MaxZoom) then Self.AdjustZoom();` — if your bounds are set after `inherited`, that check has already run (or ran with `0`/undefined bounds).

- **Confusing `TAntiban.DoAntiban` (SRL-T, the core logic) with `TBaseScript.DoAntiban` (WaspLib, a thin wrapper).** Both can be overridden separately and serve different purposes — `TBaseScript.DoAntiban` is the place to pause/resume the SCRIPT'S OWN timers (`WL.Activity`, `APIClient.Timer`, a custom `TimeRunning`) around the entire call; `TAntiban.DoAntiban` is the place to change how tasks/breaks/sleeps themselves are selected and triggered.

---

## 9. Checklist: antiban in a new script

1. Is the script built on `TBaseScript`/`TBaseWalkerScript`/`TBaseBankScript`? Then you get `Antiban.Setup()` for free via `Init` — just verify that your `Run` loop actually calls `Self.DoAntiban()` every iteration.
2. Decide: do you want WaspLib's default tasks (camera/mouse/chat/gametabs/bank)? If yes, do nothing extra (they're on by default) or write a `TAntiban.Setup(); override;` that calls `inherited`. If no for ONE category, override that specific method to a no-op; if no for EVERYTHING, override `Setup` without `inherited` (and remember the `Mouse.Speed`/`Gravity`/`Wind`/`MissChance` lines manually).
3. Set `Self.Skills` (which skills may be hovered/opened by `HoverSkills`/`OpenSkills`) and `Self.MinZoom`/`MaxZoom` in your `Setup` override, BEFORE `inherited` if you want the startup zoom check to respect them immediately.
4. Do you need your own parallel timers (active-time stopwatch, activity detector)? Wire up `OnStartBreak`/`OnFinishBreak`/`OnStartSleep`/`OnFinishSleep` — rely on `TakeBreak`/`TakeSleep` already pausing/resuming your `AddTask` countdowns.
5. Does the script move the mouse freely over dangerous UI zones (logout, world switcher, resource-spending buttons)? Add an `OnFinishTask` hook (the `HandleFinishTask` pattern, §6) that moves the mouse away from known danger zones and catches unexpected system messages.
6. Do you want breaks/sleeps? Check `wasplib.json`/the GUI — they are OFF by default (`breaks: false`, `sleep.enabled: false`). Enable via the GUI (`CreateAntibanManager`) or your own `AddBreak`/`AddSleep` calls/overrides of `SetupBreaks`/`SetupSleep`.
7. Do you want world hopping? Implement it as custom fields + methods on the script's record (not as a `TAntibanTask`), with a humanized interval (base ± ~10%), a requirement of X seconds outside combat before hopping, random target selection among available worlds, and run it AFTER `DoAntiban` in the loop.
8. Test: log `Length(Antiban.Tasks)`/`Length(Antiban.Breaks)`/`Length(Antiban.Sleeps)` right after `Init` to verify that what was actually scheduled matches your intent, before trusting that everything "just works" in the background.
