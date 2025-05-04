# LapeLLM

LapeLLM integrates Large Language Models (LLMs) into [Free Pascal / Delphi] applications, leveraging the **lape** scripting engine for flexible prompt engineering, interaction control, and response handling. Define your LLM interactions using simple Pascal-like scripts.

## ✨ Features

* Interact with various LLMs (e.g., GPT models, Claude, etc.) via API calls.
* Define complex LLM interaction logic using **lape** scripts.
* Easily integrate LLM capabilities into existing or new [Free Pascal / Delphi] projects.
* Provides a host API for `lape` scripts to manage prompts, parameters, and process results.
* Designed for speed and broad platform compatibility inherent to FPC/Delphi and `lape`.

## 🚀 Getting Started

### Prerequisites

* **Free Pascal Compiler (FPC):** Version `[e.g., 3.2.2]` or later, **OR** **Delphi:** Version `[e.g., 11 Alexandria]` or later.
    * [Lazarus IDE](https://www.lazarus-ide.org/) is recommended for FPC development.
* **`lape` Scripting Engine:** Ensure the `lape` engine units provided within this project are correctly referenced.
* **LLM API Keys:** You will likely need API keys for the specific LLM services you intend to use (e.g., OpenAI, Anthropic). Store these securely (see Configuration).
* [Any other dependencies, e.g., specific FPC/Delphi packages like Indy or Synapse for HTTP requests].

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/xD0nkey/LapeLLM.git](https://github.com/xD0nkey/LapeLLM.git)
    cd LapeLLM
    ```
2.  **Compile the Host Application/Library:**
    * **Using Lazarus:** Open `LapeLLM.lpi` (or the main project file) and choose `Run > Build`.
    * **Using Delphi:** Open `LapeLLM.dproj` (or the main project file) and choose `Project > Build LapeLLM`.
    * **Using FPC command line:**
        ```bash
        # Adjust command as needed for your project structure
        fpc LapeLLMHost.pas -O3 -o LapeLLMHost
        ```
3.  **Configure API Keys:** Set up your LLM API keys securely. This might involve environment variables, a configuration file, or secure storage. See [Usage Guide](USAGE.md#configuration). **Do not commit API keys directly into the repository.**
4.  **Prepare Scripts:** Review the example `.lape` scripts in the `scripts/` directory.

### Quick Start / Basic Usage

**Example `lape` Script (`scripts/simple_prompt.lape`):**

```pascal
// Example lape script for a simple LLM prompt
program SimplePrompt;

var
  LLM: TLLMInterface; // Assuming host provides an LLM interface object
  prompt: String;
  response: String;

begin
  // Get the LLM interface provided by the host
  LLM := Host.GetLLMInterface(); // Hypothetical host function

  if not Assigned(LLM) then
  begin
    Host.LogError('LLM Interface not available.');
    Exit;
  end;

  // Configure the LLM call (optional, might use defaults)
  // LLM.SetModel('gpt-4o');
  // LLM.SetTemperature(0.7);

  prompt := 'Explain the concept of "prompt engineering" in one sentence.';

  Host.LogInfo('Sending prompt to LLM: ' + prompt);
  response := LLM.Generate(prompt); // Synchronous generation

  if LLM.HasError then
    Host.LogError('LLM Error: ' + LLM.GetLastError)
  else
  begin
    Host.LogInfo('LLM Response Received.');
    // Assuming 'Print' is exposed by the host to show output
    Print('LLM Response:');
    Print(response);
  end;
end.
```

For detailed usage, configuration, scripting API, and more examples, see the Usage Guide.

### 📖 Documentation
* Usage Guide: Detailed instructions, configuration (API keys!), lape scripting for LLMs, and the Host API reference.
* Contributing Guide: How to contribute to LapeLLM.
* Changelog: History of changes to the project.

### 🤝 Contributing
Contributions are welcome! Help improve the core library, add support for more LLMs, write example scripts, or enhance documentation.

### 📧 Contact
For issues or questions, please use the GitHub Issues page.
