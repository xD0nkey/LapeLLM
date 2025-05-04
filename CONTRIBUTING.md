# Contributing to LapeLLM

First off, thank you for considering contributing to LapeLLM! Your involvement helps make this a better tool for the Free Pascal and Delphi communities. Contributions can range from code and scripts to documentation and bug reports.

Please take a moment to review this document to understand how you can contribute effectively.

## How Can I Contribute?

* **Reporting Bugs:** If you find a bug in the host library, `lape` integration, script execution, or LLM communication, please search the [Issues](https://github.com/xD0nkey/LapeLLM/issues) to see if it's already reported. If not, open a new issue with a clear title, detailed description, and steps to reproduce it.
* **Suggesting Enhancements:** Have an idea for a new feature, support for another LLM provider, an improvement to the scripting API, or better documentation? Open an [issue](https://github.com/xD0nkey/LapeLLM/issues) to start a discussion.
* **Code Contributions:** Improve the core Free Pascal/Delphi library (e.g., enhance network handling, add new API bindings, optimize `lape` interaction).
* **Script Contributions:** Write new example `.lape` scripts showcasing different LLM use cases (e.g., few-shot prompting, conversational agents, data extraction).
* **Documentation:** Improve the README, USAGE guide, CHANGELOG, code comments, or add tutorials.

## Getting Started with Development

### Prerequisites

* **Free Pascal/Delphi Environment:** As specified in the [README.md](README.md#prerequisites).
* **IDE (Recommended):** [Lazarus IDE](https://www.lazarus-ide.org/) or RAD Studio/Delphi IDE.
* **Git:** For version control ([https://git-scm.com/](https://git-scm.com/)).
* **LLM API Keys (Optional but Recommended):** For testing integrations, you'll need your own keys. Store them securely (environment variables, user-specific config files) and **never commit them to the repository.**
* **Required Packages:** Ensure you have any FPC/Delphi packages LapeLLM depends on (e.g., Indy, Synapse, JSON processing units).

### Setup

1.  **Fork & Clone:** Fork the repository on GitHub and clone your fork locally:
    ```bash
    git clone [https://github.com/YOUR-USERNAME/LapeLLM.git](https://github.com/YOUR-USERNAME/LapeLLM.git)
    cd LapeLLM
    # Set up the original repository as the 'upstream' remote
    git remote add upstream [https://github.com/xD0nkey/LapeLLM.git](https://github.com/xD0nkey/LapeLLM.git)
    ```
2.  **Configure IDE:** Open the project file (`.lpi` or `.dproj`) in your IDE. Verify that compiler options, unit paths, and dependency paths are correctly configured.
3.  **Build Project:** Compile the project to ensure your development environment is set up correctly.
4.  **Local Configuration (API Keys):** Set up your local environment variables or create necessary configuration files (e.g., copy `config.example.ini` to `config.ini` and add it to `.gitignore`) to store your API keys securely for testing.

## Coding Standards & Style Guide

* **Code Style (Pascal):**
    * Follow standard Object Pascal style conventions (refer to Embarcadero's or Lazarus' guidelines if unsure). Aim for consistency with the existing codebase.
    * Use clear, descriptive names for variables, types, procedures, and functions.
    * Use `begin..end` blocks clearly and indent code logically (e.g., 2 spaces).
    * Comment complex algorithms, non-obvious logic, and public API elements thoroughly.
* **Code Style (`lape` Scripts):**
    * Apply similar Pascal style guidelines within `.lape` files.
    * Keep scripts focused and readable.
    * Comment scripts to explain the purpose, prompt strategy, or expected interaction flow.
* **Testing:**
    * [Describe the project's testing strategy, e.g., using FPCUnit, DUnit, or custom test scripts].
    * Write tests for new features and bug fixes.
    * Consider mocking external API calls (LLMs) for reliable testing of core logic.
    * Ensure all tests pass before submitting a pull request. Run tests using [Specify command or IDE action].
* **Commit Messages:**
    * Write clear and concise commit messages explaining the *what* and *why* of the change.
    * Consider adopting [Conventional Commits](https://www.conventionalcommits.org/) for consistency (e.g., `feat: Add streaming support for OpenAI`, `fix(api): Handle rate limit errors gracefully`, `docs: Clarify API key configuration`).
* **API Keys:** **CRITICAL:** Under no circumstances should API keys or other sensitive credentials be committed to the Git repository. Use `.gitignore` effectively.

## Pull Request Process

1.  **Sync with Upstream:** Ensure your local `main` (or `develop`) branch is up-to-date with the `upstream` repository:
    ```bash
    git checkout main
    git pull upstream main
    ```
2.  **Create a Branch:** Create a new branch for your feature or bugfix:
    ```bash
    # Use a descriptive branch name (e.g., feat/claude-support, fix/json-parsing-error)
    git checkout -b feat/your-feature-name
    ```
3.  **Develop:** Make your changes (Pascal code, `lape` scripts, documentation). Add tests as needed.
4.  **Build & Test:** Ensure the project compiles cleanly and all tests pass.
5.  **Commit:** Commit your changes with clear, descriptive messages. Stage related changes in logical commits.
    ```bash
    git add .
    git commit -m "feat: Implement basic support for Anthropic Claude API"
    ```
6.  **Push:** Push your feature branch to your fork on GitHub:
    ```bash
    git push origin feat/your-feature-name
    ```
7.  **Open a Pull Request (PR):** Go to the [LapeLLM GitHub repository](https://github.com/xD0nkey/LapeLLM) and open a Pull Request from your branch to the project's `main` (or `develop`) branch.
    * Provide a clear title and detailed description for your PR. Explain the changes and link to any relevant issues (e.g., "Closes #123").
    * Ensure any automated checks (CI builds, linters) pass.
8.  **Code Review:** Project maintainers will review your PR. Be responsive to feedback and make necessary changes by pushing additional commits to the *same* branch.
9.  **Merge:** Once the PR is approved and passes all checks, a maintainer will merge it. Thank you for your contribution!

## Questions?

If you have questions about contributing, feel free to open an issue on the [GitHub Issues](https://github.com/xD0nkey/LapeLLM/issues) page.
