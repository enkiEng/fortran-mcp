# Fortran Companion MCP Server

A Model Context Protocol (MCP) server designed to enable AI models to write, format, compile, lint, and structure modern Fortran code (F2003/F2018/F2023) using best practices and industry design patterns.

## 🌟 Why This Project?

AI models are trained on large volumes of legacy Fortran code (e.g., Fortran 66, 77, 90). When generating Fortran today, they regularly produce **"AI Slop"**:
* **Implicit variable typing** (omitting `implicit none`).
* **Non-standard vendor-specific types** (like `real*8` or `integer*4` instead of standard `kind` parameters).
* **Obsolescent control structures** (numbered loops like `do 10 i = 1, N` and `goto` statements).
* **Global state blocks** (`common` and `equivalence`) which violate modern scoping rules.
* **Lack of explicit interfaces** (omitting module containers and dummy argument `intent` attributes).

This MCP server equips AI agents (in Cursor, Claude Desktop, or Antigravity CLI) with tools to **statically check, auto-format, compile, and structure** Fortran code. This creates a self-correcting feedback loop where the AI compiles and lints its own work, ensuring only high-quality, modern Fortran is delivered.

---

## 🔁 How It Works

**You don't call these tools yourself — your AI assistant does, automatically.** This is a *server your AI talks to* — not a CLI you run, not a library you import.

1. **Install it once** into your MCP-capable AI host (Claude Desktop, Cursor, or Antigravity CLI — see **Setup & Connection** below).
2. **Work with your AI as you normally would** — ask it to write a new module, modernize a legacy routine, or review a file.
3. **Behind the scenes, the AI uses these tools to check its own work** — it lints, compiles, and formats what it just wrote, reads the diagnostics, and fixes its own mistakes *before* showing you the result.

The net effect: you get modern, standards-compliant Fortran instead of "AI Slop," without hand-correcting the model's output.

## 👥 Who It's For

* **Engineers pairing with an AI on Fortran** who want generated code to follow F2003/F2018 standards out of the box.
* **Teams modernizing legacy F77/F90 code** — convert fixed-format layouts, `common` blocks, and obsolete types into modular, intent-checked modern Fortran, with regression checks to prove behavior didn't change.
* **Anyone auditing or onboarding onto a large codebase** — get project-wide modernization metrics, a module dependency graph, and oversized "god-file" hot spots to see what needs attention first.

---

## 🛠️ What It Does (Tool Catalog)

The server exposes **26 MCP tools** the AI can call, grouped by purpose:

**Author & verify**
* `explain_best_practices` — the modern-Fortran style guide the agent is told to follow.
* `lint_code` / `lint_file` — static analysis for obsolete types, missing `intent`, missing `implicit none`, fixed-format layout, and deprecated statements.
* `format_code` / `format_file` — clean indentation and formatting via `fprettify`.
* `compile_project` — strict `gfortran`/`fpm` compilation (`-Wall -Wextra -Wimplicit-interface -fcheck=all -std=f2018`).
* `run_tests` — runs the project's `fpm`/`make` test suite.
* `validate_syntax` / `validate_syntax_file` — fast, build-free syntax check via the fparser2 AST; preprocess-aware for source laced with C-preprocessor macros.
* `initialize_project` — scaffolds a modern modular project (fpm or Makefile layout) with intents and test templates.

**Modernize & refactor**
* `modernize_file` — converts F77 idioms (`.eq.` → `==`, `double precision` → parameterized kinds, injects `iso_fortran_env`) and reformats.
* `verify_regression` — runs legacy vs. modernized binaries and compares output + exit status to prove no behavior change.
* `convert_common_to_module` — turns global `common` blocks into module-scoped state.
* `rename_legacy_identifiers` — safe, scoped identifier renaming.
* `analyze_pure_candidates` — finds procedures that could become `pure`.
* `audit_implicit_interfaces` — flags call sites that lack explicit interfaces.
* `suggest_refactoring` / `suggest_refactoring_file` — recommends idiomatic restructurings.
* `suggest_design_pattern` — serves architectural blueprints and code templates: **OOP** (classes, inheritance, polymorphism, deferred bindings), **Generics** (interface overloading), **RAII** (`allocatable` cleanup), **Callbacks** (Strategy via abstract interfaces / procedure pointers), and **C-Interop** (`iso_c_binding`).

**Understand a codebase**
* `project_metrics` — per-file and aggregate modernization scores and legacy-feature counts.
* `dependency_graph` — module `use` graph with fan-in/fan-out, keystone modules, and mutable-global-state detection.
* `find_large_units` — oversized procedures/modules ranked by length, nesting, and `select case` arity.

**Scaffold & interoperate**
* `scaffold_unit_test` / `scaffold_hpc_grid` — unit-test and HPC grid boilerplate.
* `generate_c_bindings` / `generate_python_interface` — `iso_c_binding` C bindings and Python (ctypes/numpy) interfaces.

---

## 📂 Project Structure

```
fortran-mcp/
├── pyproject.toml              # Python project configuration & dependencies
├── README.md                   # Project overview & documentation
├── session_handoff.md          # Context handoff for AI agents
├── docs/
│   └── FEATURE_IDEAS.md        # Prioritized backlog from large-codebase field use
├── src/
│   └── fortran_mcp/
│       ├── __init__.py
│       ├── linter.py           # Custom Fortran linter engine
│       ├── design_patterns.md  # Design-pattern blueprints served by the server
│       └── server.py           # FastMCP tool definitions and entrypoint
├── test/                       # Demonstration and verification test suite
│   ├── unformatted_legacy.f90  # Non-compliant Fortran demonstration file
│   ├── modern_compliant.f90    # Formatted, best-practice compliant Fortran file
│   ├── run_benchmarks.py       # Regression & benchmark harness (run in CI)
│   ├── illustrate_mcp_tools.py # Python script orchestrating the MCP tool calls
│   └── README.md               # Test runner documentation
└── dist/                       # Packaged python distributions (tar/wheel)
```

---

## ⚙️ Setup & Connection

This server uses the standard Python MCP SDK (`fastmcp`) and requires Python 3.14+ (or 3.10+ compatible environments) with `uv` or `pip`.

### 1. Add to Antigravity CLI
Add the server configuration to your local Antigravity config file at `~/.gemini/antigravity-cli/mcp_config.json`:
```json
{
  "mcpServers": {
    "fortran-companion": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/fortran-mcp",
        "run",
        "fortran-mcp"
      ]
    }
  }
}
```

### 2. Add to Claude Desktop
To use this with Claude Desktop, insert the block below into your `claude_desktop_config.json` (typically under `~/Library/Application Support/Claude/` on macOS or `%APPDATA%/Claude/` on Windows):
```json
{
  "mcpServers": {
    "fortran-companion": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/fortran-mcp",
        "run",
        "fortran-mcp"
      ]
    }
  }
}
```

---

## 🚀 How to Test

Start a new conversation session with any MCP-capable host (like Claude or Antigravity) in this workspace. Try prompts like:
> *"Design a modules-based modern Fortran project that integrates a user-defined function using midpoint integration. Make sure you use modern intents, explicit kinds, and test it."*

The agent will use the MCP tools to bootstrap the structure, write, lint, format, and compile the code successfully, correcting its errors on the fly.
