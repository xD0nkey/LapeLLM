# LapeLLM - Usage Guide

This guide explains how to configure and use LapeLLM to interact with Large Language Models (LLMs) using the `lape` scripting engine within your Free Pascal or Delphi applications.

## Table of Contents

* [Installation](#installation)
* [Configuration](#configuration)
    * [API Keys](#api-keys)
    * [LLM Endpoints/Models](#llm-endpointsmodels)
* [Running LapeLLM](#running-lapellm)
* [Scripting LLM Interactions with `lape`](#scripting-llm-interactions-with-lape)
    * [Basic Prompts](#basic-prompts)
    * [Host Scripting API (Conceptual)](#host-scripting-api-conceptual)
    * [Handling Responses](#handling-responses)
    * [Streaming Responses](#streaming-responses)
    * [Advanced Examples](#advanced-examples)
* [Troubleshooting](#troubleshooting)

## Installation

[Reference the README or provide detailed steps for compiling and setting up LapeLLM.]

## Configuration

Proper configuration is essential, especially for API access.

### API Keys

**Never hardcode API keys in your scripts or source code.** LapeLLM should provide secure ways to manage keys:

* **Environment Variables (Recommended):** Set variables like `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`. The host application should read these.
    ```bash
    export OPENAI_API_KEY='your-key-here'
    ```
* **Configuration File:** Use an INI, JSON, or XML file (e.g., `config.ini`) that is *not* checked into version control (add it to `.gitignore`).
    ```ini
    ; Example config.ini
    [LLM_Keys]
    OpenAI=your-openai-key
    Anthropic=your-anthropic-key
    ```
* **Secure Storage:** Use system-specific secure storage if available.

[Explain how LapeLLM expects keys to be provided, e.g., "LapeLLM checks environment variables first, then looks for `config.ini`."]

### LLM Endpoints/Models

You might need to configure:

* **Default Model:** Specify the default LLM to use (e.g., `gpt-4o`, `claude-3-opus-20240229`).
* **API Endpoints:** Override default API URLs if using proxies or specific service regions.
* **Parameters:** Default temperature, max tokens, etc.

[Explain where these settings are configured - e.g., config file, command-line args, or via the `lape` Host API.]

## Running LapeLLM

[Explain how to run the main host application or integrate the LapeLLM library.]

**Example (Command Line Host):**

```bash
# Run a specific lape script
./LapeLLMHost --script scripts/my_llm_task.lape

# Run with specific configuration
./LapeLLMHost --config my_config.ini --script scripts/another_task.lape
```
Scripting LLM Interactions with lape
Use .lape scripts to define your interactions. The host application provides an API (functions, objects) accessible from the script.

###Basic Prompts
```
// scripts/ask_question.lape
program AskQuestion;
var LLM: TLLMInterface; prompt, response: String;
begin
  LLM := Host.GetLLMInterface();
  if not Assigned(LLM) then Exit;

  LLM.SetModel('claude-3-sonnet-20240229'); // Example
  prompt := 'What is the main purpose of the lape scripting engine?';
  response := LLM.Generate(prompt);

  if LLM.HasError then
    Print('Error: ' + LLM.GetLastError)
  else
    Print('Answer: ' + response);
end.
```

Host Scripting API (Conceptual)
The FPC/Delphi host application should expose objects and functions to lape. Here's a conceptual example API:

Host.GetLLMInterface(): TLLMInterface; - Gets the main object for LLM interaction.

Host.LogInfo(message: String); - Logs messages.

Host.LogError(message: String);

TLLMInterface Methods:

SetAPIKey(service: String; key: String); - Set API key for a service ('OpenAI', 'Anthropic'). Often handled by host config.
SetModel(modelName: String); - Select the LLM model.
SetTemperature(value: Single); - Set sampling temperature.
SetMaxTokens(value: Integer); - Set max response tokens.
Generate(prompt: String): String; - Send prompt, wait for, and return the full response.
GenerateStream(prompt: String; callback: TStreamCallback); - Start generation, calling the callback procedure for each received chunk.
HasError: Boolean; - Check if the last operation failed.
GetLastError: String; - Get the last error message.
TStreamCallback = procedure(chunk: String; isFinal: Boolean); - Callback type for streaming.

Note: This API is hypothetical. Refer to the actual LapeLLM source/documentation for the real API.

Handling Responses
The Generate function typically returns the complete text response. Check HasError and GetLastError after calls.

Streaming Responses
For interactive use or long responses, streaming is preferred.
```
// scripts/stream_example.lape
program StreamExample;
var LLM: TLLMInterface; prompt: String; FullResponse: String;
begin
  LLM := Host.GetLLMInterface();
  if not Assigned(LLM) then Exit;

  FullResponse := '';

  // Define the callback procedure within the script
  procedure MyStreamHandler(chunk: String; isFinal: Boolean);
  begin
    Print(chunk); // Print chunk as it arrives
    FullResponse := FullResponse + chunk;
    if isFinal then
      Host.LogInfo('Streaming finished.');
  end;

  prompt := 'Write a short story about a robot learning to use Pascal.';
  LLM.GenerateStream(prompt, @MyStreamHandler); // Pass procedure address

  // Note: GenerateStream might be asynchronous in the host.
  // The host might need to wait for the stream to complete.
  // Or the script might end while streaming continues if not handled.

  if LLM.HasError then
    Print('Error starting stream: ' + LLM.GetLastError);

  // FullResponse can be used later if needed (after isFinal=True)
end.
```
Advanced Examples
[Provide examples of more complex scenarios: multi-turn conversations, function calling (if supported), complex prompt templating within the script, processing structured data (JSON) from LLM responses.]

Troubleshooting
API Key Errors: Ensure keys are correctly configured and valid. Check for 401 Unauthorized or 403 Forbidden errors in logs.
Network Issues: Verify internet connectivity. Check for timeouts or DNS errors.
Rate Limits: You may hit usage limits on the LLM API. Check the specific provider's documentation. Logs might show 429 Too Many Requests.
Script Errors: Check lape syntax. Use Host.LogInfo extensively in scripts for debugging.
Model Not Found: Ensure the model name set via SetModel is correct and available for your API key.
Check Host Logs: The FPC/Delphi application logs are crucial for diagnosing underlying issues (HTTP requests, errors).
Consult LLM Provider Docs: Refer to OpenAI/Anthropic/etc. documentation for API details and error codes.
