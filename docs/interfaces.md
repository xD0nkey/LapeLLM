# SRL-T / WaspLib: Interfaces (GameTabs, Inventory, Bank, Chat, ChooseOption, Login/Logout, etc.)

This file is a self-instruction (written by me, to myself, for future conversations) about how to
correctly open/close/read RuneScape's fixed UI elements ("interfaces") in Simba/SRL-T/WaspLib scripts.
It goes deeper than `wasplib-script-anatomy.md` (read that one for the helicopter view of script
architecture, walking/`TRSObjectV2`, the antiban layers, and the GUI). Here the focus is solely on
interfaces: opening, closing, checking status, reading content.

Sources I have read line by line to verify this:
- `SRL-T/osr/interfaces/core/interface.simba` (the base class `TRSInterface`/`TRSTitledInterface`)
- `SRL-T/osr/interfaces/gametabs/{gametabs,gametab,inventory,equipment,magic,prayer,logout}.simba`
- `SRL-T/osr/interfaces/core/iteminterface.simba` (`TRSItemInterface`, shared by Inventory/Equipment/Bank/DepositBox)
- `SRL-T/osr/interfaces/mainscreen/{bank,depositbox}.simba`
- `SRL-T/osr/interfaces/chat/{chat,chatbuttons}.simba`
- `SRL-T/osr/interfaces/chooseoption.simba`, `SRL-T/osr/interfaces/login.simba`
- `WaspLib/osr/interfaces/gametabs/inventory.simba`, `WaspLib/osr/interfaces/mainscreen/bank.simba`,
  `WaspLib/osr/interfaces/chat/chat.simba` (WaspLib's overrides of SRL-T)
- My own scripts in `Ny mapp/`, `aeroguardians (4).simba` vs `aeroguardians.simba`, `bigaussie_gemstone_crab_slayer.simba`
  etc., to see actual usage (and actual mistakes) in practice.

---

## 1. The basic pattern: `TRSInterface` and its subclasses

Almost every interface (`Inventory`, `Equipment`, `Bank`, `Chat`, `GameTabs`, `Prayer`, `Magic`,
`DepositBox`, `Login`, ...) is a global variable of a record type that directly or indirectly inherits
`TRSInterface` (defined in `SRL-T/osr/interfaces/core/interface.simba`):

```pascal
TRSInterface = record(TSRLBaseRecord)
  ButtonColors: array of TCTS1Color;
  ButtonEnabledColors: array of TCTS1Color;

  Width, Height: Int32;
  Center: TPoint;
  Bounds: TBox;        // <- FIELD, not a function!
  Rectangle: TRectangle;

  ScrollArea: TBox;
end;
```

`TRSTitledInterface` (inherited by e.g. `Bank` and `DepositBox`) adds `CloseButtonBounds: TBox` and
methods such as `GetTitle()`, `IsTitle(text)`, `ClickCloseButton()`.

**`.Bounds` is a field of type `TBox`, NEVER a method.** Write:

```pascal
WriteLn(Bank.Bounds);          // CORRECT
Mouse.Move(Inventory.Bounds.Middle);   // CORRECT
```

NOT:

```pascal
WriteLn(Bank.Bounds());        // WRONG — doesn't compile (or, worse, compiles against the wrong overload)
```

See §9 "Common pitfalls" — this is a mistake we've made ourselves several times (found verbatim in
`wrath_runecrafter.simba` line 104: `Minimap.Bounds()`, and `ptk_starminer.simba` lines 184/235/245:
`Chat.Bounds()`). The confusion likely comes from the fact that many OTHER types in Simba (`TPointArray`,
`TCuboid`, etc.) actually DO have a `.Bounds()` method (computing a bounding box from points), so the
pattern "`.Bounds()` with parentheses" is valid there but wrong on a `TRSInterface` object.

Every interface normally has:
- `.Setup()` — internal initialization (name, colors), called automatically by `TSRL.Setup()`. You never call this yourself.
- `.SetupAlignment()` — computes `.Bounds` for the current client mode (FIXED/RESIZABLE_CLASSIC/RESIZABLE_MODERN). Called automatically on `TRSClient.ClientModeChanged()`.
- `.IsOpen()` — boolean check, often cheap (only checks color/state), inexpensive to call frequently.
- `.Open()` — attempts to open the interface, returns whether it succeeded.
- `.Close()` — attempts to close (exists on titled interfaces like Bank/DepositBox; gametabs have no "close", you just switch tab).
- `.Draw(bitmap)` — debug drawing, used via `Debug()`/`SRL.Debug()`.

## 2. GameTabs

`GameTabs: TRSGameTabs` (in `gametabs.simba`) manages the 14 tabs (Combat, Stats, Quests, Inventory,
Equipment, Prayer, Magic, Clan, Friends, Account, Logout, Options, Emotes, Music) via the enum `ERSGameTab`.

```pascal
type
  ERSGameTab = (COMBAT, STATS, QUESTS, INVENTORY, EQUIPMENT, PRAYER, MAGIC,
                CLAN, FRIENDS, ACCOUNT, LOGOUT, OPTIONS, EMOTES, MUSIC, UNKNOWN);

  TRSGameTabs = record(TRSInterface)
    Boxes: TBoxArray;   // One box per ERSGameTab, indexable: GameTabs.Boxes[ERSGameTab.INVENTORY]
  end;
```

Central methods:
```pascal
function TRSGameTabs.GetCurrentTab(): ERSGametab;
function TRSGameTabs.Open(tab: ERSGameTab): Boolean;
```

`Open()` clicks multiple times (1 to 3 attempts) until `GetCurrentTab() = tab`, with `WaitUntil` and
`SRL.Dice`-controlled double-click risk built in — you do NOT need to write your own retry loop around this.

```pascal
WriteLn GameTabs.Open(ERSGameTab.INVENTORY);          // open the inventory tab
Mouse.Move(GameTabs.Boxes[ERSGameTab.PRAYER]);         // hover the prayer tab icon without clicking
WriteLn GameTabs.GetCurrentTab() = ERSGameTab.MAGIC;   // check which tab is currently active
```

Each individual tab also has a shared "content box" `GameTab: TRSGameTab` (singular!) — this is the box
for the TAB CONTENT ITSELF (below the tab buttons), separate from `GameTabs` (plural, the tab buttons at
the top/right). Most gametab interfaces (Inventory, Equipment, Prayer, Magic) link their `.SetupAlignment`
to `GameTab.Bounds`, not to `GameTabs.Bounds`. Do not confuse these two variables.

`Bank.IsOpen()` affects `GameTabs.Open()`: an override in `bank.simba` automatically closes the bank if
you try to switch to a tab other than Inventory while the bank is open — good to know, you don't need to
manually close the bank before switching tabs.

## 3. Inventory

`Inventory: TRSInventory` (inherits `TRSItemGameTab` -> `TRSInterface`, plus an internal `Items: TRSItemInterface`
that does all the heavy lifting). 28 slots (0..27, `HIGH_SLOT = 27`).

### Open/status
```pascal
Inventory.IsOpen();   // GameTabs.GetCurrentTab() = ERSGameTab.INVENTORY
Inventory.Open();     // GameTabs.Open(ERSGameTab.INVENTORY)
```
Most `Inventory.X` methods call `Self.Open()` internally and return empty/false if it fails — but don't
blindly rely on that for complex flows; open explicitly if you're going to do several things in a row.

### Finding/counting items
```pascal
Inventory.ContainsItem('Shark');                       // Boolean
Inventory.ContainsAny(['Shark', 'Lobster']);            // Boolean, any of
Inventory.ContainsAll(['Shark', 'Lobster', 'Tuna']);    // Boolean, all of
Inventory.CountItem('Shark');                           // number of slots with Shark (non-stack)
Inventory.CountItemStack('Air rune');                   // reads OFF the stack number (OCR) on a stackable item
Inventory.FindItem('Shark', slot);                      // out Int32 — first matching slot, -1 if not found
Inventory.FindItems(['Shark','Lobster'], slots);        // out TIntegerArray — all matching slots
Inventory.Count();                                      // total number of used slots
Inventory.IsFull();                                     // Count() >= 28
```

### Clicking/hovering — three levels of interaction
```pascal
Inventory.MouseItem('Bronze arrows');                 // ONLY hover, no click — for uptext verification
Inventory.ClickItem('Attack potion(3)');               // left-click (option = '')
Inventory.ClickItem('Ashes', 'Drop');                  // right-click + ChooseOption.Select('Drop')
Inventory.ClickSlot(1);                                // like ClickItem but via slot index instead of name
Inventory.ClickSlot(1, 'Drop');
```
**Rule:** `option` parameter empty string = left-click (fastest, but assumes the left-click default action
is correct). Non-empty `option` = right-click + `ChooseOption.Select(option)` (safer when the default
click is context-dependent or the item has multiple possible left-click actions).

In WaspLib's override of `ClickItem`/`ClickSlot` (in `WaspLib/osr/interfaces/gametabs/inventory.simba`)
an extra safeguard is added: if the uptext contains `'>'` (i.e. a submenu, e.g. "Cast spell on >")
and your `option` does not itself contain `'>'`, the click is automatically cancelled with
`ChooseOption.Select('Cancel')` instead of risking the wrong submenu choice. Good to know if a click
"mysteriously" does nothing — it might be this safeguard that triggered.

### Drop patterns (antiban)
```pascal
Inventory.ShiftDrop(['Maple logs','Willow logs'], DROP_PATTERN_SNAKE);   // shift-click drop, a pattern
Inventory.RightClickDrop(['Ashes'], DROP_PATTERN_REGULAR);                // right-click drop (fallback)
Inventory.RandomPattern();                                                 // randomizes one of the built-in patterns
```
`ShiftDrop` automatically falls back to `RightClickDrop` if `Inventory.ShiftEnabled` is `False`
(automatically set to `False` if shift-click is detected as not working, e.g. the game setting is disabled).

### Other things worth knowing
```pascal
Inventory.IsSlotUsed(slot);          // Boolean — is there anything in the slot
Inventory.GetSelectedSlot();         // -1 if no slot is selected (white outline, "Use" mode)
Inventory.SetSelectedSlot(slot);     // simulates clicking "Use" on an item, then possibly another
Inventory.Use(itemA, itemB);         // combine two items (e.g. Knife + Logs)
Inventory.DiscoverAll();             // OCR/hash-based identification of ALL items right now (slow, debug tool)
```

## 4. Equipment

`Equipment: TRSEquipment` (= `TRSItemGameTab`, same base as Inventory) — 11 slots via `ERSEquipmentSlot`
(HEAD, CAPE, NECK, AMMO, WEAPON, BODY, SHIELD, LEGS, HANDS, FEET, RING — note that SECONDARY_AMMO exists
in the enum but is excluded from slots in `SetupAlignment` since it doesn't visually exist in the UI).

The API is an almost 1:1 mirror of Inventory but for equipment:
```pascal
Equipment.Open();                              // GameTabs.Open(ERSGameTab.EQUIPMENT)
Equipment.IsOpen();
Equipment.ContainsItem('Abyssal whip');
Equipment.FindItem('Abyssal whip', bounds);     // out TBox
Equipment.ClickItem('Abyssal whip', 'Remove');  // right-click + 'Remove' for example
Equipment.ClickSlot(ERSEquipmentSlot.WEAPON);
Equipment.IsSlotUsed(ERSEquipmentSlot.SHIELD);
Equipment.CountGear();                          // number of equipped slots
Equipment.GetButton(ERSEquipmentButton.PRICES); // TRSButton for the buttons below (Stats/Prices/Death/Follower)
```

## 5. Bank

`Bank: TRSBank` (inherits `TRSTitledInterface`). Large and complex — has its own `Items: TRSItemInterface`,
tab handling, search, deposit/withdraw helpers, quantity buttons.

### Open/status/close
```pascal
Bank.IsOpen();                  // by default waits up to 1s for items to appear (waitForItems = True)
Bank.IsOpen(False);              // quick check without waiting for items
Bank.IsOpen(3000);               // overload: wait up to 3000ms
Bank.Close();                    // clicks the X button; Bank.Close(True) presses Escape instead
Bank.WalkOpen();                 // (WaspLib concept, see TBaseBankScript) — walks to and opens the nearest bank
Bank.Open(P: TPoint);            // open via a known screen point (moves the mouse, verifies uptext/ChooseOption)
Bank.Open(Location: ERSBankLocation); // open a specific known bank location (CASTLE_WARS, FEROX, GRAND_EXCHANGE, FALADOR_EAST)
```
**NOTE:** `Bank.Open(P)` relies on `MainScreen.IsUpText(Self.FINDER_UPTEXT)` or `ChooseOption`
— exactly the same uptext-verification pattern described in `wasplib-script-anatomy.md` §6. Never write
your own "guessing" bank-open if you already have a TPoint to the bank; use `Bank.Open(P)`.

### Items: finding, counting, clicking
```pascal
Bank.ContainsItem('Coins');
Bank.FindItem('Coins', box);                              // TRSItem variant, checks ONLY visible items
Bank.FindItem(TRSBankItem.Setup('Coins'), box);           // TRSBankItem variant SEARCHES (switches tab/scrolls as needed!)
Bank.CountItem('Seaweed');                                // sprite-based counting (rarely useful)
Bank.CountItemStack('Coins');                              // OCR-read stack count
Bank.MouseItem('Coins');
Bank.ClickItem('Coins', 'All');                            // right-click + 'All' for example
```
The difference between `FindItem(TRSItem, ...)` and `FindItem(TRSBankItem, ...)` is important: the first
only checks what's already visible on screen, the second (with `TRSBankItem`) actively switches bank tabs
and scrolls until it finds it (or gives up), and caches the position for faster searching next time.

### Withdraw / Deposit
```pascal
// WithdrawHelper is the low-level building block WithdrawItem builds on — you usually call WithdrawItem directly:
Bank.WithdrawItem('Iron full helm', True);                          // True = use the quantity buttons (1/5/10/X/All)
Bank.WithdrawItem(['Iron full helm', 5, False], True);               // TRSBankItem as an array literal: [Item, Quantity, Noted]
Bank.WithdrawItem(TRSBankItem.Setup('Coins', Bank.QUANTITY_ALL), True);

Bank.DepositItem('Logs', True);
Bank.DepositAll();                  // clicks the "Deposit Inventory" button — NOT the same as DepositItem for every item
Bank.DepositEquipment();            // clicks the "Deposit Worn Items" button
```
`Bank.QUANTITY_ALL = -1` and `Bank.QUANTITY_ALL_BUT_ONE = -2` are special values for the `Quantity` field
in `TRSBankItem`, not actual quantities.

### The search field
```pascal
Bank.OpenSearch();                       // clicks the search button, waits until the Chat query "Show items" is open
Bank.IsSearchOpen();                     // Chat.FindQuery('Show items', waitTime)
Bank.ClearSearch();                      // closes the search if a search is already active (title starts with "Showing items:")
Bank.Search('logs');                     // the whole flow: ClearSearch -> OpenSearch -> Chat.AnswerQuery -> verify title
Bank.CloseSearch();                      // ClearSearch + empty AnswerQuery, closes completely
```
**Important:** The search goes through the chat's query system (`Chat.AnswerQuery`), NOT by you manually
sending `Keyboard.Send` letter by letter to the bank's search field. `Chat.AnswerQuery` internally erases
existing text (`Keyboard.PressKey(VK_BACK)` repeated) and then sends the entire string with
`Keyboard.Send(Answer, VK_ENTER)` — so you do NOT need to loop letter by letter yourself, it's already
built in and works on the whole string in one call.

### Tabs
```pascal
Bank.CountTabs();                  // how many bank tabs exist (have content)
Bank.GetCurrentTab();               // which tab is currently selected (0 = "all items")
Bank.OpenTab(3);                    // switch to tab 3
Bank.FindItemTab('Molten glass');   // find WHICH tab an item is in (searches, switches tabs, OCRs the tab number)
```

## 6. DepositBox

`DepositBox: TRSDepositBox` (inherits `TRSTitledInterface`) — very similar to Bank but simpler (no
search, no withdraw buttons, deposit only). Has separate slot arrays for inventory and equipment:

```pascal
DepositBox.IsOpen();                                   // StringMatch against title "... - Deposit Box"
DepositBox.Close();
DepositBox.FindInventoryItem('Logs', box);
DepositBox.FindEquipmentItem('Rune axe', box);
DepositBox.ContainsInventoryItem('Logs');
DepositBox.ClickInventoryItem('Logs', 'Deposit-All');
DepositBox.DepositItem('Logs', True);                  // TRSBankItem/TRSItem variant, like Bank.DepositItem
DepositBox.DepositInventory();                          // clicks the "Deposit Inventory" button (DepositAll is a deprecated alias)
```
The `ERSDepositButton` enum (`LOCK_SETTINGS`, `QUANTITY_1/5/10/CUSTOM/ALL`, `DEPOSIT_WORN/LOOT/INVENTORY`)
mirrors the layout in the UI. `GetButton(button: ERSDepositButton): TRSButton` gives you the button's box
for manual hover/click if you need something `DepositItem` doesn't already handle.

## 7. Chat

`Chat: TRSChat` — the chatbox in the bottom left, 9 rows (`CHAT_MESSAGE_LINES = [0..7]`,
`CHAT_INPUT_LINE = 8`).

### Status
```pascal
Chat.IsOpen();              // color check against the background, or IsTransparent()
Chat.IsTransparent();       // chatbox in "transparent overlay" mode (common with modern client settings)
```

### Failsafe pattern: reading messages
```pascal
Chat.GetMessage(5);                                    // read ROW 5 specifically (all CHAT_MESSAGE_COLORS)
Chat.FindMessage('Buying gf');                           // search ALL rows for a substring
Chat.FindMessage('do not have enough', [CHAT_COLOR_BLACK]); // restrict to a specific CHAT_COLOR_ constant
```
`CHAT_MESSAGE_COLORS` includes `CHAT_COLOR_BLACK/MAROON/BLUE/PURPLE/RED/LIGHT_RED/WHITE/LIGHT_PURPLE/GREEN`.
**The common failsafe pattern** (seen in `aeroguardians`, `bigaussie_gemstone_crab_slayer`, etc.):
```pascal
if Chat.FindMessage('You do not have enough runes', [CHAT_COLOR_BLACK]) then
  // handle the error — e.g. abort the craft state, switch to the gather state
```
Use a specific color when you know it (faster, fewer false matches) — `CHAT_COLOR_BLACK` for regular
system text, `2101487`/`811014` (and other "raw data" color values in hex/dec) show up in older scripts
for special NPC dialogue colors; if you don't know the color, run with the default (all
`CHAT_MESSAGE_COLORS`).

### Dialogue choices / continue
```pascal
Chat.FindOption('Yes');                  // does the option "Yes" exist in the chat right now?
Chat.ClickOption('Yes', True);            // True = use the keyboard (1-9/Space), False = click with the mouse
Chat.ClickContinue(True);                 // click the "Click here to continue" link
Chat.ChatToOption('Yes');                 // click Continue REPEATEDLY until 'Yes' appears, then select it
```
`ChatToOption` is what you want for multi-step NPC dialogues where you only know the end goal, e.g.
"click through all the dialogue until you see the option to trade with the NPC".

### The query system (X/Bank search, NMZ barrels, etc.)
```pascal
Chat.GetQuery();                                          // read the question, e.g. "How many doses?"
Chat.FindQuery('How many doses', 2000);                    // wait up to 2000ms for the query to appear
Chat.AnswerQuery('How many doses', '20', 2000);             // answer, waits, erases the old answer, Enter
```

### Other
```pascal
Chat.GetDisplayName();        // your own OCR-read username in the input row — good failsafe for "are we logged in and is chat ready"
Chat.GetIronManType();        // ERSIronManType, read from the color accent around the name
```
`ChatButtons: TRSChatButtons` is a SEPARATE global variable for the small tab buttons (All/Game/Public/
Private/Channel/Clan/Trade/Report) at the bottom above the chat window — NOT the same as `Chat`. Relevant
if a script needs to mute/filter a chat tab (`ChatButtons.ChangeState(...)`) without it disrupting
failsafe reading via `Chat.FindMessage`. WaspLib's antiban has a `RandomChatTask` that can otherwise
toggle these automatically in the background — override it (see `wasplib-script-anatomy.md` §8) if your
failsafes are sensitive to which chat tab is active.

## 8. ChooseOption (the right-click menu)

`ChooseOption: TRSChooseOption` handles the context menu that appears on right-click. It finds itself
via an embedded bitmap signature, not via a fixed position (the menu can appear anywhere).

```pascal
ChooseOption.IsOpen();                          // is the menu open right now
ChooseOption.IsOpen(3000);                       // wait up to 3000ms for it to open
ChooseOption.Open();                             // right-clicks if it's not already open
ChooseOption.HasOption('Take');                  // does the option exist (without selecting it)
ChooseOption.Select('Take Bones');               // find and SELECT the option (click as default)
ChooseOption.Select(['Bank', 'Use Bank'], MOUSE_LEFT, True, False);  // multiple candidate texts, last = closeIfNotFound
ChooseOption.Hover('Take Bones');                // like Select but only hover (MOUSE_MOVE), no click
ChooseOption.Close();                            // move the mouse away and close the menu
```
Signature (note the parameter order, easy to mix up):
```pascal
function TRSChooseOption.Select(
  text: TStringArray;            // can also be a SINGLE string (another overload exists for String)
  mouseAction: Int32 = MOUSE_LEFT;
  caseSensitive: Boolean = True;
  closeIfNotFound: Boolean = True
): Boolean;
```
`Select()` opens the menu itself if it's not already open — you do NOT need to write `Mouse.Click(MOUSE_RIGHT)`
manually before a `ChooseOption.Select(...)` call.

Submenus ("... >", e.g. "Cast spell on >") are handled automatically: if the main text isn't found but an
entry ending in " >" exists, `Select` automatically tries to open the submenu and look there (`OpenSub`/
`HasSubOption`/`SelectSubOption` internally) — again, you rarely need to handle submenus manually.

## 9. Login / Logout

### Login
`Login: TRSLogin` handles the ENTIRE login flow including error messages, world switching, and Jagex
Launcher detection.

```pascal
Login.AddPlayer('myusername', 'mypassword', '1234', [301, 302]);  // user, pass, pin (bank pin), worlds (for world-hopping)
Login.PlayerIndex := High(Login.Players);                          // select which player to use
if not Login.LoginPlayer() then
  TerminateScript('Failed to login!');
```
`LoginPlayer()` is the ENTIRE flow in one call: waits for the login screen to be ready, fills in
username/password (or handles the Jagex Launcher click if `UsingLauncher()`), handles dialogues
("Try again", "Existing User", etc.) and known `LOGIN_MESSAGES` (wrong password, world full, server down
— with built-in backoff waiting for some), and world switching if a `worlds` list was provided. There's
also an overload `LoginPlayer(randomHop: Boolean; hopChance: Int32 = 30)` if you want more control over
how often the world is switched on each login attempt — otherwise world switching only happens if the
current world isn't in the list, or with a 30% random chance (`SRL.Dice(30)`).

```pascal
Login.SwitchToWorld(303);     // switch to a specific world (regardless of the login flow)
Login.NextPlayer(True);       // go to the next ACTIVE player in the Players list (True = disable the current one)
```

### Logout
`Logout: TRSLogout` (gametab-based, opened via the same `GameTabs.Open` pattern as Inventory/Equipment).

```pascal
Logout.IsOpen();                       // GameTabs.GetCurrentTab() = ERSGameTab.LOGOUT
Logout.Open();                          // GameTabs.Open(ERSGameTab.LOGOUT)
Logout.ClickLogout();                   // the entire flow: open the tab, close the world switcher if open, click, wait it out
Logout.ClickLogout(5, 20000);           // attempts, total time (ms) — the default values
```
`ClickLogout()` is what you want in 99% of cases — it automatically closes an open world switcher before
clicking, and retries up to `attempts` times.

**Pattern for safely ending a script** (seen in several of our scripts):
```pascal
Logout.ClickLogout();
TerminateScript('Done for today');
```
Always log out BEFORE `TerminateScript` if the account is to be left unattended — otherwise you risk the
client staying logged in and visible after the script has stopped.

## 10. Magic

`Magic: TRSMagic` — the spellbook tab. Spells are identified via the `ERSSpell` enum (shared across all
of SRL-T, not defined in magic.simba itself but used here) and an internal `SpellFinder`.

```pascal
Magic.Open();                                       // GameTabs.Open(ERSGameTab.MAGIC)
Magic.GetSpellBook();                                // ERSSpellBook: STANDARD/ANCIENT/LUNAR/ARCEUUS
Magic.IsSpellBook(ERSSpellBook.LUNAR);
Magic.CanActivate(ERSSpell.HIGH_LEVEL_ALCHEMY);      // do we have the level + runes + is the spell unlocked?
Magic.CastSpell(ERSSpell.LOW_LEVEL_ALCHEMY);          // the entire flow: find, click, verify it was cast
Magic.CastSpell(ERSSpell.ICE_BARRAGE, 'Cast');        // with an explicit option if uptext isn't enough
Magic.IsSelected(ERSSpell.ICE_BARRAGE);               // is the spell ACTIVATED (white outline, for auto-cast spells)
```
`CastSpell` internally handles deselecting an already selected spell if another is to be activated
(`Self.Deselect`), and spells like `RS_INSTANT_THROW_SPELLS` (teleports etc. that are cast immediately
without "sticking" as selected) are handled separately in the `IsSelected`/`SpellWasCast` logic — you
don't need to write special cases for teleport spells versus "sticky" combat spells, that's already built in.

## 11. Prayer (and Quick Prayers)

Two SEPARATE global variables: `Prayer: TRSPrayer` (the prayer tab itself, 28 prayers via `ERSPrayer`)
and `QuickPrayer: TRSQuickPrayer` (the quick-select box opened via the minimap orb).

```pascal
Prayer.Open();                                        // opens the prayer TAB (closes QuickPrayer if it was open)
Prayer.GetPrayerLevel();                               // OCR'd current prayer points
Prayer.CanActivate(ERSPrayer.PROTECT_FROM_MELEE);      // do we have the level/is this prayer unlocked?
Prayer.ActivatePrayer(ERSPrayer.PROTECT_FROM_MELEE);   // activate (no-op if already active)
Prayer.ActivatePrayer([ERSPrayer.PIETY, ERSPrayer.PROTECT_FROM_MELEE]);  // multiple at once
Prayer.IsPrayerActive(ERSPrayer.SMITE);
Prayer.DisablePrayer(ERSPrayer.SMITE);
Prayer.GetActivePrayers();                              // array of ERSPrayer, all currently active

QuickPrayer.Open();                                     // opens the quick-prayer box via the Minimap orb + ChooseOption 'Setup'
QuickPrayer.SelectPrayer(ERSPrayer.PROTECT_ITEM);        // SELECT a prayer TO BE INCLUDED in quick prayers (configuration)
QuickPrayer.Close();
```
**Do not confuse** `Prayer.ActivatePrayer` (activates the prayer NOW, requires the prayer tab to be open)
with `QuickPrayer.SelectPrayer` (adds/removes the prayer from the quick-prayer LIST, a configuration
action — does not activate the prayer itself). To actually TURN ON quick prayers (all selected ones at
once) you normally click the minimap orb directly (see `Minimap.Orbs[ERSMinimapOrb.PRAYER]` in the
mapping/minimap file, outside the scope of this file).

## 12. RSInterface — the base class's shared behaviors

Several interfaces (Bank, DepositBox, GrandExchange) share a common `RSInterface.Close(pressEscape)` path
via WaspLib's override layer — if you see `RSInterface.Close(...)` in WaspLib source code, it's the
shared implementation behind `Bank.Close`/`DepositBox.Close`/`GrandExchange.Close`, not a separate
interface you should call directly in your own scripts. In your own scripts you always call the SPECIFIC
interface's `.Close()` (`Bank.Close()`, not `RSInterface.Close()`).

`TRSTitledInterface` (the base for Bank/DepositBox/GrandExchange) gives you for free:
```pascal
SomeInterface.GetTitle();                  // OCR-read title text
SomeInterface.IsTitle('Bank');              // substring check against the title
SomeInterface.ClickCloseButton(pressEscape);// clicks X or presses Escape
```

## 13. Common pitfalls

1. **`.Bounds()` with parentheses.** `TRSInterface.Bounds` is A FIELD (`TBox`), never a method. Write
   `Bank.Bounds`, not `Bank.Bounds()`. We've made this mistake ourselves — found verbatim in
   `wrath_runecrafter.simba` (`Minimap.Bounds()`) and `ptk_starminer.simba` (`Chat.Bounds()` three times).
   The confusion comes from OTHER types (`TPointArray.Bounds()`, `TCuboid.Bounds()`) legitimately HAVING
   a `.Bounds()` method — always check which TYPE the variable has before pasting in `()`.

2. **Forgetting `.Open()` before reading an interface.** Many methods (`ContainsItem`, `FindItem`,
   `CountItem`, etc.) silently return empty/false/-1 if the interface isn't open — they call `Self.Open()`
   internally BUT only exactly when the method runs, not in advance. If you're doing several things in a
   row against the same interface, open it explicitly once at the start of the block instead of relying
   on every single method opening it itself (unnecessary extra GameTabs clicks, and harder to debug if
   something goes wrong).

3. **Mixing up `ClickItem`/`ClickSlot` WITH and WITHOUT the `option` parameter.**
   - Empty `option` (`''`, default) = left-click = "do the default action immediately".
   - Non-empty `option` = right-click + `ChooseOption.Select(option)` = "look up and select a specific option".
   Sending `option` when you actually wanted a quick left-click makes the script unnecessarily slow
   (extra right-click + menu reading). NOT sending `option` when the default click is context-dependent
   (the item changes function dynamically, e.g. a rune pouch's Fill/Empty after a game update — see
   `wasplib-script-anatomy.md` §6/§12) gives a seemingly working but in practice unreliable bot.
   Rule of thumb: if you're unsure what the left-click does right now, use `MouseItem`/`MouseSlot` +
   `MainScreen.IsUpText(...)` verification BEFORE clicking, or go via `option`.

4. **`Inventory` vs `GameTab` vs `GameTabs`.** Three different global variables: `GameTabs` (plural) is
   the tab BUTTONS at the bottom/right; `GameTab` (singular) is the CONTENT AREA below/above the buttons,
   shared between Inventory/Equipment/Prayer/Magic/etc.; each individual interface (`Inventory`, `Equipment`,
   ...) has its OWN `.Bounds` which is typically set equal to `GameTab.Bounds`. Misreading between these
   three is easy when skimming code quickly.

5. **`Bank.FindItem(TRSItem, ...)` vs `Bank.FindItem(TRSBankItem, ...)`.** The first only checks what's
   already visible on screen (no tab switching/scrolling). The second (with `TRSBankItem`, e.g.
   `TRSBankItem.Setup('Coins')`) ACTIVELY searches by switching bank tabs and scrolling. If an item
   search "mysteriously" finds nothing that you KNOW is in the bank, check which overload you happened
   to use.

6. **Trying to write your own character-by-character send to a search field.** Bank search and Chat
   queries (`Chat.AnswerQuery`) already handle erasing old text and sending the whole string in one
   `Keyboard.Send` call. Don't write your own loop with `Keyboard.Send(c)` per letter if
   `Bank.Search`/`Chat.AnswerQuery` already does the job.

7. **Confusing `Prayer.ActivatePrayer` with `QuickPrayer.SelectPrayer`.** The first activates ONE prayer
   NOW (requires the prayer tab to be open). The second configures WHICH prayers are included in the
   quick-prayer button (a completely different, less frequently performed, action).

8. **Assuming `ChooseOption.Select` requires you to right-click yourself first.** It does that for you.
   A double right-click (once manually + once built into `Select`) opens and closes the menu unnecessarily.

## 14. Checklist: new code that interacts with an interface

1. Which interface should I use — is there already a high-level method for what I want to do
   (`Bank.WithdrawItem`, `Inventory.ShiftDrop`, `Chat.ChatToOption`), or do I have to build from lower-level
   building blocks (`MouseItem` + `IsUpText` + `Mouse.Click`)? Prefer high-level if it exists.
2. Is the interface open? If I'm going to do several things in a row against the same interface, open it
   EXPLICITLY once at the top of the block (`if not Bank.IsOpen() then Exit;` or similar) instead of
   relying on every individual method opening it for me.
3. Is the action I want to perform context-dependent/ambiguous (an item that changes appearance/function,
   an NPC with multiple dialogue choices, a right-click menu that can vary)? If yes: verify with uptext
   (`MainScreen.IsUpText`) or go via the `option` parameter/`ChooseOption.Select` instead of blindly
   left-clicking.
4. Am I writing `.Bounds`? Double-check that I did NOT write `.Bounds()` by mistake (see §13.1).
5. Do I need to read off something (text, count, status)? Is there already an OCR/color-based method
   (`Chat.GetMessage`, `Bank.CountItemStack`, `Prayer.GetPrayerLevel`) before I build my own
   `OCR.Recognize`/`SRL.FindColors` solution from scratch.
6. If I'm building a failsafe pattern against the chat: use `Chat.FindMessage`/`Chat.GetMessage` with a
   specific `CHAT_COLOR_*` constant when I know the color, otherwise default (all `CHAT_MESSAGE_COLORS`).
7. Does the script end the account session entirely (not just a task)? Remember `Logout.ClickLogout()`
   BEFORE `TerminateScript(...)`.
8. Is this WaspLib code (not just SRL-T)? Check whether WaspLib has an override that changes the behavior
   (e.g. `Inventory.ClickItem`/`ClickSlot` adds the submenu-cancel safeguard, `Bank.Close` switches to
   `RSInterface.Close`) — read the WaspLib file for the same interface, not just the SRL-T original,
   before assuming exactly what a method does.
