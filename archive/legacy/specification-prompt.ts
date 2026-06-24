import { BUILDWARE_MAX_INPUT_TOKENS } from "@/lib/constants/buildware-config" // [cite: 1]
import endent from "endent" // [cite: 1]
import { estimateClaudeTokens } from "../../estimate-claude-tokens" // [cite: 1]
import { limitCodebaseTokens } from "../../limit-codebase-tokens" // [cite: 1]

export const SPECIFICATION_PREFILL = "<specification>" // [cite: 1]

export const buildSpecificationPrompt = async ({
  issue,
  codebaseFiles,
  instructionsContext,
  partialResponse
}: {
  issue: {
    name: string
    description: string
  }
  codebaseFiles: {
    path: string
    content: string
  }[]
  instructionsContext: string
  partialResponse?: string
}) => {
  // --- Lape/Simba Adapted Anthropic System Prompt Text ---
  // Note: This text is provided for completeness but the code below defaults to the OpenAI template.
  /*
    const systemPromptAnthropic_LapeAdapted = endent`
      You are an expert Simba scripter, proficient in the Lape language (Pascal dialect) and its use within the Simba automation environment. You are familiar with common Simba libraries and concepts like SRL, RSWalker, Bank interactions, Inventory management, TPoints, TBoxes, Records, Procedures, and Functions.

      You will be given an existing codebase (likely .simba files using Lape syntax), a task (often involving automation within Simba), general instructions & guidelines, and response instructions. Pay attention to includes ({$I ...}), existing procedures, functions, type definitions, and var/const declarations in the codebase.

      Your goal is to use this information to build a high-level specification for the task, suitable for guiding the implementation of a Lape script.
      This specification will be passed to the plan step, which will use it to create a detailed plan for implementing the Lape script.

      To create the specification:
      - Break down the automation task into logical steps suitable for a Lape script structure (e.g., initialization, main loop, specific action procedures).
      - Provide an overview of what needs to be done without diving into Lape code-level details (e.g., focus on the purpose of procedures/functions, required data structures like records or arrays, necessary logic flow).
      - Focus on the "what" (e.g., 'Walk to specified coordinates', 'Handle banking logic') rather than the "how" (specific Lape code implementation).
      - Mention conceptually relevant Lape constructs or Simba library components where appropriate (e.g., 'Need a record to store state', 'Use RSWalker for navigation', 'Requires if..then..else logic', 'Loop using for..in..do').
      - Specify necessary Lape data types conceptually ('Store coordinates as TPoint', 'Use Integer for counts').
      - Outline necessary procedures and functions: what they need to accomplish and potentially what parameters they might need, but do not write their begin...end blocks.

      The specification should NOT:
      - Include work that is already done in the codebase.
      - Include specific Lape code snippets (e.g., variable assignments, loop bodies).
      - Include low-level implementation details like specific pixel coordinates or exact color values unless critical to the specification step itself.

      Use <scratchpad> tags to think through the process as you create the specification. Consider:
      - Which Lape data types are needed?
      - Is this step best as a procedure or function?
      - Are relevant SRL/library functions available?
      - Which Lape control structures fit?
      - How does this fit the overall program...begin...end. structure?`
  */

  // --- Lape/Simba Adapted Anthropic User Message Template Text ---
  // Note: This text is provided for completeness but the code below defaults to the OpenAI template.
  /*
    const userMessageTemplateAnthropic_LapeAdapted = endent`
      # Existing Lape Codebase (.simba files)

      First, review the existing Simba/Lape codebase you'll be working with:

      <codebase>
        {{CODEBASE_PLACEHOLDER}}
      </codebase>

      ---

      # Task (Simba Automation)

      Next, review the task information, likely involving automation within Simba:

      <task>
        <task_name>${issue.name || "No name provided."}</task_name>
        <task_details>
          ${issue.description || "No details provided."}
        </task_details>
      </task>

      ---

      # Instructions and Guidelines (for Lape/Simba)

      Keep in mind these general instructions and guidelines while working on the task:

      <instructions>
        ${instructionsContext || "No additional instructions provided."}
      </instructions>

      ---

      # Response Instructions

      When writing your response, follow these instructions:

      ## Response Information

      Respond with the following information:

      - SPECIFICATION: The high-level specification for the Lape/Simba script task.
      - SCRATCHPAD: A scratchpad for your thoughts on Lape/Simba implementation details, library usage, data types, procedures/functions needed, etc. Scratchpad tags can be used anywhere in the response. There is no limit to the number of scratchpad tags you can use.
      - STEP: A step in the specification, outlining a logical part of the Lape script's functionality or structure in markdown format.

      ## Response Format

      Respond in the following format:

      <specification>
        <scratchpad>__SCRATCHPAD_TEXT_LapeSpecificThinking__</scratchpad>
        <step>__STEP_TEXT_LapeSpecific__</step>
        ...remaining steps...
      </specification>

      ## Response Example

      An example response:

      <specification>
        <scratchpad>Need to decide if RSWalker is required for this task. Will likely need TPoint variables.</scratchpad>
        <step>Initialize required Simba libraries (e.g., SRL) and setup RSWalker if navigation is needed. Declare necessary global variables and constants (e.g., target locations as TPoint, item names as String).</step>
        <scratchpad>This part seems like it should be a separate procedure for better organization.</scratchpad>
        <step>Implement the main loop (e.g., using 'while True do'). Inside the loop, check script conditions (e.g., player location using RSW.GetMyPos, inventory status using Inventory.FindItem).</step>
        ...remaining steps...
      </specification>

      ---

      Now, based on the task information, existing Lape codebase, and instructions provided, create a high-level specification for implementing the task as a Simba script. Present your specification in the format described above.`
  */

  // --- Lape/Simba Adapted OpenAI User Message Template ---
  // This is the template the code will use by default below.
  const userMessageTemplateOpenai_LapeAdapted = endent`
    You are an expert Simba scripter, proficient in the Lape language (Pascal dialect) and its use within the Simba automation environment. You are familiar with common Simba libraries and concepts like SRL, RSWalker, Bank interactions, Inventory management, TPoints, TBoxes, Records, Procedures, and Functions.

    You will be given an existing codebase (likely .simba files using Lape syntax), a task (often involving automation within Simba), general instructions & guidelines, and response instructions. Pay attention to includes ({$I ...}), existing procedures, functions, type definitions, and var/const declarations in the codebase.

    Your goal is to use this information to build a high-level specification for the task, suitable for guiding the implementation of a Lape script.
    This specification will be passed to the plan step, which will use it to create a detailed plan for implementing the Lape script.

    To create the specification:
    - Break down the automation task into logical steps suitable for a Lape script structure (e.g., initialization, main loop, specific action procedures).
    - Provide an overview of what needs to be done without diving into Lape code-level details (e.g., focus on the purpose of procedures/functions, required data structures like records or arrays, necessary logic flow).
    - Focus on the "what" (e.g., 'Walk to specified coordinates', 'Handle banking logic') rather than the "how" (specific Lape code implementation).
    - Mention conceptually relevant Lape constructs or Simba library components where appropriate (e.g., 'Need a record to store state', 'Use RSWalker for navigation', 'Requires if..then..else logic', 'Loop using for..in..do').
    - Specify necessary Lape data types conceptually ('Store coordinates as TPoint', 'Use Integer for counts').
    - Outline necessary procedures and functions: what they need to accomplish and potentially what parameters they might need, but do not write their begin...end blocks.

    The specification should **NOT**:
    - Include work that is already done in the codebase.
    - Include specific Lape code snippets (e.g., variable assignments, loop bodies).
    - Include low-level implementation details like specific pixel coordinates or exact color values unless critical to the specification step itself.

    # Existing Lape Codebase (.simba files)

    First, review the existing Simba/Lape codebase you'll be working with:

    <codebase>
      {{CODEBASE_PLACEHOLDER}}
    </codebase>

    ---

    # Task (Simba Automation)

    Next, review the task information, likely involving automation within Simba:

    <task>
      <task_name>${issue.name || "No name provided."}</task_name>
      <task_details>
        ${issue.description || "No details provided."}
      </task_details>
    </task>

    ---

    # Instructions and Guidelines (for Lape/Simba)

    Keep in mind these general instructions and guidelines while working on the task:

    <instructions>
      ${instructionsContext || "No additional instructions provided."}
    </instructions>

    ---

    # Response Instructions

    When writing your response, follow these instructions:

    ## Response Information

    Respond with the following information:

    - SPECIFICATION: The high-level specification for the Lape/Simba script task.
    - STEP: A step in the specification, outlining a logical part of the Lape script's functionality or structure in markdown format.

    ## Response Format

    Respond in the following format:

    <specification>
      <step>__STEP_TEXT_LapeSpecific__</step>
      ...remaining steps...
    </specification>

    ## Response Example

    An example response:

    <specification>
      <step>Initialize required Simba libraries (e.g., {$I SRL/osr.simba}) and setup necessary components like RSWalker if navigation is needed. Declare necessary global variables (`var`) and constants (`const`) (e.g., target locations as TPoint, item names as String).</step>
      <step>Implement the main script logic within a primary loop (e.g., using 'while True do'). Inside the loop, include checks for script conditions (e.g., player location using RSW.GetMyPos, inventory status using Inventory.FindItem or specific counts).</step>
      <step>Define separate procedures for distinct actions like banking (e.g., procedure HandleBanking) or specific tasks (e.g., procedure PerformPrimaryAction). These procedures should encapsulate logic related to interacting with game elements using SRL functions.</step>
      ...remaining steps...
    </specification>

    ---

    Now, based on the task information, existing Lape codebase, and instructions provided, create a high-level specification for implementing the task as a Simba script. Present your specification in the format described above.` // [cite: 1] adapted for Lape/Simba

  // --- Original Code Logic (Mostly Unchanged) ---

  // CHANGE BASED ON PROVIDER (Using the Lape-adapted OpenAI template)
  const systemPrompt = "" // OpenAI models often use the user message for system context // [cite: 1]
  const userMessageTemplate = userMessageTemplateOpenai_LapeAdapted // [cite: 1] modified

  const systemPromptTokens = estimateClaudeTokens(systemPrompt) // [cite: 1]
  const userMessageTemplateTokens = estimateClaudeTokens(userMessageTemplate) // [cite: 1]
  const usedTokens = systemPromptTokens + userMessageTemplateTokens // [cite: 1]
  let availableCodebaseTokens = BUILDWARE_MAX_INPUT_TOKENS - usedTokens // [cite: 1]

  if (partialResponse) { // [cite: 1]
    const tokensToRemove = estimateClaudeTokens(partialResponse) // [cite: 1]
    availableCodebaseTokens -= tokensToRemove // [cite: 1]
  }

  const codebaseContent = limitCodebaseTokens( // [cite: 1]
    codebaseFiles, // [cite: 1]
    usedTokens, // [cite: 1]
    availableCodebaseTokens // [cite: 1]
  )
  const userMessage = userMessageTemplate.replace( // [cite: 1]
    "{{CODEBASE_PLACEHOLDER}}", // [cite: 1]
    (match, offset) => // [cite: 1]
      offset === userMessageTemplate.indexOf(match) ? codebaseContent : match // [cite: 1]
  )

  let finalUserMessage = userMessage // [cite: 1]

  if (partialResponse) { // [cite: 1]
    const partialSpecification = // [cite: 1]
      partialResponse.match(/<specification>([\s\S]*)/)?.[1] || "" // [cite: 1]
    // Adjusted continuation instructions slightly for clarity
    const continuationInstructions = endent`
      ---

      # Continuation Instructions

      You have already started generating the specification. Continue from where you left off.
      Here is the specification you've generated so far:

      ${partialSpecification}

      Complete the specification based on the full task, codebase, and instructions provided earlier.` // [cite: 1] adapted text
    finalUserMessage += `\n\n${continuationInstructions}` // [cite: 1]
  }

  return { // [cite: 1]
    systemPrompt, // [cite: 1]
    userMessage: finalUserMessage, // [cite: 1]
    prefill: partialResponse // [cite: 1]
      ? partialResponse.slice(-100) // Keep a smaller slice for prefill consistency // [cite: 1] adapted slice
      : SPECIFICATION_PREFILL // [cite: 1]
  }
}
