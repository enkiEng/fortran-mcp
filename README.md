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

## 🛠️ Features

* **Legacy Linter:** Scans code for obsolete type notations, missing intents, missing `implicit none` units, fixed-format layouts, and deprecated statements.
* **Auto-Formatter:** Connects directly to `fprettify` to cleanly indent and format Fortran code.
* **Strict Compiler Verification:** Triggers compilation checks using `gfortran` or `fpm` with strict diagnostic flags (`-Wall -Wextra -Wimplicit-interface -fcheck=all -std=f2018`).
* **Boilerplate Initializer:** Sets up standard modular layouts (supporting both `fpm` or standard Makefiles) with modern syntax, intents, and testing templates.
* **Design Patterns Database:** Serves architectural blueprints and code templates for:
  * **OOP:** Classes, inheritance, polymorphism, and deferred bindings.
  * **Generics:** Function/operator overloading using generic interfaces.
  * **RAII:** Automated resource cleanups using `allocatable`.
  * **Callbacks:** Strategy pattern using abstract interfaces and procedure pointers.
  * **C-Interop:** Interfacing standard C and Python bindings using `iso_c_binding`.

---

## 📂 Project Structure

```
fortran-mcp/
├── pyproject.toml              # Python project configuration & dependencies
├── README.md                   # Project overview & documentation
├── session_handoff.md          # Context handoff for AI agents
├── src/
│   └── fortran_mcp/
│       ├── __init__.py
│       ├── linter.py           # Custom Fortran Linter engine
│       └── server.py           # FastMCP tools definitions and entrypoint
└── dist/                       # Packaged python distributions (tar/wheel)
```

---

## ⚙️ Setup & Connection

This server uses the standard Python MCP SDK (`fastmcp`) and requires Python 3.14+ (or 3.10+ compatible environments) with `uv` or `pip`.

### 1. Add to Antigravity CLI
The server is already registered in your local Antigravity config file at `/Volumes/home/chest/.gemini/antigravity-cli/mcp_config.json`:
```json
{
  "mcpServers": {
    "fortran-companion": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "--directory",
        "/Volumes/home/chest/fortran-mcp",
        "run",
        "fortran-mcp"
      ]
    }
  }
}
```

### 2. Add to Claude Desktop
To use this with Claude Desktop, insert the block below into your `claude_desktop_config.json` (typically under `~/Library/Application Support/Claude/` on macOS):
```json
{
  "mcpServers": {
    "fortran-companion": {
      "command": "uv",
      "args": [
        "--directory",
        "/Volumes/home/chest/fortran-mcp",
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
