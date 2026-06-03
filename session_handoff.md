# Session Handoff: Fortran MCP Server

Hello! If you are an AI assistant starting a new session in this workspace, this handoff document contains everything you need to know about the current status of the project, its files, and what we have set up.

## 🎯 Context & Goal
Modern Fortran (F2003+) is a highly type-safe, modular, and performant language, but AI coding models consistently generate antiquated "AI Slop" (fixed-format, implicit variable types, missing intent attributes, obsolete `real*8` syntax, and legacy common blocks). 

To remediate this, we have developed a local **Model Context Protocol (MCP) Server** named **Fortran Companion** that gives AI models access to compiling, formatting, static linting, and design patterns. When client agents use this MCP server, they can self-correct their code in a loop before presenting it to the user.

---

## 🛠️ Current Project State & Components

1. **Custom Linter ([linter.py](file:///Volumes/home/chest/fortran-mcp/src/fortran_mcp/linter.py)):**
   * Statically parses Fortran lines.
   * Checks for `implicit none` missing at the program/module level and in external procedures (nested module procedures inherit correctly and are handled).
   * Checks for missing `intent(in/out/inout)` on dummy arguments in subroutines/functions.
   * Checks for non-standard types (`real*8`, `integer*4`) and flags `double precision`.
   * Identifies legacy fixed-format comments and obsolete constructs (`common`, `equivalence`, `goto`, `pause`, arithmetic `if`, `dimension` statements).
2. **MCP Server Entrypoint ([server.py](file:///Volumes/home/chest/fortran-mcp/src/fortran_mcp/server.py)):**
   * Uses `fastmcp` to expose MCP tools.
   * Integrates the custom linter (`lint_code`, `lint_file`).
   * Integrates `fprettify` for auto-formatting (`format_code`, `format_file`).
   * Orchestrates compilation checks via `gfortran` or `fpm` with strict warning flags (`compile_project`), supporting custom standard flags (e.g. `-std=f2018`).
   * Integrates project bootstrapping (`initialize_project`) that writes modular modern template files and Makefiles.
   * Exposes a `suggest_design_pattern` database describing modern Fortran OOP, Generics, RAII, Callback (Strategy), and C-interoperability patterns.
3. **Dependencies & Package ([pyproject.toml](file:///Volumes/home/chest/fortran-mcp/pyproject.toml)):**
   * Managed via `uv`. Key dependencies are `fastmcp` and `fprettify`.
   * Configured CLI entrypoint `fortran-mcp = "fortran_mcp.server:mcp.run"`.
   * Checked and built successfully into `.whl` and `.tar.gz` in `dist/`.
4. **Client Setup Config ([mcp_config.json](file:///Volumes/home/chest/.gemini/antigravity-cli/mcp_config.json)):**
   * Registered in the user's local Antigravity config file so that the AGY agent host boots the server automatically in future sessions.

---

## 🚀 Key Entrypoints for Next Session

* **Test Linter Script:** Run the scratch script `uv run python3 /Volumes/home/chest/.gemini/antigravity-cli/brain/c2c4a7e1-4dc0-4ac3-91c8-3753394902f3/scratch/test_linter.py` to check the linter rules on various legacy scenarios.
* **Launch Server CLI:** Run `uv run fortran-mcp` or `uv run python3 src/fortran_mcp/server.py` to start the server in stdio mode.
* **Check Config:** View or modify [mcp_config.json](file:///Volumes/home/chest/.gemini/antigravity-cli/mcp_config.json).

---

## 🎯 Next Tasks to Undertake
* **Interactive Testing:** Run an agent session in this workspace and ask it to initialize and build a project. Verify that the agent uses your new tools (`lint_code`, `compile_project`) to write correct code.
* **FPM Integration:** Test initializing a project when `fpm` is installed in the system to verify that the `fpm new` path works correctly alongside the custom Makefile fallback.
* **Additional Linter Rules:** If required, expand the `linter.py` rules to check for other obsolescent Fortran structures, like shared variable shadowing or obsolete I/O statements.
