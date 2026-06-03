# Session Handoff: Fortran Companion MCP Server

Hello! If you are an AI assistant starting a new session in this workspace, this handoff document contains everything you need to know about the current status of the project, its files, and what we have set up.

---

## 🎯 Context & Goal
Modern Fortran (F2003+) is a highly type-safe, modular, and performant language, but AI coding models consistently generate legacy "AI Slop" (fixed-format, implicit variable types, missing intent attributes, obsolete `real*8` syntax, and legacy common blocks). 

To remediate this, we have developed a local **Model Context Protocol (MCP) Server** named **Fortran Companion** that gives AI models access to compiling, formatting, static linting, design patterns, and automated refactoring. When client agents use this MCP server, they can self-correct their code in a loop before presenting it to the user.

---

## 🛠️ Current Project State & Components

1. **Custom Linter ([linter.py](file:///Volumes/home/chest/fortran-mcp/src/fortran_mcp/linter.py)):**
   * Statically parses Fortran lines to detect legacy syntax warnings.
   * **Scope Popping Bug Fix (June 2026):** Fixed a critical scope parser bug where standard construct terminators (such as `end interface`, `end type`, `end select`, and `end do`) were falsely matched as scoping unit end boundaries, terminating subroutine scopes prematurely. It now strictly pops scopes only on standard unit terminators.
   * **F77 Comment-Stripping Fix (June 2026):** Added auto-detection for legacy fixed-format code. If the file contains F77 comment patterns (`c`, `C`, or `*` at column 1), it ignores them completely during scoping and procedure extraction, resolving linter false-positives on large legacy codebases.
   * **Dummy Procedure Filter (June 2026):** Excludes dummy procedures (declared via `procedure(...)`) and `external` declarations from `missing_intent` checks, as intents are illegal on procedures.

2. **MCP Server Entrypoint ([server.py](file:///Volumes/home/chest/fortran-mcp/src/fortran_mcp/server.py)):**
   * Exposes MCP tools to lint, compile, and format code.
   * **New Modernization Tool (`modernize_file` - June 2026):** Performs AST/regex-based replacements on F77 files (converts `.eq.`, `.le.`, etc. to standard relational symbols, swaps `double precision` to parameterized kind constants `real(dp)`, injects `iso_fortran_env` imports, and runs `fprettify` to cleanly format).
   * **New Regression Tool (`verify_regression` - June 2026):** Standardizes verification by executing both a legacy binary and modernized binary, comparing output streams and exit status to guarantee no computational regressions occurred.

3. **Design Patterns Documentation ([design_patterns.md](file:///Volumes/home/chest/fortran-mcp/design_patterns.md)):**
   * A comprehensive architectural reference guide outlining how to implement Creational (Factory, Singleton), Structural (Adapter, Composite), and Behavioral (Strategy, Observer, Command) design patterns idiomatically in modern Fortran.
   * Contains a detailed guide on solving the **Object Sorting Problem** in Fortran using both Generic Polymorphic interfaces (`comparable_t`) and procedural Callback pointers, along with indirect index sorting to avoid deep copy bottlenecks.

4. **Demonstration & Verification Test Suite ([test/](file:///Volumes/home/chest/fortran-mcp/test/)):**
   * [lmdif.f](file:///Volumes/home/chest/fortran-mcp/test/lmdif.f): Baseline legacy F77 Levenberg-Marquardt solver from Netlib MINPACK containing 29 lint violations.
   * [modern_lmdif.f90](file:///Volumes/home/chest/fortran-mcp/test/modern_lmdif.f90): Fully modernized F2018 free-form module version of the solver (0 lint violations, compiles cleanly with `-std=f2018` flags).
   * [run_benchmarks.py](file:///Volumes/home/chest/fortran-mcp/test/run_benchmarks.py): Core regression testing script that asserts linter warnings on legacy files, validates compliant files, and verifies standard-compliant compilation.

---

## 🚀 Key Entrypoints for Next Session

*   **Run Regression Checks & Benchmarks:** Run the benchmark script to check formatting, linting, and compiler verification:
    ```bash
    uv run python3 test/run_benchmarks.py
    ```
*   **Launch Server CLI:** Run `uv run fortran-mcp` or `uv run python3 src/fortran_mcp/server.py` to start the server in stdio mode.

---

## 🎯 Next Tasks to Undertake

*   **Integrate Benchmarks into CI/CD:** Add `uv run python3 test/run_benchmarks.py` as a step in any local build loops or GitHub Actions configurations to assert linter rules and compiler standard diagnostics.
*   **Expand Linter Rules:** Update `linter.py` to actively catch newly documented legacy rules (e.g. flagging standalone Cray pointers, DEC union structures, or checking if parameters are initialized via obsolescent `DATA` statements rather than inline declarations).
*   **Fprettify Settings Integration:** Allow custom configuration settings for the `fprettify` formatter (such as line length or indentation size) to be passed through the `format_code` and `format_file` tools.

