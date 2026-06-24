# GUI and settings in Simba/WaspLib scripts

This file is a deep dive into a single topic from `script-anatomy.md` (section 9: "GUI and settings"). Read that file for the helicopter view of the entire script architecture; read this file when you're actually going to **build or modify a GUI**.

Based on (path typical for a Windows installation, may vary):
- `%LocalAppData%\Simba\Includes\WaspLib\utils\forms\scriptform.simba` (source for `TScriptForm` and all `Create*` building blocks)
- `%LocalAppData%\Simba\Includes\WaspLib\utils\settings.simba` (source for `TWLSettings`, WaspLib's own global `TConfigJSON` instance)
- `%LocalAppData%\Simba\Includes\WaspLib\utils\config.simba` (source for `TConfigJSON` and `TConfigINI`)
- `%LocalAppData%\Simba\Includes\WaspLib\utils\forms\formutils.simba` (source for `TLabeledEdit`/`TLabeledCheckBox`/`TLabeledComboBox`/`TLabeledPanel`/`TControl.AdjustToDPI`)
- Two generations of the same example GUI code (referred to as "aeroguardians" in the research, an older rev 21 and a newer rev 19/38 style) — not included in this repo
- A large, complex combat script with multiple GUI tabs (referred to as "gemstone crab slayer" in the research) — a good example but also a cautionary example of mixed old/new style; not included in this repo
- Spot samples from roughly 20 additional WaspLib scripts examined during the research, not included in this repo (see the `.simba` policy in the root `README.md`)

---

## 1. Basic structure

All modern WaspLib GUIs follow the same skeleton: a custom record that inherits from `TScriptForm`, a `Run` override that builds the form, and a `StartScript` override that reads the controls when the user clicks "Start!".

```pascal
type
  TConfig = record(TScriptForm)
    // Your own fields you want to be able to access from StartScript and other methods.
    // You CAN declare controls here (Self.MinPoints: TLabeledEdit; etc.)
    // instead of fetching them again with GetChild every time.
    Config: TConfigJSON;
  end;

var
  GUI: TConfig;   // or "Config", "MyForm" etc. - the name doesn't matter

procedure TConfig.StartScript(Sender: TObject); override;
begin
  inherited;   // IMPORTANT - see §7, closes the form/terminates the script on close

  // Read all controls HERE, before the form is gone (see pitfall in §7).
end;

procedure TConfig.Run(); override;
var
  tab: TTabSheet;
begin
  Self.Setup('My Script');             // Creates Self.Form, Self.PageControl, the Self.Start button
  Self.Start.SetOnClick(@Self.StartScript);

  Self.AddTab('Script Settings');
  tab := Self.Tabs[High(Self.Tabs)];

  // ... create your own controls on "tab" here ...

  Self.CreateAccountManager();           // ready-made WaspLib building blocks, see §4
  Self.CreateAntibanManager();
  Self.CreateWaspLibSettings();
  Self.CreateAPISettings();

  inherited;   // MUST be last - shows the form (Sync(@Self.Show)) and sets up RemoteInput
end;

var
  GUI: TConfig;

begin
  GUI.Run();
  // the script continues from here once the user has pressed Start
end.
```

Two things that are easily misunderstood:

- `Self.Setup(...)` is **not** the same as `Self.Run()`. `Setup` only builds the form's shell (window, PageControl, Start button). `Run` is the wrapper that (1) optionally calls your `Setup` logic if you override `Run` entirely, (2) actually shows the window via `Sync(@Self.Show)`, and (3) sets up RemoteInput based on saved settings. **Override `Run`, not `Show`,** and always finish with `inherited;`.
- You can also override `TScriptForm.Setup` instead of `Run` if you want to add things directly into the skeleton build (the new aeroguardians does this, see §5). Both patterns appear in real scripts - pick whichever feels more natural, but never forget `inherited`.

---

## 2. How to create controls

The standard pattern is `with control do begin Create(parent); ... end;`. `parent` is usually a `TTabSheet` (a tab) or a `TPanel`.

Example taken (simplified) from `aeroguardians.simba` (rev 38), `CreateSettingsTab`:

```pascal
var
  lb_Time: TLabel;
  box_Run: TLabeledEdit;
  cb_Breaks: TLabeledCheckBox;
begin
  with lb_Time do
  begin
    Create(Result);                          // Result is a TTabSheet here
    SetLeft(TControl.AdjustToDPI(25));
    SetTop(TControl.AdjustToDPI(10));
    SetFontColor(2145591);
    GetFont().SetSize(15);
    SetCaption('Time settings');
  end;

  with box_Run do
  begin
    Create(Result);
    SetLeft(TControl.AdjustToDPI(5));
    SetTop(TControl.AdjustToDPI(45));
    SetName('box_Run');                      // IMPORTANT - see §3 and §7
    SetCaption('Max run time');              // the label above the field
    SetToolTip('Time in minutes');
    SetText('700');                          // default value
    SetFontColor($00FFFF);
  end;

  with cb_Breaks do
  begin
    Create(Result);
    SetLeft(TControl.AdjustToDPI(25));
    SetTop(TControl.AdjustToDPI(105));
    SetName('cb_breaks');
    SetCaption('Take breaks');
    SetFontColor($00FFFF);
    SetChecked(True);
  end;
end;
```

### Why `TControl.AdjustToDPI(...)` is used everywhere

The source (`formutils.simba`):

```pascal
function TControl.AdjustToDPI(n: Int32): Int32; static;
begin
  Result := Round(n * TControl.GetScreenDPI() / 96);
end;
```

96 DPI is the Windows default ("100% scaling"). If the user has set 125% or 150% screen scaling in Windows, `GetScreenDPI()` will be higher, and every coordinate/size you pass to `SetLeft`/`SetTop`/`SetWidth`/`SetHeight` is scaled proportionally. **If you write raw pixel values without `AdjustToDPI`, the GUI looks fine on your own 96-DPI screen but ends up too small/mis-positioned and bunched together on a user's 125-150% scaled screen.** This is one of the most common copy-paste mistakes seen in scripts (see §7).

Rule of thumb: **every** `SetLeft`, `SetTop`, `SetWidth`, `SetHeight`, `SetMaxLength`-like pixel value should go through `TControl.AdjustToDPI(...)`, unless it's a relative value (`SomeControl.GetRight() + 10` usually isn't sufficient either - the `10` should still be DPI-scaled: `SomeControl.GetRight() + TControl.AdjustToDPI(10)`).

### Ready-made "Labeled" controls

WaspLib has a whole family of "Labeled" wrappers (`formutils.simba`) that combine a `TLabel` + a `TPanel` + the actual control into one package, so you don't have to build a label + field manually every time:

```pascal
TLabeledControl = record
  Panel: TPanel;
  Caption: TLabel;
end;

TLabeledEdit      = record(TLabeledControl)  Edit: TEdit;          end;
TLabeledCheckBox  = record(TLabeledControl)  CheckBox: TCheckBox;  end;
TLabeledComboBox  = record(TLabeledControl)  ComboBox: TComboBox;  end;
TLabeledMemo      = record(TLabeledControl)  Memo: TMemo;          end;
TLabeledPanel     = type TLabeledControl;
```

The most common shortcuts are delegated directly on the wrapper, so you can write `myCheckbox.SetChecked(True)` / `myCheckbox.IsChecked()` without going through `.CheckBox` (source code):

```pascal
procedure TLabeledCheckBox.SetChecked(value: Boolean);
begin
  Self.CheckBox.SetChecked(value);
end;

function TLabeledCheckBox.IsChecked(): Boolean;
begin
  Result := Self.CheckBox.IsChecked();
end;
```

But for things that don't have a shortcut (e.g. `SetOnChange`, `SetOnClick`, `SetStyle(csDropDownList)`) you must go through the underlying control explicitly: `myCombobox.ComboBox.SetOnChange(@Self.SomethingOnChange);`, `myEdit.Edit.SetOnKeyPress(@Edit.NumberField);`.

Example of a dropdown (combobox), a pattern seen in several scripts (`wasp_woodcutter`, `wasp_jewelry_smelter`, etc.):

```pascal
var
  TreeSelector: TLabeledCombobox;
begin
  with TreeSelector do
  begin
    Create(tab);
    SetCaption('Tree:');
    SetLeft(TControl.AdjustToDPI(40));
    SetTop(TControl.AdjustToDPI(170));
    SetStyle(csDropDownList);                 // makes it a pure dropdown (no free text)
    AddItemArray(['Oak', 'Willow', 'Yew']);
    SetItemIndex(0);                          // default selection
    ComboBox.SetOnChange(@Self.OnTreeChange);  // NOTE: via .ComboBox, no shortcut for SetOnChange
  end;
end;
```

`TPanel`/`TImage` are mostly used for background images and visual grouping. A recurring (copy-pasted) pattern in several "students_*" and "aerofisher" scripts:

```pascal
var
  Img: TPicture;
  BGImg: TImage;
begin
  Img.Init();
  Img.LoadFromFile('Resources\MyBackground.png');
  with BGImg do
  begin
    Init(Self.PageControl);
    SetParent(Self.PageControl);
    SetPicture(Img);
    SetBounds(0, 0, Self.Form.GetWidth, Self.Form.GetHeight);
    SetStretch(True);
  end;
end;
```

---

## 3. How to read controls after the GUI has closed

The most common and most fundamental pattern, seen in practically all scripts (old style as well as new), is `Self.Form.GetChild('name')` followed by a type cast to the correct control type:

```pascal
procedure TConfig.StartScript(Sender: TObject); override;
var
  e_Run: TEdit;
  cb_Breaks: TCheckBox;
  MaxRun: Int32;
begin
  inherited;

  e_Run      := Self.Form.GetChild('box_run_edit');     // note the _edit suffix
  MaxRun     := StrToInt(e_Run.GetText());

  cb_Breaks  := Self.Form.GetChild('cb_breaks_checkbox'); // note the _checkbox suffix
  Bot.TakeBreaks := cb_Breaks.IsChecked();
end;
```

### Why the suffixes `_edit` / `_checkbox` / `_combobox`

When you create a `TLabeledEdit` and call `SetName('box_run')`, WaspLib names the **panel** `box_run`, but the underlying `TEdit` control automatically gets the name `box_run_edit` (the same pattern applies for `TLabeledCheckBox` → `_checkbox`, `TLabeledComboBox` → `_combobox`, `TLabeledMemo` → `_memo`). This is exactly why the `GetChild` calls in `StartScript` have these suffixes appended to the name you set with `SetName(...)` on the labeled control.

Type conversion after `GetText()`/`getText`:

```pascal
MaxActions  := StrToInt(edit.GetText());                       // crashes if the text isn't a number
MaxActions  := StrToIntDef(edit.GetText(), 0);                 // safer - defaults to 0 if parsing fails
TakeBreaks  := StrToBoolDef(ReadINI(...), False);               // common in INI patterns, see §7
Length      := Round(StrToFloat(edit.GetText()), 2);
```

**Recommendation:** use `StrToIntDef`/`StrToBoolDef`/`StrToFloatDef` (with a default value) rather than the "strict" variants when the input comes directly from a text field a user can type freely into - otherwise the script terminates with a cryptic error if the user happens to leave the field empty or types letters.

---

## 4. Ready-made WaspLib building blocks

`TScriptForm` (in `scriptform.simba`) gives you five large, ready-built components for free. You call them as methods on your GUI record (they are `TScriptForm` methods, i.e. available through inheritance) from within your `Run`/`Setup` override:

| Method | Returns | What you get |
|---|---|---|
| `Self.CreateAccountManager()` | `TTabSheet` (own tab) | Complete account management: select/add/update/remove account, username, password, bank pin, world list. Writes/reads directly against `Login.Players` and `credentials.simba`. |
| `Self.CreateAccountManager(owner: TControl)` | `TPanel` (overload) | Same content but as a panel you place yourself on an existing tab, instead of a whole new tab. |
| `Self.CreateAntibanManager()` | `TTabSheet` | BioHash trackbar, on/off for camera/mouse/chat/gametabs/bank tasks, short breaks, sleep settings (hour, length, biohash-driven or manual). Reads/writes against `WLSettings` (WaspLib's global `TConfigJSON`, see §5). |
| `Self.CreateBankSettings()` | `TTabSheet` | Bank selection (`RSBankRegions`) + a visual map image where you right-click-drag to view/confirm the bank zone. |
| `Self.CreateWaspLibSettings(limits: Boolean = True)` | `TTabSheet` | Video-on-crash setting, RemoteInput settings (HUD report/debug/transparent, block real input), and if `limits=True` also max actions/max time. |
| `Self.CreateAPISettings()` | `TTabSheet` | WaspStats UUID/password management (show, copy, change) plus an optional visible username for statistics. |

Practical example (simplified variant of WaspLib's own documentation example in `scriptform.simba`):

```pascal
procedure TConfig.Run(); override;
var
  tab: TTabSheet;
begin
  Self.Setup('My Script');
  Self.Start.SetOnClick(@Self.StartScript);

  Self.AddTab('Script Settings');
  tab := Self.Tabs[High(Self.Tabs)];

  Self.CreateAccountManager(tab);     // as a panel, on our own tab

  // ... your own controls on "tab" here ...

  Self.CreateVersionPanel(tab);       // shows SRL-T/WaspLib/script version + latest version
  Self.CreateAntibanManager();        // own tab
  Self.CreateBankSettings();          // own tab
  Self.CreateWaspLibSettings();       // own tab
  Self.CreateAPISettings();           // own tab

  inherited;
end;
```

**Reuse these instead of rebuilding account management/antiban GUI yourself.** In `aeroguardians (4).simba` (rev 21) and rev 38, the entire account management is already `Self.CreateAccountManager()` - it is *not* handwritten in any of the scripts we reviewed. Writing your own account manager with your own INI rows for users/passwords is extra code, extra surface for bugs, and you lose things like the automatic `RewriteCredentials()` sync against `credentials.simba` and the `Antiban.SetupBiometrics()` link that `CreateAccountManager` handles automatically on account switch.

`CreateBankSettingsV2` also exists (a newer, simpler variant that returns a `TLabeledComboBox` instead of a whole tab+map image) - seen in `wasp_enchanter.simba` and `wasp_herblore.simba`. Use it if you just want a simple bank dropdown embedded in an existing tab, not a full map viewer.

---

## 5. The `TConfigJSON` pattern for saving settings

`TConfigJSON` (source: `config.simba`) is a general JSON file wrapper:

```pascal
TConfigJSON = record
  Path: String;
  JSON: TJSONObject;
  IsSetup, OnTerminate: Boolean;   // internal, don't touch these
end;
```

The basic flow, once per script:

```pascal
type
  TConfig = record(TScriptForm)
    Config: TConfigJSON;
  end;
```

`Self.Config.Setup('scriptname')` is called **once**, conveniently in your `Run` or `Setup` override (the new aeroguardians does it in `Setup`):

```pascal
procedure TConfig.Setup(caption: String = 'Script Form'; size: TPoint = [750, 500]; allowResize: Boolean = False); override;
begin
  inherited;
  Self.Config.Setup('aeroguardians');   // creates/opens Configs/aeroguardians.json
  // ... the rest of your custom setup (background image, Start button redesign, etc.) ...
end;
```

`Setup('scriptname')` doesn't look for a path separator in the string → the file ends up at `AppPath + 'Configs' + DirectorySeparator + 'scriptname.json'` (`.json` is appended automatically if you haven't already written it).

**Complete pattern around ONE control** (create → read saved value if it exists, otherwise default → save new value on Start), taken from real code in `aeroguardians.simba` (rev 38):

When building the control (in your tab-build function):

```pascal
with cb_Frags do
begin
  Create(Result);
  SetLeft(TControl.AdjustToDPI(270));
  SetTop(TControl.AdjustToDPI(100));
  SetName('cb_frags');
  SetCaption('Auto-fragments');
  SetToolTip('Mine fragments until the first portal appears');
  if Self.Config.Has('autofrags') then
    SetChecked(Self.Config.GetBoolean('autofrags'))   // restore saved value
  else
    SetChecked(True);                                  // otherwise: hardcoded default
end;
```

In `StartScript` (when the user presses Start), read AND save at the same time:

```pascal
procedure TGUI.StartScript(Sender: TObject); override;
var
  cb_Frags: TCheckBox;
begin
  inherited;

  cb_Frags        := Self.Form.GetChild('cb_frags_checkbox');
  Bot.AutoFrags   := cb_Frags.IsChecked();
  Self.Config.Put('autofrags', cb_Frags.IsChecked());   // saved to disk immediately (save=True is the default)
end;
```

Same pattern for text fields, just with `GetString`/`SetText`:

```pascal
// Build:
if Self.Config.Has('droprunes') then
  SetText(Self.Config.GetString('droprunes'))
else
  SetText('Body');

// Start:
Self.Config.Put('droprunes', e_RDrop.GetText());
```

The API in brief (`config.simba`):
- `Setup(jsonFile: String = ScriptName)` - open/create the JSON file.
- `Put(key, value)` - overloads exist for `String`/`Int32`/`Double`/`Boolean`/`Pointer` (the pointer variant for nested `TJSONObject`/`TJSONArray`). Saves to disk immediately by default (`save: Boolean = True`).
- `Has(key, nullIsValid: Boolean = True)` - check whether the key exists before reading it.
- `GetString`/`GetInt`/`GetDouble`/`GetBoolean`/`GetObject`/`GetArray` - read out a value (returns empty/0/False if the key is missing - does NOT crash, but you should still `Has`-check to distinguish "never saved" from "saved as false/empty string" when that matters for default values).
- `Remove(key)`, `DeleteConfig()`, `ToString(indentFactor)`.

WaspLib has its own global instance, `WLSettings: TWLSettings` (in `settings.simba`), which is `record(TConfigJSON)` with extra typed fields/methods (`MaxActions()`, `SetAntibanCamera(state)`, etc. on top of raw `Get`/`Put`). It is set up automatically by WaspLib itself (`TSRL.Setup` calls `WLSettings.Setup('wasplib')`) and drives, among other things, `CreateAntibanManager`/`CreateWaspLibSettings` internally - you normally do **not** need to touch `WLSettings` directly, but it's good to know it exists and already persists antiban/remote-input/video settings separately from your own `Self.Config`.

### Difference from `TConfigINI`

`config.simba` also contains `TConfigINI`, a thin wrapper around the older global `ReadINI`/`WriteINI`/`DeleteINI` functions:

```pascal
ConfigINI.Setup('MyScriptSettings.ini');
ConfigINI.Put('GUISettings', 'UsePoolPOH', 'True');
WriteLn(ConfigINI.Get('GUISettings', 'UsePoolPOH'));
```

It exists and works, but the WaspLib direction is `TConfigJSON`. Write new scripts against `TConfigJSON`.

---

## 6. Tabs and panels - organizing many settings

`Self.AddTab(caption: String)` adds a new `TTabSheet` to `Self.PageControl` and to the `Self.Tabs` array:

```pascal
Self.AddTab('Script Settings');
tab := Self.Tabs[High(Self.Tabs)];   // get the just-created tab to keep building on it
```

The caption is automatically sanitized into an internal name (`LowerCase`, spaces → `_`), so `'Script Settings'` internally becomes `script_settings` - this only matters if you later want to fetch the tab via `Self.Form.GetChild('script_settings')` instead of `Self.GetTab('Script Settings')`.

For several tabs in a row, break out each tab into its own function that returns a fully built `TTabSheet`, and call them in sequence in `Run`/`Setup`:

```pascal
procedure TConfig.Run(); override;
begin
  Self.Setup('My Script');
  Self.Start.SetOnClick(@Self.StartScript);

  Self.AddTab(Self.CreateGeneralTab());     // pattern seen in the bigaussie script
  Self.AddTab(Self.CreateFarmRunTab());
  Self.AddTab(Self.CreateUITab());

  Self.CreateAccountManager();
  Self.CreateAntibanManager();

  inherited;
end;
```

`bigaussie_gemstone_crab_slayer.simba` has three of its own tabs ("Script Settings", "Farm Run Settings", "UI Settings") in addition to WaspLib's own - it is the most complex example of tab organization we've seen, and a good reference if you need to group a lot.

**Within a tab**, use `TLabeledPanel` to visually group related controls (heading + frame) instead of scattering loose labels across the whole tab. Pattern from bigaussie:

```pascal
function TConfig.CreateLabeledPanel(owner: TControl; title: String; top, height: Int32;
  fontSize: Int32 = 10; color: TColor = clBlack; fontStyles: TFontStyles = [fsBold];
  centerCaption: Boolean = True): TLabeledPanel;
begin
  Result.Create(owner);
  with Result do
  begin
    SetCaption(title);
    Panel.SetBevelWidth(1);
    Panel.SetBevelInner(bvRaised);
    Panel.SetBevelOuter(bvLowered);
    Panel.SetTop(top + TControl.AdjustToDPI(3));
    Panel.SetWidth(Self.Form.GetWidth - TControl.AdjustToDPI(25));
    Panel.SetHeight(TControl.AdjustToDPI(height));
    Caption.SetFontSize(fontSize);
    Caption.SetFontColor(color);
    Caption.GetFont().SetStyle(fontStyles);
  end;
end;
```

Then all controls for that group are created with `owner := minPanel` instead of `owner := tab`, so they end up visually framed.

**Practical rule:** more than ~10-15 controls on a single tab without panels/grouping quickly becomes unmanageable (we have seen tabs with 20+ unlabeled `TLabel`/`TLabeledCheckBox` variables in a single `var` section). Break out into separate tabs or `TLabeledPanel` groups as soon as a tab starts to feel cramped.

---

## 7. Common pitfalls

1. **The `GetChild` name doesn't exactly match what you set with `SetName`.** Remember the suffix rules in §3: a `TLabeledEdit` with `SetName('box_run')` produces an underlying `TEdit` under the name `box_run_edit`, NOT `box_run`. If you forget the suffix you get `nil` back from `GetChild`, and the next call (`.GetText()` on `nil`) crashes. We have seen real examples of exactly this kind of name mismatch in `students_only_farm_and_bhruns.simba` (a `GetChild('lcb_fguildtp_combobox')` where the neighboring variables consistently use the `_caption` suffix - likely a copy-paste bug).

2. **Reading controls BEFORE the form has closed / wrong order of `inherited`.** The `StartScript` override must call `inherited` (which calls `Self.Form.Close()`), but you can still read control values AFTER that - the form is visually closed but the objects are still alive until the procedure returns. What actually goes wrong in practice is if you try to read controls in a completely different procedure that runs after the `TConfig` instance has already gone out of scope, or if you forget `inherited` entirely (in which case the window never closes - the user sees a frozen GUI that does nothing when Start is clicked).

3. **Forgotten `TControl.AdjustToDPI(...)`.** Raw pixel values (`SetLeft(325)`, `SetTop(3)`) work perfectly on your own machine but end up mis-positioned or too small on a screen with different Windows scaling. We have found several examples of this in real scripts (`charter_shop_crafting (1).simba`, `bigaussie_gemstone_crab_slayer.simba`) sitting in the middle of code that otherwise consistently DPI-scales - this often happens when a control is copied and the new number is left unwrapped.

4. **Mixing old INI style with new JSON style in the same script.** `bigaussie_gemstone_crab_slayer.simba` is a concrete example: it uses `Self.CreateAccountManager(tab)` (a modern WaspLib building block) AND its own `ReadINI`/`WriteINI` calls against a handwritten `Configs/BASettings.ini` file with dozens of `WriteINI(Username + ' Gemstone Crab Settings', 'UseBoosts', BoolToStr(...), 'Configs/BASettings.ini')` lines in a `SaveUserSettings` procedure. It works, but:
   - You maintain two completely different persistence APIs in the same file.
   - The INI style requires YOU to manually type-convert every value (`BoolToStr`/`StrToBoolDef`/`IntToStr`/`StrToIntDef`) in both directions, while `TConfigJSON.Put`/`GetBoolean` does it for you.
   - There is a risk that one setting gets saved in the `.ini` file while another, related setting ends up saved in the `.json` file (or WaspLib's own `WLSettings`) - hard to find "where is X actually saved" when reading the code later.
   - **If you're building something new: pick `TConfigJSON` throughout. Never migrate new INI calls into a script that already uses `TConfigJSON`, and vice versa.**

5. **Forgetting `Self.Config.Has(key)` before `SetChecked`/`SetText` with a saved value.** If you simply write `SetChecked(Self.Config.GetBoolean('x'))` without a `Has` check, new users (without a saved config) will always get `False`/an empty value instead of your intended default. The pattern should always be `if Self.Config.Has(key) then <set saved value> else <set default>;` (see §5).

6. **Rebuilding account management/antiban GUI by hand.** See §4 - there is rarely a good reason to write your own `TEdit`-based login box or your own antiban on/off checkboxes when `CreateAccountManager`/`CreateAntibanManager` already exist, are tested, and are correctly wired against `Login.Players`/`WLSettings`/`Antiban.SetupBiometrics()`.

7. **Forgetting `SetOnClick`/`SetOnChange` on the correct sub-control.** On a `TLabeledComboBox`/`TLabeledCheckBox`/`TLabeledEdit` there is no shortcut for `SetOnChange`/`SetOnClick` (only for things like `SetChecked`/`IsChecked`/`SetEnabled`). You must write `minControl.ComboBox.SetOnChange(...)` / `minControl.CheckBox.SetOnChange(...)` / `minControl.Edit.SetOnKeyPress(...)` - if you forget the `.ComboBox`/`.CheckBox`/`.Edit` part you get a compile error or (worse) set the event on the wrong object.

---

## 8. Checklist for a new GUI in a new script

1. **Define `TConfig = record(TScriptForm)`** (or `TGUI`, the name doesn't matter) with a `Config: TConfigJSON` field if you have your own settings to save.
2. **Override `Run()` (or `Setup()`)**: `Self.Setup('Name')` → `Self.Start.SetOnClick(@Self.StartScript)` → build tabs/controls → `Self.Config.Setup('scriptname')` somewhere early → finish with `inherited;`.
3. **Reuse WaspLib's building blocks** (`CreateAccountManager`, `CreateAntibanManager`, `CreateBankSettings`/`CreateBankSettingsV2`, `CreateWaspLibSettings`, `CreateAPISettings`, `CreateVersionPanel`) for everything they already cover - only build your own controls for what's unique to your script.
4. **Each of your own controls:** `Create(parent)` → `SetName(...)` (unique, you'll need it in `StartScript`) → `SetLeft`/`SetTop` always through `TControl.AdjustToDPI(...)` → `SetCaption`/`SetText`/`SetChecked` with a default → if savable: `if Self.Config.Has(key) then <restore> else <default>`.
5. **Override `StartScript(Sender: TObject)`**: `inherited;` FIRST → read each control via `Self.Form.GetChild('name_suffix')` (remember the `_edit`/`_checkbox`/`_combobox` suffixes for Labeled controls) → type-convert safely (`StrToIntDef`/`StrToBoolDef`) → save each value with `Self.Config.Put(key, value)`.
6. **Group** more than a handful of controls per tab into `TLabeledPanel`, and break out into more tabs (`Self.AddTab`) rather than cramming everything onto one.
7. **Stick to a single persistence style** (`TConfigJSON`) throughout the script - don't mix in `ReadINI`/`WriteINI` "just for one thing".

**Recommendation for new scripts:** `TConfigJSON` + maximum reuse of WaspLib's `Create*` building blocks. This is clearly where both the WaspLib source code and the most recent script revisions (aeroguardians rev 38 compared to rev 21) point.
