# Session Handoff: Fortran MCP Server

Hello! If you are an AI assistant starting a new session in this workspace, this handoff document contains everything you need to know about the current status of the project, its files, and what we have set up.

## 🎯 Context & Goal
Modern Fortran (F2003+) is a highly type-safe, modular, and performant language, but AI coding models consistently generate antiquated "AI Slop" (fixed-format, implicit variable types, missing intent attributes, obsolete `real*8` syntax, and legacy common blocks). 

To remediate this, we have developed a local **Model Context Protocol (MCP) Server** named **Fortran Companion** that gives AI models access to compiling, formatting, static linting, and design patterns. When client agents use this MCP server, they can self-correct their code in a loop before presenting it to the user.

---

## 🛠️ Current Project State & Components

1. **Custom Linter ([linter.py](file:///Volumes/home/chest/fortran-mcp/src/fortran_mcp/linter.py)):**
   * Statically parses Fortran lines.
   * Checks for `implicit none` missing at the program/module level and in external procedures.
   * Checks for missing `intent(in/out/inout)` on dummy arguments in subroutines/functions.
   * Checks for non-standard types (`real*8`, `integer*4`) and flags `double precision`.
   * Identifies legacy fixed-format comments and obsolete constructs (`common`, `equivalence`, `goto`, `pause`, arithmetic `if`, `dimension` statements).
   * **Bug Fix (June 2026):** Corrected the fixed-format comment regex `fixed_comment_rx` to check for non-word characters/spaces after `C`/`c`/`*` at column 1. This prevents false positives on standard modern statements (such as `contains` or `call`) when they are written starting at column 1 in free-form files.

2. **MCP Server Entrypoint ([server.py](file:///Volumes/home/chest/fortran-mcp/src/fortran_mcp/server.py)):**
   * Uses `fastmcp` to expose MCP tools.
   * Integrates the custom linter (`lint_code`, `lint_file`).
   * Integrates `fprettify` for auto-formatting (`format_code`, `format_file`).
   * Orchestrates compilation checks via `gfortran` or `fpm` with strict warning flags (`compile_project`).
   * Exposes a `suggest_design_pattern` database describing modern Fortran OOP, Generics, RAII, Callback (Strategy), and C-interoperability patterns.
   * **Bug Fix (June 2026):** Fixed a bug in `format_file` where the `-i` parameter (indentation width) was passed to the `fprettify` CLI without its matching integer argument, causing formatting tasks to crash. We now invoke `fprettify` directly with the file path since it formats in-place by default.

3. **Demonstration & Verification Test Suite ([test/](file:///Volumes/home/chest/fortran-mcp/test/)):**
   * [unformatted_legacy.f90](file:///Volumes/home/chest/fortran-mcp/test/unformatted_legacy.f90): Legacy code intentionally populated with 12 linting violations and bad spacing to demonstrate linter and formatter capabilities.
   * [modern_compliant.f90](file:///Volumes/home/chest/fortran-mcp/test/modern_compliant.f90): A fully compliant F2018 modern program showing proper kind parameters, intents, modular architecture, and modern free-form comments.
   * [illustrate_mcp_tools.py](file:///Volumes/home/chest/fortran-mcp/test/illustrate_mcp_tools.py): Programmatic driver script that lints both files, prints formatting deltas, compiles the compliant code with strict flags, and executes the binary to verify output.

4. **Dependencies & Package ([pyproject.toml](file:///Volumes/home/chest/fortran-mcp/pyproject.toml)):**
   * Managed via `uv`. Key dependencies are `fastmcp` and `fprettify`.
   * Configured CLI entrypoint `fortran-mcp = "fortran_mcp.server:mcp.run"`.

5. **Client Setup Config ([mcp_config.json](file:///Volumes/home/chest/.gemini/antigravity-cli/mcp_config.json)):**
   * Registered in the user's local Antigravity config file so that the AGY agent host boots the server automatically.

---

## 🚀 Key Entrypoints for Next Session

* **Run Demonstration / Verify Setup:** Run the script in the test folder to check formatting, linting, and compiler verification:
  ```bash
  uv run python3 test/illustrate_mcp_tools.py
  ```
* **Launch Server CLI:** Run `uv run fortran-mcp` or `uv run python3 src/fortran_mcp/server.py` to start the server in stdio mode.

---

## 🎯 Next Tasks to Undertake
* **Integrate Test Script into CI/CD:** If a GitHub Action or local testing pipeline is configured, add a step to run `test/illustrate_mcp_tools.py` to assert the linter rules and compiler settings are working.
* **Additional Linter Rules:** Expand `linter.py` rules to check for other legacy items, such as the `data` statement when declaring parameters, or checking if subroutines/functions have explicitly declared return types instead of relying on default implicit types.
