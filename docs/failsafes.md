# Robustness and error handling in Lape/SRL-T/WaspLib scripts

This file is the reference for **how to make sure an OSRS bot script doesn't crash, get stuck in an infinite loop, or cause damage (leave the account visibly logged in, spam the same error over and over) when something unexpected happens**. This is NOT the same topic as antiban (randomized timing, human-like behavior to avoid detection) — that has its own separate file. Here it's all about defensive programming: log clearly, put an upper bound on everything that waits, count failures, and escalate cleanly when something goes wrong.

Sources: installed WaspLib/SRL-T helpers plus multiple real scripts examined during research. One larger example script is especially thorough, with Discord webhooks, a `CheckSystemUpdate` pattern, HP failsafes, and a `ConsecutiveFailedAttacks` counter. See also `script-anatomy.md` §11 for a brief overview — this file goes deeper into the same topic.

---

## 1. Logging: `WriteLn`, the `WriteMsg` wrapper, and `DEBUGMODE`

The basic pattern is a thin wrapper around `WriteLn` that adds a prefix tag, so logs can be visually scanned and (if desired) filtered:

```pascal
const
  DEBUGMODE = True;  // Enable debug mode?

procedure TScript.WriteMsg(Message: String);
begin
  WriteLn('[Bot]: ' + Message);
end;
```

Usage, almost always conditioned on `DEBUGMODE`:

```pascal
if DEBUGMODE then
  Self.WriteMsg('Repairing rune pouches');
```

**Why you wrap logging behind a flag instead of logging unconditionally:**
- Bot scripts often log inside tight loops (every state transition, every pixel search). Unconditional logging there floods the console and makes it hard to find the line that actually matters when something goes wrong.
- `DEBUGMODE` gives you a single place to turn off "noise" logging for production runs but turn it back on when debugging, without deleting or commenting out code.
- Critical events (errors that lead to `TerminateScript`, triggered failsafes, Discord notifications) are still always logged **unconditionally** with plain `WriteLn` — it's only the routine "what am I doing right now" logging that belongs behind `DEBUGMODE`. See for example the crab slayer script: all `ConsecutiveFailedAttacks`, degradation, and death messages are always logged, regardless of `DEBUGMODE` state, because they must show up in the console/log file no matter what.

The crab slayer script additionally uses per-subsystem prefix tags instead of a generic `[Bot]:`, which makes it easier to `grep`/scroll through the log for a specific failsafe system:

```pascal
WriteLn('[BOLT ENCHANTING] Cannot cast Enchant Crossbow Bolt - out of runes or bolts');
WriteLn('[Discord] Failed to send system update warning');
WriteLn('[Screenshot] Failed to save screenshot - skipping');
```

**Rule:** give every major subsystem (Discord, screenshots, a specific failsafe) its own `[TAG]` prefix if the script is large enough to have several. For simpler scripts, a generic `Self.WriteMsg` is enough.

---

## 2. `TerminateScript` versus `Exit`/`False` and letting the main loop retry

`TerminateScript('reason')` is a **hard, irrevocable stop**. It should only be used for errors that cannot be healed by trying again later:

- Missing a required piece of equipment (`'Player does not have a pickaxe'`, `'Could not find colossal pouch'`).
- Out of a critical resource that the script itself cannot reacquire (`'Could not find the skills necklace'`, `'No player credentials'`).
- The account appears to be banned/in a strange state (`'Ring of life activated'` — something has gone seriously wrong in combat).
- The game server is about to go down (`'Time to shutdown'`, system update failsafe, see §6).
- A repeated-failure counter has reached its limit (see §3): `'No XP gained from 3 consecutive attacks'`.

Contrast this with ordinary state functions that simply return `Boolean`: if a single action fails (couldn't find an object right now, a click missed), the function should normally **return `False`/do an `Exit`** and let the main loop's `GetState()`/`case` pattern try again next iteration. Terminating on every small, transient failure makes the script unnecessarily brittle — termination is for things that don't resolve themselves by retrying.

**Log before terminating.** This pattern appears in practically every example in the source material:

```pascal
Self.WriteMsg('No pickaxe');
Logout.ClickLogout;
TerminateScript('Player does not have a pickaxe');
```

```pascal
Logout.ClickLogout();
TerminateScript('Time to shutdown');
```

Why: if the script just dies without logging out, the account is left logged in and visible on screen (or, if running headless/on a farm, in an unknown state that a human has to check manually). Logging out before terminating is a simple, cheap safety measure — make it a reflex every time you write a `TerminateScript` line.

---

## 3. Counters for repeated failures: the `ConsecutiveFailedAttempts` pattern

The pattern: keep a counter in the script's main record, increment it on every failure, **reset it to 0 on every success**, and escalate (change strategy or terminate) once it passes a threshold. This is the difference between tolerating a single, transient failure and detecting that something is *systematically* wrong (out of ammo, wrong state, the game has changed).

From a larger representative example script:

```pascal
type
  GemStoneCrabSlayer = record(TBaseScript)
    ...
    ConsecutiveFailedAttacks: Int32;
    LastFailedAttackTime: UInt64;
    LastSuccessfulClick: Boolean;
    ...
  end;
```

Reset on success:

```pascal
WL.Activity.Restart();
Self.ConsecutiveFailedAttacks := 0;
WriteLn(ModePrefix + 'Successfully attacked boss and gained XP!');
```

Increment and escalation on failure (note: it waits with a timeout, see §4, BEFORE giving up):

```pascal
until (GetTickCount() - TimeoutStart) > 5000;

WriteLn(ModePrefix + 'No XP gained within 5 seconds after attack');

Inc(Self.ConsecutiveFailedAttacks);
Self.LastFailedAttackTime := GetTickCount();
WriteLn(ModePrefix + 'Attack failed to gain XP. Consecutive failed attacks: ', Self.ConsecutiveFailedAttacks, '/3');

if Self.ConsecutiveFailedAttacks >= 3 then
begin
  WriteLn('3 consecutive boss attacks failed to gain XP!');
  WriteLn('This likely means we are out of ammo/runes. Logging out and terminating script.');

  Self.TakeScreenshot('_NoAmmoFailsafe');

  if ENABLEWEBHOOKS then
  begin
    try
      Discord.Webhook.Content := 'Failed to gain XP! Script will logout and terminate. Please check your ammo/runes!';
      Discord.SendScreenshot(False);
    except
      WriteLn('[Discord] Failed to send no ammo notification');
    end;
  end;

  TerminateScript('No XP gained from 3 consecutive attacks');
end;
```

Notice the whole chain in this single example: timeout-bounded wait -> counter -> log -> screenshot -> Discord notification in `try/except` -> `TerminateScript`. That's exactly the escalation order you want to replicate in new scripts.

The script also has a **"forgot-about-it counter"** safety valve: if a long time has passed since the last error, reset the counter even without a successful attack, so that old, irrelevant errors don't accumulate against future, unrelated errors:

```pascal
if (Self.ConsecutiveFailedAttacks > 0) and
   (Self.LastFailedAttackTime > 0) and
   ((GetTickCount() - Self.LastFailedAttackTime) > 600000) then
begin
  Self.ConsecutiveFailedAttacks := 0;
  Self.LastFailedAttackTime := 0;
end;
```

**Rule for new scripts:** every action that can fail in a way that *could* mean "something is systematically wrong" (out of resource, wrong game state, the game has changed) should have a corresponding counter. Reset on success, escalate after N (often 3) in a row, and clean up (screenshot, log, possibly webhook, `Logout.ClickLogout`) before `TerminateScript`.

---

## 4. Timeout patterns: `TCountdown` and `WaitUntil`

**This is the dominant technique for waiting on something in these scripts, and the single most important rule in this file: a wait without an upper time limit can hang the script permanently.** Never use a bare `while <condition> do` without a parallel time-out.

### `WaitUntil(condition, intervalMs, timeoutMs)`

The most common form — polls a condition at an interval, gives up after a timeout, returns `Boolean` for whether the condition became true before time ran out:

```pascal
if WaitUntil(Bank.IsOpen(), 115, 12500) then
  ...

if (not WaitUntil(Self.IsInWestArea, 75, 500)) then Exit;

WaitUntil(InRange(Self.GetETypeRune, TYPEAIR, TYPEBLOOD), 150, 5000);
```

Patterns to note:
- The result is often used directly in an `if`/`if not ... then Exit` — if the condition never became true within the time limit, give up on this action rather than continuing as if everything went fine.
- The second and third arguments (interval, timeout) are varied depending on how quickly you expect the condition to normally be satisfied — short `WaitUntil` calls (300-2500 ms) for UI reactions, longer ones (5000-12500 ms) for game-world events like walking or loading.

### `TCountdown` — for manual loops that must be polled with their own logic between each attempt

When the wait can't be expressed as a simple condition (e.g. you have to *do* something — click again — every iteration, not just check), `TCountdown` is used manually:

```pascal
var
  bankTimeout: TCountdown;
begin
  bankTimeout.Init(45000);

  while not bankTimeout.IsFinished() and not Bank.IsOpen() do
  begin
    Bank.WalkOpen(Bot.BankObj);
  end;

  WaitUntil(Bank.IsOpen(), 115, 12500);
```

The API used throughout:
- `T.Init(ms)` — starts the countdown.
- `T.IsFinished` — `True` once the time has run out.
- `T.TimeRemaining` — time remaining, useful for e.g. logging "X ms left" or computing a shorter sub-timeout.

**The general form to always write:**

```pascal
while (not T.IsFinished()) and (not <condition>) do
begin
  <do something to try to satisfy the condition>;
end;
```

never:

```pascal
while not <condition> do  // DANGEROUS: no upper bound
  <do something>;
```

### Manual timeout with `GetTickCount()` when `TCountdown` feels too heavy

In simpler cases, the same idea is used directly with `GetTickCount()`, for example the crab slayer script's attack confirmation:

```pascal
var
  TimeoutStart: UInt64;
begin
  TimeoutStart := GetTickCount();
  repeat
    ...
    if <xp gained> then
    begin
      Result := True;
      Exit;
    end;
  until (GetTickCount() - TimeoutStart) > 5000;

  WriteLn(ModePrefix + 'No XP gained within 5 seconds after attack');
  // ... escalate (see §3)
```

Both variants (`TCountdown` or a raw `GetTickCount` diff) are valid — choose `TCountdown` when you already have an instance kept around across multiple calls (e.g. a reused field timer), and a raw `GetTickCount` diff for a one-off check within a function.

---

## 5. Chat-based failsafes

Many game states are *not* clearly visible in the UI but are printed as a chat message — that's often the only reliable way to detect them programmatically. The pattern: look for specific keywords in the most recent chat lines, act if something is found.

```pascal
function GemStoneCrabSlayer.IsOutOfAmmo(): Boolean;
var
  Messages: String;
  I: Int32;
begin
  Result := False;

  for I := 0 to CHAT_INPUT_LINE - 1 do
    Messages += Chat.GetMessage(I, [CHAT_COLOR_BLACK]);

  Result := Messages.ContainsAny([
    'out of ammo',   // General ammo message
    'no charges',    // Magic weapons/trident
    'last one',      // Darts/throwing weapons
    'degraded'       // Dharoks armour
  ]);

  if Result then
    WriteLn('Out of ammo detected in chat messages');
end;
```

A single search for a specific phrase with `Chat.FindMessage`:

```pascal
if Chat.FindMessage('no bolts', [CHAT_COLOR_BLACK]) or Chat.FindMessage('not have enough', [CHAT_COLOR_BLACK]) then
begin
  WriteLn('[BOLT ENCHANTING] Chat message for bolts - disabling bolt enchanting');
  ENABLEBOLTENCHANTING := False;
  Exit;
end;
```

Death detection (combines chat search + screenshot + webhook + logout + termination in a single, complete failsafe):

```pascal
if (Chat.FindMessage('you are dead', [CHAT_COLOR_BLACK])) then
begin
  Self.TakeScreenshot('_PlayerDeath');
  WaitUntil(Minimap.PercentBlack() < 20, 65, 10000);
  WriteLn('PLAYER HAS DIED! Terminating script');

  if ENABLEWEBHOOKS then
  begin
    try
      Discord.Webhook.Content := '**PLAYER DEATH** :skull: Script detected player death and is terminating.';
      Discord.SendScreenshot(False);
    except
      WriteLn('[Discord] Failed to send death notification');
    end;
  end;
  Logout.ClickLogout();
  TerminateScript('Player death detected');
end;
```

**General rule:** every time you implement an activity that can run out of a resource (ammo, runes, food), or where the game has a distinct chat message for an error condition (degraded equipment, "you are dead", "enough" when casting a spell), search for that phrase explicitly. Don't guess — look in the chat for exactly what the game says in that state (test it manually or ask the community for the exact string).

**Warning related to antiban:** if the antiban system's `RandomChatTask` toggles chat tabs randomly, it can filter out messages your failsafes need to read. As mentioned in `script-anatomy.md` §8 — override `RandomChatTask` to a no-op if your chat-based failsafes are critical.

---

## 6. Proactive handling of server events: `CheckSystemUpdate`

Jagex shows a countdown in the chat ("System update in X minutes") ahead of planned server restarts. Simply letting the script run into the restart risks a frozen client or an account left mid-way through a dangerous situation. The pattern: read the countdown with OCR, and if it's below a threshold, log out cleanly *before* the restart hits.

From `bigaussie_gemstone_crab_slayer (3).simba` (the comment "Thanks Bootie" in the original code):

```pascal
function TRSChat.CheckSystemUpdate(minuteTreshold: Integer): Boolean;
var
  b: TBox;
  s: String;
  numbers: TExtendedArray;
begin
  b := Chat.Bounds;
  b.X1 += 4;
  b.Y1 -= 16;
  b.Y2 := Chat.Bounds.Y1 - 1;
  b.X2 := b.X1 + 140;

  s := OCR.Recognize(
      b,
      TOCRColorFilter.Create([65535]),
      RS_FONT_PLAIN_12
    );

  if s.Contains('System update') then
  begin
    s := s.After(': ');
    numbers := s.ExtractNumbers();
    if (length(numbers) > 0) and (numbers[0] <= minuteTreshold) then
      Result := True;
  end;
end;
```

This is extended into a method on the script itself (`TRSChat` is SRL-T's type, `GemStoneCrabSlayer.CheckSystemUpdate` is the script's own wrapper around it) which adds throttling (doesn't check every tick), a one-time warning, and a clean logout flow:

```pascal
procedure GemStoneCrabSlayer.CheckSystemUpdate();
var
  CurrentTime: UInt64;
  SystemUpdateThreshold: Integer;
begin
  CurrentTime := GetTickCount();
  // (throttling: only checks every X seconds, not every loop iteration)
  ...
  Self.LastSystemUpdateCheck := CurrentTime;

  SystemUpdateThreshold := 15;

  if Chat.CheckSystemUpdate(SystemUpdateThreshold) then
  begin
    WriteLn('SYSTEM UPDATE DETECTED! Server going down in ' + IntToStr(SystemUpdateThreshold) + ' minutes or less!');

    if not Self.SystemUpdateWarningShown then
    begin
      if ENABLEWEBHOOKS then
      begin
        try
          Discord.Webhook.Content := '**SYSTEM UPDATE DETECTED** :warning: Server going down in ' + IntToStr(SystemUpdateThreshold) + ' minutes or less! Preparing to logout...';
          Discord.Send();
        except
          WriteLn('[Discord] Failed to send system update warning');
        end;
      end;
    end;

    // Only logout if we're NOT in combat
    if not (Self.InCombat or Self.IsAttacking) then
    begin
      WriteLn('Not in combat - logging out safely for system update');

      if ENABLEWEBHOOKS then
      begin
        try
          Discord.Webhook.Content := '**SAFE LOGOUT** :white_check_mark: Successfully logged out before system update. Runtime: ' + SRL.MsToTime(GetTimeRunning(), Time_Short);
          Discord.SendScreenshot(False);
        except
          WriteLn('[Discord] Failed to send safe logout notification');
        end;
      end;

      Logout.ClickLogout();
      ...
    end;
  end;
end;
```

Note the design choice of **"wait until we're not in combat before logging out"** — a blind, immediate logout in the middle of a dangerous fight can be worse than letting the restart take the script down. The call to `Self.CheckSystemUpdate()` is then placed in the main loop (the same place as `Self.CheckHourlyReport()` and other status checks) so it gets checked every iteration (with internal throttling).

**A more primitive variant** (without OCR, just a hard time limit set by the user/GUI): an older example has the same idea but simpler — a `Bot.ShutdownTime` compared against `GetTimeRunning()`:

```pascal
if GetTimeRunning() > Bot.ShutdownTime then
  TerminateScript('Time to shutdown');
```

Use the OCR variant when you want to react specifically to Jagex's actual countdown; use the simple time-limit variant when you just want the script to stop running after a certain number of hours regardless of reason.

---

## 7. Screenshots on error: the `SaveScreenshot`/`TakeScreenshot` wrapper

Always save a screenshot right before handling a critical error (before logout, before termination) — it's the only chance to see *exactly* what happened afterward. The wrapper should be defensive in multiple layers, so that a screenshot failure can never itself crash the error handling it's meant to support:

```pascal
procedure GemStoneCrabSlayer.TakeScreenshot(Name: String);
var
  ScreenshotPath: String;
  FileCount: Integer;
begin
  try
    if (Name = '') then
      Name := 'Unknown';

    try
      CreateDirectory('Screenshots/');
    except
      WriteLn('[Screenshot] Failed to create Screenshots directory');
      Exit;
    end;

    try
      FileCount := Length(GetFiles('Screenshots/', 'png'));
    except
      WriteLn('[Screenshot] Failed to count existing screenshots, dfault to 0');
      FileCount := 0;
    end;

    ScreenshotPath := 'Screenshots/GemStoneCrab' + Name + '_' + IntToStr(FileCount) + '.png';

    try
      SaveScreenshot(ScreenshotPath);
      WriteLn('[Screenshot] Successfully saved: ' + ScreenshotPath);
    except
      WriteLn('[Screenshot] Failed to save screenshot - skipping');
    end;

  except
    WriteLn('[Screenshot] Error in TakeScreenshot - skipping');
  end;
end;
```

Usage — always with a descriptive name identifying WHICH error triggered it, so the files can be sorted/searched afterward:

```pascal
Self.TakeScreenshot('_PlayerDeath');
Self.TakeScreenshot('_NoAmmoFailsafe');
```

The filename is incremented automatically (`FileCount`) so that repeated runs don't overwrite each other's screenshots.

**Why three nested `try/except` blocks instead of one big one:** if the directory can't be created, you still want to log *that specific* error and bail out early (`Exit`), rather than pretending to count files in a folder that doesn't exist. Each step has its own, natural fallback behavior — that's hard to express with a single enclosing `try/except`.

---

## 8. External notifications: Discord webhooks

`Discord` is a global `TDiscordClient` instance, set up once in the script's init (usually conditioned on an `ENABLEWEBHOOKS` flag from the GUI):

```pascal
var
  Discord: TDiscordClient;
...
if ENABLEWEBHOOKS then
begin
  Discord.SetWebhook(WEBHOOKURL);
  Discord.SetUsername('BigAussies Gemstone Crab Slayer');
  Discord.SetAvatar('https://oldschool.runescape.wiki/images/thumb/2/2e/Gemstone_crab.png/150px-Gemstone_crab.png');
end;
```

**Every single webhook call sits in its own `try/except`.** This is the most important rule for the Discord integration: a network error, an invalid webhook URL, or Discord responding with an error message must NEVER crash the rest of the script — webhooks are a bonus feature, not a critical path.

```pascal
if ENABLEWEBHOOKS then
begin
  try
    Discord.Webhook.Content := '**DHAROKS ARMOUR DEGRADED** :warning: Your Dharoks armour has degraded and the script will terminate.';
    Discord.SendScreenshot(False);
  except
    WriteLn('[Discord] Failed to send degradation notification');
  end;
end;
```

Two send methods are used depending on whether you want to attach an image:
- `Discord.Send()` — sends only the text content in `Discord.Webhook.Content` (and any embeds).
- `Discord.SendScreenshot(False)` — takes and attaches a screenshot to the message (the parameter often controls whether the mouse cursor should be shown/hidden).

Richer messages are built with embeds (e.g. for periodic status reports):

```pascal
try
  Discord.Webhook.Content := '**Hourly Progress Report** :chart_with_upwards_trend:';

  EmbedIdx := Discord.Webhook.AddEmbed();
  Discord.Webhook.Embeds[EmbedIdx].Title := 'BigAussies Gemstone Crab Slayer - Hourly Report';
  Discord.Webhook.Embeds[EmbedIdx].Color := $FFA500;
  Discord.Webhook.Embeds[EmbedIdx].Description := 'Runtime: ' + SRL.MsToTime(GetTimeRunning, Time_Short) + LineEnding +
                                                  'XP Gained: ' + FormatRoundedNumber(TotalXPGained);

  if Discord.Send() then
    WriteLn('[Discord] Hourly report sent!')
  else
    WriteLn('[Discord] Failed to send hourly report: ' + Discord.LastError);
except
  WriteLn('[Discord] Error sending hourly report: ' + GetExceptionMessage);
end;
```

Note the pattern of logging **both** the expected failure case (`if Discord.Send() then ... else WriteLn(... Discord.LastError)`) **and** having an enclosing `try/except` for the unexpected (network exception). `GetExceptionMessage` gives the actual exception text for the log.

**Automatically send a summary when the script ends**, regardless of why it ended, using `AddOnTerminate`:

```pascal
if SENDSESSIONSUMMARYMSG and ENABLEWEBHOOKS then
  AddOnTerminate(@Self.SendTerminationNotification);
```

`AddOnTerminate` registers a callback that the Simba runtime runs when the script ends — whether that was via `TerminateScript`, an unhandled error, or the user stopping it manually. A good place to send a session summary (total XP, runtime, number of successful rounds) without having to remember to call it at every single `TerminateScript` line in the code.

---

## 9. `try/except`/`try/finally` — when, and when NOT

### `try/except`: protect against calls that can throw an exception you can't prevent with a condition

Typical use cases in the source material:
- **Network calls** (Discord webhooks, HTTP downloads) — external systems you don't control can always time out or respond incorrectly.
- **Filesystem operations** (create folder, count files, save screenshot) — disk can be full, the folder can be locked by another program.

```pascal
Client := InitializeHTTPClient(False);
try
  GetHTTPPageEx(Client, URL, Filename);
finally
  FreeHTTPClient(Client);
end;
```

### `try/finally`: guarantee cleanup regardless of whether the code in the `try` block succeeds or throws an exception

The most common concrete example is **freeing DTMs** (`FreeDTM`) allocated with `DTMFromString`. If the search between allocation and freeing throws an exception (or just exits early via a `Break`/`Exit` inside the `try`), the DTM memory must still be freed — otherwise it leaks on every call:

```pascal
function GetEnhancedNPCDots(): TPointArray;
const
  NPC_DTM1: Int64 := DTMFromString('...');
  NPC_DTM2: Int64 := DTMFromString('...');
  // ... NPC_DTM3..7
begin
  try
    if FindDTMs(NPC_DTM1, TempPoints, SearchArea) then AllPoints := AllPoints + TempPoints;
    if FindDTMs(NPC_DTM2, TempPoints, SearchArea) then AllPoints := AllPoints + TempPoints;
    // ... the rest of the searches and deduplication logic
  finally
    FreeDTM(NPC_DTM1); FreeDTM(NPC_DTM2); FreeDTM(NPC_DTM3); FreeDTM(NPC_DTM4);
    FreeDTM(NPC_DTM5); FreeDTM(NPC_DTM6); FreeDTM(NPC_DTM7);
  end;
end;
```

Another common `try/finally` case: guarantee that a held-down key is released even if something in the middle fails (otherwise a crash in the middle of a shift-click sequence can leave Shift held down permanently):

```pascal
try
  // ... loop that holds Shift down and clicks multiple slots
finally
  if IsKeyDown(VK_SHIFT) then
    KeyUp(VK_SHIFT);
end;
```

**General rule for `try/finally`:** use it when you have a resource (DTM, held-down key, open file handle, a paused timer) that must be restored/freed regardless of outcome. If there is no such resource to clean up, no `finally` is needed.

### Why you should NOT wrap ALL code in `try/except`

It's tempting to put one giant `try/except` around an entire function or the whole main loop "just to be safe." **Don't do that.** The reasons:

1. **It hides real bugs.** If a logic error (wrong index, null reference, typo in a comparison) happens to be thrown as an exception, and you catch it silently or just log a generic line, all information about WHERE and WHY disappears. You end up with a script that "works" (doesn't crash) but behaves incorrectly in ways that are extremely hard to trace later.
2. **It prevents real failsafes from ever triggering.** If a bug causes an exception that gets silently swallowed every loop iteration, nothing visible happens — no logs, no Discord notification, no `TerminateScript`. The script just stands still or behaves strangely indefinitely, which is exactly what this file is trying to prevent.
3. **Specific `try/except` blocks (around just the network call, just the file operation) give a much more useful error report**, because you know exactly which operation failed, compared to "something, somewhere in this 200-line-long function, threw an error."

**Rule of thumb:** `try/except`/`try/finally` should wrap a specific, named risk (this network call, this file operation, these DTM allocations) — not act as a generic safety net around logic you don't trust. If you feel a need to protect large amounts of logic with `try/except`, that's usually a sign that the logic needs better condition checks (more `if`/early-`Exit`), not a broader `except`.

---

## 10. Common pitfalls

- **An infinite `while`/`repeat` without a time limit can hang the script permanently.** Every `while`/`repeat` loop that waits on a game state must have a `TCountdown`, a `GetTickCount()` diff, or use `WaitUntil` — never a bare `while <condition> do` without a parallel exit path. See §4.
- **Swallowing all exceptions without logging anything** makes future debugging impossible — you only know that "something went wrong" with no clue where. Log at least `GetExceptionMessage` in every `except` block, even the "unimportant" ones.
- **Terminating without logging out** (`TerminateScript` without a preceding `Logout.ClickLogout`) leaves the account visibly logged in on screen, which is especially dangerous if the script runs unattended or on a farm — a human has to notice and handle it manually. Make logging out a reflex right before every `TerminateScript` call (see §2).
- **Escalating too late or never.** If an action fails silently in a loop without a `ConsecutiveFailedAttempts` counter (§3), the script can sit there trying the same impossible action for hours without anyone (or anything) noticing.
- **Logging unconditionally in tight loops** floods the console/log file and makes it hard to find the actually relevant line when an error occurs. Wrap routine logging behind `DEBUGMODE` (§1).
- **Blindly trusting that an action succeeded** without verifying it (uptext, chat message, a measurable game state) — always pair an action with a way to confirm the result, otherwise failsafes never detect that something went wrong in the first place. (See also `script-anatomy.md` §6 on uptext verification on click.)
- **Forgetting `FreeDTM` in a `finally`** when a function can leave the `try` block via multiple paths (early `Exit`, `Break`, an exception) — leads to memory leaks that accumulate over a long run.
- **Letting a Discord webhook call lack its own `try/except`** — a network error in a notification function should never be able to stop the main logic or, worse, prevent an in-progress `TerminateScript` sequence from completing.

---

## 11. Checklist: building robustness into a new script

When writing a new script (or adding a new activity to an existing one), go through:

1. **Logging:** is there a `WriteMsg`/prefix logging function, and is routine logging conditioned behind `DEBUGMODE`? Are critical errors (failsafes, termination) logged unconditionally?
2. **Every `while`/`repeat` wait:** does it have a `TCountdown`, a `GetTickCount()` diff, or is it expressed as `WaitUntil(condition, interval, timeout)`? Is there ANY wait in the script without an upper time limit?
3. **Every action that can fail systematically** (out of resource, wrong game state): is there a `ConsecutiveFailedAttempts` counter that resets on success and escalates after N attempts?
4. **Chat-based error conditions:** have you identified the exact phrases the game shows for relevant error conditions (out of ammo/runes, degraded equipment, "you are dead", "enough", etc.), and does the script look for them with `Chat.FindMessage`/`Chat.GetMessage`?
5. **Server events:** does the script need to proactively handle a planned shutdown (the `CheckSystemUpdate` pattern) in addition to a simple `ShutdownTime` limit?
6. **Screenshot on critical errors:** is there a `TakeScreenshot` wrapper, and is it called before every critical escalation (before `TerminateScript`)?
7. **External notifications:** if Discord webhooks are used, does EVERY single webhook call sit in its own `try/except`? Is a session summary sent via `AddOnTerminate` where relevant?
8. **`try/except`/`try/finally`:** are they limited to specific, named risks (network, filesystem, DTM allocation, held-down keys) rather than broad sweeps around all logic?
9. **Termination:** does every `TerminateScript` call log out (`Logout.ClickLogout`) right before it, if the account is logged in when the error occurs?
10. **Is the error truly irrevocable?** Double-check that `TerminateScript` is only used for errors that won't resolve by retrying — otherwise, return `False`/`Exit` and let the main loop handle it.
