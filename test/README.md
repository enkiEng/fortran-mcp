# Fortran Companion MCP Server - Test suite

This folder contains a test suite and demonstration files illustrating the use of the **Fortran Companion MCP Server** tools.

## 📂 Folder Structure

* [unformatted_legacy.f90](file:///Volumes/home/chest/fortran-mcp/test/unformatted_legacy.f90): An unformatted, legacy Fortran program designed to trigger several linting rules (obsolete types, missing `implicit none`, missing dummy argument `intent` attributes, standalone `dimension` declarations, `GOTO` statements, and fixed-format style comments).
* [modern_compliant.f90](file:///Volumes/home/chest/fortran-mcp/test/modern_compliant.f90): A fully modern, formatted, and standards-compliant Fortran program that passes all linting rules and compiles under strict `-std=f2018` flags.
* [illustrate_mcp_tools.py](file:///Volumes/home/chest/fortran-mcp/test/illustrate_mcp_tools.py): A Python script that programmatically imports and runs the core MCP companion tools on these test files.
* [README.md](file:///Volumes/home/chest/fortran-mcp/test/README.md): This documentation.

## 🚀 How to Run the Demonstration Script

You can run the demonstration script using the environment's `uv` setup:

```bash
uv run python3 test/illustrate_mcp_tools.py
```

This will run the following steps:
1. **Linting Legacy Code:** Performs static analysis on `unformatted_legacy.f90`, reporting 12 specific violations.
2. **Linting Modern Code:** Analyzes `modern_compliant.f90`, demonstrating a clean pass with 0 warnings.
3. **In-place Formatting:** Runs the `fprettify` engine in-place on a temporary copy of the legacy code, aligning indentation and structure automatically.
4. **Strict Compilation:** Compiles `modern_compliant.f90` with strict compiler flags (`-Wall -Wextra -Wimplicit-interface -fcheck=all -std=f2018`) using `gfortran`, and runs the binary to verify output.

---

## 🛠️ Simulating via MCP Server Tools

If you are communicating with this MCP server inside Claude Desktop, Cursor, or the Antigravity CLI, you can directly call the following tools:

### 1. `lint_file`
Analyze the files to see code quality reports:
* Run `lint_file` on `test/unformatted_legacy.f90` to view the 12 issues.
* Run `lint_file` on `test/modern_compliant.f90` to verify a clean result.

### 2. `format_file`
Automatically format the layout in-place:
* Run `format_file` on `test/unformatted_legacy.f90` to apply standard indentation (indent: 3 spaces).

### 3. `compile_project`
Compile using the root Makefile/fpm config:
* Run `compile_project` with standard flag `f2018` on the project root to compile verified assets.
