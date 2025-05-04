# LapeLLM

LapeLLM helps you generate better code with AI by creating optimized prompts for the Pascal-like Lape scripting language.
Build intelligent prompts, get accurate Lape code, and accelerate your development workflow!

## Simple Setup

Follow these steps to get LapeLLM running.

## Clone the Repo

```bash
git clone https://github.com/xD0nkey/LapeLLM.git
```

## Lape Syntax Overview

Lape (Lightweight Anonymous Pascal Engine) uses familiar Pascal-like syntax:

```pascal
// Variables and types
var
  count: Integer;
  name: String;
  isValid: Boolean;
begin
  count := 10;
  name := 'Lape';
  isValid := True;
  
  // Control structures
  if (count > 5) then
  begin
    WriteLn('Count is greater than 5');
  end;
  
  // Functions
  function Add(a, b: Integer): Integer;
  begin
    Result := a + b;
  end;
end;
```

## Creating Effective Prompts

LapeLLM helps you create optimized prompts that:

1. **Specify Pascal-like syntax** - Ensures the LLM generates proper Lape code
2. **Include clear requirements** - Defines inputs, outputs, and behavior
3. **Provide context** - Explains how the code will be used
4. **Request appropriate documentation** - Gets well-commented, maintainable code

## Contributing

Contributions are welcome! Please feel free to submit PRs for:
* New prompt templates
* Syntax examples
* Documentation improvements
* Feature enhancements
