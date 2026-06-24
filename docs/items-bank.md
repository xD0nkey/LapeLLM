# Items, Inventory and Bank — practical deep dive

This file covers the daily craft: how item names/IDs are handled under the hood,
how to build a bank loadout, how to do withdraw/deposit robustly, and which pitfalls
keep recurring in bank-based AIO/farm scripts. The basic
Inventory/Bank API (`Inventory.Open`, `Bank.IsOpen`, etc.) is covered briefly in the file about
"interfaces" — see also `script-anatomy.md` for how
an entire script fits together around this. Everything here is verified against the source code in:

- `SRL-T\utils\items.simba` (TRSItem/TRSItemArray + helper functions)
- `SRL-T\osr\interfaces\mainscreen\bank.simba` (TRSBank, TRSBankItem, WithdrawHelper, FindItem, Search, DepositAll/Items)
- `SRL-T\osr\interfaces\core\item_interface.simba` (TRSItemInterface — the base that both `Inventory` and `Bank.Items` inherit from)
- `WaspLib\osr\interfaces\mainscreen\bank.simba` (DepositRandomItems, DepositAllBut)
- Multiple real scripts examined during research, including examples that use `WithdrawHelper`/`ProgressiveBankSearch` and `TRSBankItem` loadouts

---

## 1. TRSItem and TRSItemArray — it's just a Variant

The source says it all:

```pascal
type
  TRSItem = Variant;
  TRSItemArray = array of TRSItem;
```

`TRSItem` is **not** a string type, it is a `Variant`. This means that one and the same
array can freely mix strings (item names) and integers (item IDs):

```pascal
const
  POUCH: TRSItemArray = ['Medium pouch', 5511];
```

### Why name OR ID, and why sometimes both for the same logical item

- **Name is the default.** Most API calls (`Bank.FindItem`, `Inventory.ContainsItem`,
  `Bank.Search`, etc.) take an item name that you recognize from the game, e.g.
  `'Coins'`, `'Shark'`, `'Adamantite bar'`.
- **ID is used when the name is ambiguous or items share a sprite.** Under the hood,
  `ItemFinder` (see `item_interface.simba`, `ItemFinder.Find`/`FindAll`) matches items against a
  hash database of sprites — the name is really just a key into that database.
  Some items have identical or nearly identical sprites but different names/IDs depending on
  state (charge level, wear, quantity). In that case it is safer to reference them directly by
  ID.
- **Mixed name+ID arrays are used for "the same logical item, multiple variants".**
  The classic example is pouches in Runecrafting: a pouch can be intact or have degraded into
  a degraded/cheaper variant with a different name and ID, but you want your
  "do I have a pouch" check to hit both. By writing
  `['Medium pouch', 5511]` you are telling `ContainsAny`/`FindItem`/`Bank.FindAny`:
  "match if ANY of these exist" — you avoid having to write separate handling code for each
  variant.
- The same principle is used for equipment that degrades (e.g. Barrows sets) or items
  that have a "(broken)"/"(charged)" variant — list all known name/ID variants in a
  constant array once, reuse that array in all checks.

**Practical rule:** when you write code that needs to recognize "one item, regardless of its
exact state," define a `TRSItemArray` constant with all name/ID variants and
use `ContainsAny`/`FindAny` against it — don't write separate `if` branches for every
variant.

```pascal
const
  ANY_RUNE_POUCH: TRSItemArray = ['Rune pouch', 'Rune pouch(l)', 'Divine rune pouch'];

if Inventory.ContainsAny(ANY_RUNE_POUCH) then
  ...
```

### Comparison and conversion

`TRSItemArray.Find`/`Contains` compare via `VarToStr`, i.e. an ID is compared as its
string representation — `5511` and `'5511'` are equivalent in that comparison, but an
ID NEVER matches a name (`5511 <> 'Medium pouch'` as values — they're only the same
*logical* item according to your own array). The point of listing both is not that they are
"equal" to Lape, but that your own search array contains all known representations.

---

## 2. Check and count functions — which one should I use?

These exist on `TRSItemInterface` (the base for both `Inventory` and `Bank.Items`) and on
`TRSItemArray` itself (pure array operations, no screen reading). Two completely different
layers — don't mix them up:

| Need | Array level (no screen reads) | Interface level (`Inventory.`/`Bank.`, reads the screen) |
|---|---|---|
| Does X exist in the list/inventory? | `TRSItemArray.Contains(item)` | `Inventory.ContainsItem(item)` / `Bank.ContainsItem(item)` |
| Does ANY of several exist? | `TRSItemArray.ContainsAny(items)` | `Inventory.ContainsAny(items)` / `Bank.ContainsAny(items)` |
| Do ALL of several exist? | `TRSItemArray.ContainsAll(items)` | `Inventory.ContainsAll(items)` |
| How many slots/occurrences? | `TRSItemArray.Count(item)` | `Inventory.CountItem(item)` / `Bank.CountItem(item)` |
| How big is the stack? | — | `Inventory.CountItemStack(item)` / `Bank.CountItemStack(item)` |

### CountItem vs CountItemStack — the most common beginner bug

- **`CountItem`** counts the number of **slots/occurrences** of an item. For a
  non-stackable item (e.g. `'Shark'` occupying 5 separate slots) this gives the correct
  count: 5.
- **`CountItemStack`** reads the **stack number** shown in the corner of the slot. For a
  stackable item (e.g. `'Coins'`, `'Feather'`, runes) the ENTIRE quantity sits in ONE slot —
  `CountItem('Coins')` gives `1` (one slot occupied), not the balance. You must use
  `CountItemStack('Coins')` to get the real count.

```pascal
// WRONG for stackable items:
if Inventory.CountItem('Coins') >= 1000 then ...   // gives number of SLOTS (0 or 1), not coins!

// CORRECT:
if Inventory.CountItemStack('Coins') >= 1000 then ...
```

A robust pattern for when you don't know in advance whether an item is stackable (e.g. a
generated loadout item) is to test the stack first and fall back to `CountItem`
if the stack is 0 — that is exactly what a larger example script does:

```pascal
function TScript.GetInventoryItemQuantity(item: TRSItem): Int32;
var
  stackCount: Int32;
begin
  stackCount := Inventory.CountItemStack(item);
  if stackCount > 0 then
    Result := stackCount
  else
    Result := Inventory.CountItem(item);
end;
```

`Bank.CountItem` has its own quirk worth knowing about (from the documentation comment
in `bank.simba`): it counts items that share the same sprite/icon in the bank view, which in
extremely rare cases (the example in the source: Edible seaweed / Seaweed / Giant seaweed)
can give surprising results — rely on `CountItemStack` for actual quantities and
`FindItem`/`ContainsItem` for exact name matching when it's critical.

---

## 3. Bank loadouts: TRSBankItem and "what I want in my inventory"

### TRSBankItem — the definition

```pascal
TRSBankItem = record
  Item: TRSItem;
  Quantity: Int32;
  Noted: Boolean;
end;

function TRSBankItem.Setup(item: TRSItem; quantity: Int32 = -1; noted: Boolean = False): TRSBankItem; static;
```

`Quantity` accepts the special values `Bank.QUANTITY_ALL` (take everything available) and
`Bank.QUANTITY_ALL_BUT_ONE`, in addition to regular integers. You can build a `TRSBankItem`
either via `.Setup(...)` or as a shorthand array (`['Iron full helm', 5, False]`),
since Lape can implicitly convert a literal array into a record with the same
field order.

```pascal
var
  helm: TRSBankItem;
begin
  helm := TRSBankItem.Setup('Iron full helm', 5, False);
  // equivalent shorthand:
  Bank.WithdrawItem(['Iron full helm', 5, False], True);
```

### Build a loadout as a TRSBankItemArray

The standard pattern (seen in several WaspLib-style examples and a larger modern script) is to declare the loadout as a field on the
script's main record and populate it once in `Init`/`Setup`:

```pascal
type
  TScript = record
    InventoryLoadout: TRSBankItemArray;
  end;

procedure TScript.SetupLoadout();
begin
  Self.InventoryLoadout := [
    TRSBankItem.Setup('Shark', 10),
    TRSBankItem.Setup('Prayer potion(4)', 4),
    TRSBankItem.Setup('Ring of wealth(i)', 1, False),
    TRSBankItem.Setup(Self.Bar, -1)          // -1 = "as many as needed/possible"
  ];
end;
```

Note the common style where each loadout item is stored in its
own named field (`Self.BarB`, `Self.OreB`, `Self.CoalB`, ...) instead of a loose
array — useful when different parts of the script need to reference *that specific* item object
(e.g. to change its `.Quantity` dynamically at runtime based on price calculations).
Use the array form when the loadout is static and just needs to be "iterated through"; use
named fields when individual items need individual logic.

### The HandleBankItems pattern: compare current state against the loadout, withdraw the difference

The dominant flow in all of these scripts is not "withdraw a fixed list every
time," but **"check what I already have, only withdraw what's missing."** This makes the
script resilient to interrupted runs (if you already have 6 of 10 sharks left
in your inventory, you should not withdraw 10 more).

Pattern, based on `GemStoneCrabSlayer.GetItemsToWithdraw` + `HandleBankItems`:

```pascal
function TScript.GetItemsToWithdraw(): TRSBankItemArray;
var
  loadoutItem: TRSBankItem;
  have, need: Int32;
begin
  Result := [];
  for loadoutItem in Self.InventoryLoadout do
  begin
    have := Inventory.CountItem(loadoutItem.Item);   // switch to CountItemStack if stackable!
    need := loadoutItem.Quantity - have;

    if need > 0 then
      Result += TRSBankItem.Setup(loadoutItem.Item, need, loadoutItem.Noted);
    // need <= 0: already have enough of this item, skip it
  end;
end;

function TScript.HandleBankItems(): Boolean;
var
  toWithdraw: TRSBankItemArray;
  item: TRSBankItem;
begin
  if not Bank.IsOpen() then
    Exit(False);

  toWithdraw := Self.GetItemsToWithdraw();
  if Length(toWithdraw) = 0 then
    Exit(True);   // inventory is already complete, nothing to do

  Result := True;
  for item in toWithdraw do
    if not Bank.WithdrawItem(item, True) then
      Result := False;   // log/handle, see the withdraw pattern in section 4
end;
```

This "diff against the loadout" approach is the same principle that `Bank.DepositRandomItems`
uses in the opposite direction (see section 5): you describe the **target state** ("this is
what I want to keep" or "this is what I want to get rid of"), and the function figures out what
actually needs to be done given the current inventory — you never loop over raw
slot information yourself.

---

## 4. Withdraw with retry and search-field fallback (the complete pattern)

This is the core of robust bank code. `Bank.FindItem(item: TRSBankItem; ...)` already
tries on its own to find the item by looking through visible tabs/scroll positions (see
`bank.simba` line ~1197–1241: it caches where an item was last found and tries up to
2 extra attempts with tab-switching/scrolling). But when the bank is large, unorganized, or
the item is in a tab you don't want to open manually, the **search field** is the robust
route — and the search field itself has its own pitfalls (closes unexpectedly, requires
restarting the input).

### Step 1: Try the simple route first

```pascal
if Bank.FindItem(item, itemBox) then
  Bank.WithdrawHelper(itemBox, quantity, False, False)
```

`Bank.FindItem` (the TRSBankItem variant) actually searches the bank (switches tabs, scrolls)
— if it succeeds you already have the box and can withdraw directly without touching the search field.

### Step 2: If that fails, open the search field and type letter by letter

This is the `ProgressiveBankSearch` pattern from a larger example script.
The reason for typing letter by letter (instead of sending the whole
string at once) is twofold: (1) it looks more human for antiban purposes, and (2)
the search results in the bank interface update progressively — after only 1–2 letters the
list may still show TOO MANY results (see the pitfall in section 6), so you wait and
check only after a minimum number of characters before looking for a match:

```pascal
function TScript.ProgressiveBankSearch(item: TRSItem; out itemBox: TBox): Boolean;
var
  searchText, currentSearch: String;
  i, j, minLetters: Int32;
begin
  Result := False;
  searchText := item;
  minLetters := Min(3, Length(searchText));   // NEVER type fewer than 3 letters

  if not Bank.ClearSearch() then
    Exit(False);

  if not Bank.IsSearchOpen() then
    if not Bank.OpenSearch(Random(2000, 2500)) then
      Exit(False);   // could not open the search field at all

  currentSearch := '';
  for i := 1 to Length(searchText) do
  begin
    currentSearch += searchText[i];
    Keyboard.Send(searchText[i]);

    // Wait longer after minLetters (the bank has time to reshuffle the results),
    // shorter before that (we don't have enough letters for a meaningful match anyway)
    if i >= minLetters then
      Wait(Random(1000, 2000))
    else
      Wait(Random(70, 200));

    // The search field can close unexpectedly (e.g. due to game events) — detect and recover
    if not Bank.IsSearchOpen(1200) then
    begin
      if not Bank.ClearSearch() then Exit(False);
      if not Bank.OpenSearch(Random(2000, 2500)) then Exit(False);

      // Retype EVERYTHING from the start, not just the last letter
      currentSearch := '';
      for j := 1 to i do
      begin
        currentSearch += searchText[j];
        Keyboard.Send(searchText[j]);
        Wait(IfThen(j >= minLetters, Random(1000, 2000), Random(70, 100)));
      end;
    end;

    // Check for a match no earlier than after minLetters letters
    if (i >= minLetters) and Bank.FindItem(item, itemBox) then
      Exit(True);
  end;

  // Typed the entire name and still found nothing
  Result := False;
end;
```

### Step 3: The full withdraw function with a bounded number of attempts and a clear termination

The outermost layer combines steps 1–2 in a loop with a maximum number of attempts, and if
everything fails the script terminates in a controlled manner rather than continuing blindly:

```pascal
function TScript.WithdrawHelper(item: TRSItem; quant: Int32): Boolean;
var
  attempts: Int32;
  itemBox: TBox;
begin
  if Self.GetInventoryItemQuantity(item) >= quant then
    Exit(True);   // already done, nothing to withdraw

  // Require at least 1-2 free slots BEFORE attempting the withdraw (see pitfall 6.3)
  if Inventory.CountEmptySlots() < 2 then
    TerminateScript('Inventory has no empty slots to withdraw item ' + item);

  for attempts := 0 to 2 do
  begin
    if Bank.FindItem(item, itemBox) then
      Bank.WithdrawHelper(itemBox, quant, False, False)
    else if Self.ProgressiveBankSearch(item, itemBox) then
      Bank.WithdrawHelper(itemBox, quant, False, False);

    if WaitUntil(Self.GetInventoryItemQuantity(item) >= quant, 35, 3000) then
      Exit(True);   // verified: the item actually arrived in the inventory

    if attempts < 2 then
      Wait(Random(500, 1000));
  end;

  // Three attempts made, still no result — give up clearly and loudly
  TerminateScript('Failed to withdraw "' + item + '" after 3 attempts');
end;
```

Three things to always include in a withdraw call, in this order:

1. **Check whether it's already done** before touching the bank at all.
2. **Check for free slots** before withdrawing (see section 6).
3. **Verify the result** after withdrawing with `WaitUntil(... CountItem/CountItemStack ...)`
   — never assume that a successful button press means the item actually landed in the
   inventory (it can fail due to lag, a full inventory, an anti-bot popup, etc.).

---

## 5. Deposit patterns

### DepositAll — the simple variant

```pascal
Bank.DepositAll();
```

Just clicks the "Deposit inventory" button. Use it when you want to empty everything
(typically right after arriving at the bank, before withdrawing a new loadout).

### Selective deposit — keep some items, deposit the rest

The common need in farm/AIO scripts: you have a set of items you ALWAYS want to
keep (talismans, teleport items, tools, rune pouches) and want to deposit everything
else (harvested crops, empty seed packets, etc.) without enumerating every single item you want to
get rid of. `Bank.DepositRandomItems` (WaspLib) does exactly this — you list
**the exceptions** (what should STAY), and the function deposits the rest:

```pascal
Bank.DepositRandomItems([
  'Rune pouch', 'Divine rune pouch', 'Magic secateurs', 'Spade', 'Seed dibber',
  'Air rune', 'Water rune', 'Earth rune', 'Fire rune', 'Law rune',
  "Xeric's talisman", 'Hosidius teleport', 'Construct. cape', 'Farming cape'
]);
```

(Example taken from an older real script — where the talisman
`"Xeric's talisman"` is exactly the kind of item that is deliberately excluded from deposit
because you want to reuse it for fast transport, not sell/store it every
bank run.)

For depositing specific, named items (the opposite — an explicit whitelist of WHAT
should be deposited, not what should be kept) you use `Bank.DepositItems`:

```pascal
Bank.DepositItems(['Raw shark', 'Empty seed packet'], True);   // useQuantityButtons=True
```

or per-item with a quantity via `TRSBankItemArray`:

```pascal
Bank.DepositItems([
  TRSBankItem.Setup('Raw shark', Bank.QUANTITY_ALL),
  TRSBankItem.Setup('Coins', 1000)   // deposit only 1000, keep the rest
], True);
```

`DepositAllBut` (older, `deprecated` in WaspLib in favor of `DepositRandomItems`) did
the same "keep these" job but operated on a specific tab — avoid it in new scripts.

### DepositEquipment

```pascal
Bank.DepositEquipment();
```

Clicks "Deposit worn items." Good to run before `DepositAll`/withdrawing a new
equipment set so that old worn items end up in the bank instead of staying on the
character.

---

## 6. Common pitfalls

### 6.1 Bank search can show TOO MANY results after only 1-2 letters

The search field filters progressively as you type, but after, say, only "co," it still
matches `'Coal'`, `'Coins'`, `'Cooked karambwan'`, etc. If you check for a match
too early you risk getting box coordinates for the WRONG item (or finding a false
positive if your search term is a substring of another item's name). Always type at least
3 letters (`minLetters := Min(3, Length(searchText))`) before you start looking for
a match, and keep typing until `Bank.FindItem` actually matches — don't rely on
3 letters always being enough for short names (if the entire name is 3 letters or shorter,
`Min` ensures you type the whole name).

### 6.2 Stackable items require CountItemStack, otherwise you get the wrong count

Already covered in section 2, but worth repeating as a rule: **if you don't know whether an
item is stackable, test `CountItemStack` first and fall back to `CountItem` if the
result is 0.** Never write code that assumes `CountItem` gives the "real count" for
an item you don't 100% know is non-stackable (this applies especially to items that vary:
runes, ammunition, food in some cases, currency, certain raw materials).

### 6.3 No free inventory slots before a withdraw

If the inventory is full (or has only 0-1 free slots and you're about to withdraw several
different items), the withdraw button will either do nothing, or only partially fill —
and your `WaitUntil` verification after the withdraw will then time out, wasting your
3 retry attempts on a problem that has nothing to do with the bank at all. Check
`Inventory.CountEmptySlots() < N` (at least 1-2, depending on how many distinct new
items you're going to withdraw in that bank session) BEFORE touching the search field or
`Bank.FindItem`, and `TerminateScript` with a clear error message if it doesn't
check out — otherwise you mask a configuration error (too many GUI selections,
wrong loadout size) as a bank error.

### 6.4 The search field can close unexpectedly mid-typing

The game client can close the search field (chat messages, other popup queries, certain
server events) between keystrokes. If you don't check `Bank.IsSearchOpen()`
after EVERY letter, the rest of your string risks going to the wrong place (e.g. the chat
or the main window) instead of the search field. The pattern in section 4 (step 2) handles
this by verifying after every letter that the search field is still open, and
if not: reopening it and **retyping the ENTIRE string from the start** (not just
continuing where it was interrupted) — otherwise the search result could end up matching a
different substring than the one you intend.

### 6.5 Confusing TRSItemArray operations (pure array comparisons) with Interface operations (screen reading)

`TRSItemArray.Contains` is a pure in-memory comparison between values you already have in an
array — it reads NOTHING from the screen. `Inventory.ContainsItem`/`Bank.ContainsItem`
actually read the game client. For example, building a local `TRSItemArray` of "items I've
already seen this session" and then mistakenly believing that calling `.Contains()` on that
array says something about the current game state is a common logical mistake — keep "what I
remember" and "what is actually visible on screen right now" separate.

### 6.6 Assuming a successful button press equals a successful transaction

`Bank.WithdrawHelper`/`WithdrawItem` returns `True` if the interaction (click/
quantity selection) went through, NOT a guarantee that the item actually landed in the
inventory. Lag, full slots, or the bank closing at just that moment can make the interaction
"succeed" while the inventory never changes. Always verify with
`WaitUntil(Inventory.ContainsItem/CountItem/CountItemStack ...)` afterward, as in
the pattern in section 4.

---

## 7. Checklist — before writing item/bank code in a new script

1. **Define the loadout once, declaratively.** A `TRSBankItemArray`
   (`Self.InventoryLoadout`) or named `TRSBankItem` fields set up in
   `Setup`/`Init` — not ad-hoc `Bank.WithdrawItem(...)` calls scattered through the flow.
2. **Decide name vs. ID per item.** If the item can have multiple states/variants
   (degraded, charged, noted), build a `TRSItemArray` constant with all known
   names/IDs and use it consistently in all `ContainsAny`/`FindAny` calls for that
   logical item.
3. **Determine stackability in advance** for each item in the loadout, or write a
   generic `GetQuantity` helper function that tries `CountItemStack` → falls back to
   `CountItem` (see section 2/3).
4. **Write "diff against the loadout" logic**, not a fixed withdraw list: compute what is
   missing (`needed := loadout.Quantity - have`) before touching the bank.
5. **Implement withdraw with three layers:** (a) `Bank.FindItem` directly, (b) the search field
   letter-by-letter with at least 3 characters and closed-search-field detection, (c) a
   maximum total number of attempts (typically 3) followed by `TerminateScript` with a specific
   error message (which item, how many attempts).
6. **Check for free slots before withdrawing**, not only afterward.
7. **Decide on a deposit strategy:** `DepositAll` for "empty everything," `DepositRandomItems`
   with an exception list for "keep these specific items (talismans, tools,
   pouches)," `DepositItems` for an explicit whitelist of what should go.
8. **Verify every withdraw/deposit operation** with `WaitUntil` against the
   `Inventory` state — never rely solely on the return value of the click function.
9. **Log (WriteLn) every withdraw/deposit decision** during development — "need X,
   have Y, withdrawing Z" — it's the single most valuable piece of debug information when
   a bank loop hangs.
