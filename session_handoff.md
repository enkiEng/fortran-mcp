# Session Handoff: Fortran Companion MCP Server

Hello! If you are an AI assistant starting a new session in this workspace, this handoff
documents the current status of the project. Last reconciled against the code on
**2026-06-25** (v0.2.0, `main` clean and up to date with `origin/main`; no open PRs; the only
remote branch is `origin/main`).

---

## 🎯 Context & Goal
Modern Fortran (F2003+) is highly type-safe, modular, and performant, but AI coding models
consistently generate legacy "AI Slop" (fixed-format, implicit variable types, missing intent
attributes, obsolete `real*8` syntax, legacy common blocks).

To remediate this, we built a local **Model Context Protocol (MCP) Server** named **Fortran
Companion** that gives AI models access to compiling, formatting, static linting, design
patterns, project-wide analysis, refactoring, interop binding generation, and test scaffolding.
Client agents use it to self-correct their code in a loop before presenting it to the user.

---

## 📦 Release / Repo State
- **Version:** 0.2.0 (`pyproject.toml`). Prior releases: 0.1.1, 0.1.0.
- **Branch:** `main`, clean, up to date with `origin/main`.
- **PRs:** #1–#7 all MERGED. No open PRs. Only remote branch is `origin/main`.
- **CI:** `.github/workflows/ci.yml` runs `test/run_benchmarks.py` on push/PR (Python 3.14 +
  gfortran). `.github/workflows/release.yml` builds wheel/sdist and publishes a GitHub Release
  on version tags (and verifies `design_patterns.md` is packaged in the wheel).

---

## 🛠️ Current Components

1. **Custom Linter ([linter.py](src/fortran_mcp/linter.py), ~597 lines):**
   Statically parses Fortran lines to detect legacy syntax warnings and emits a modernization
   score. Notable fixes in place:
   * **Scope-popping fix:** construct terminators (`end interface`, `end type`, `end select`,
     `end do`) are no longer falsely matched as scoping-unit ends; scopes pop only on true unit
     terminators.
   * **F77 comment auto-detection/stripping:** if the file has fixed-format comment patterns
     (`c`/`C`/`*` in column 1) it auto-detects fixed format and ignores those lines during
     scoping/procedure extraction, killing false positives on legacy code.
   * **Dummy-procedure filter:** excludes dummy procedures (`procedure(...)`) and `external`
     declarations from `missing_intent` checks (intents are illegal on procedures).

2. **MCP Server Entrypoint ([server.py](src/fortran_mcp/server.py), ~3000 lines):**
   Exposes **27 MCP tools**. Grouped:
   * **Core:** `explain_best_practices`, `lint_code`, `lint_file`, `format_code`,
     `format_file`, `initialize_project`, `compile_project`, `run_tests`.
   * **Design / refactoring:** `suggest_design_pattern`, `suggest_refactoring`,
     `suggest_refactoring_file`, `modernize_file`, `verify_regression`,
     `rename_legacy_identifiers`, `convert_common_to_module`, `analyze_pure_candidates`,
     `audit_implicit_interfaces`.
   * **Scaffolding:** `scaffold_unit_test`, `scaffold_hpc_grid`.
   * **Interop:** `generate_c_bindings`, `generate_python_interface`.
   * **Project-wide analysis (added in `afff5ba`):** `project_metrics`, `dependency_graph`,
     `find_large_units`.
   * `modernize_file` converts `.eq.`/`.le.` etc. to relational symbols, swaps `double
     precision` to parameterized kind constants, injects `iso_fortran_env`, and runs
     `fprettify`. `verify_regression` runs a legacy and a modernized binary and compares output
     streams + exit status to guarantee no computational regression.

3. **Design Patterns Documentation ([design_patterns.md](src/fortran_mcp/design_patterns.md)):**
   Architectural reference for Creational (Factory, Singleton), Structural (Adapter, Composite),
   and Behavioral (Strategy, Observer, Command) patterns in modern Fortran, plus the
   **Object Sorting Problem** (generic polymorphic `comparable_t` interfaces, procedural
   callback pointers, and indirect index sorting). Resolved package-relative at runtime.

4. **Test Suite ([test/](test/)):** `run_benchmarks.py` is the regression harness with four
   sections — (1) linter benchmarks, (2) strict F2018 compiler verification, (3) interop binding
   generation, (4) the new metrics/dependency/large-unit tools. Fixtures:
   * [lmdif.f](test/lmdif.f): legacy F77 Levenberg-Marquardt solver (Netlib MINPACK), ~30 lint
     violations.
   * [modern_lmdif.f90](test/modern_lmdif.f90): fully modernized F2018 version (0 violations,
     compiles clean under `-std=f2018`).
   * [unformatted_legacy.f90](test/unformatted_legacy.f90) / [modern_compliant.f90](test/modern_compliant.f90):
     additional legacy vs. compliant linter fixtures.
   * [interop_test_mod.f90](test/interop_test_mod.f90), [test_interop_run.py](test/test_interop_run.py),
     [illustrate_mcp_tools.py](test/illustrate_mcp_tools.py): interop + tool-illustration tests.

---

## 🚀 Key Entrypoints
*   **Run regression checks & benchmarks:**
    ```bash
    uv run python3 test/run_benchmarks.py
    ```
    (If `uv` isn't on PATH: `source .venv/bin/activate && python3 test/run_benchmarks.py`.)
*   **Launch server CLI:** `uv run fortran-mcp` or `uv run python3 src/fortran_mcp/server.py`
    (stdio mode).

---

## 🎯 Next Tasks
The live, prioritized backlog is now **[docs/FEATURE_IDEAS.md](docs/FEATURE_IDEAS.md)**, derived
from exercising the server against a ~490k-LOC real codebase. Status:

* ✅ **Done:** CI benchmark integration; FEATURE_IDEAS items 1–3 (`project_metrics`,
  `dependency_graph`, `find_large_units`).
* ⏳ **Open (high value):**
  * **#6 Pure-candidate blocker reporting** — make `analyze_pure_candidates` report *why* a
    procedure isn't pure (I/O, global/module-state writes, pointer aliasing, missing `intent`).
  * **#4 Higher-signal `suggest_refactoring` detectors** — module-level mutable public state,
    pointer-to-global aliasing, repeated `SELECT CASE` dispatch matrices, string-keyed field
    accessors.
  * **#5 Characterization-test scaffolding** — a `scaffold_characterization_test` mode that pins
    current output within tolerance (FRUIT/Julienne), pairing with `verify_regression`.
* ⏳ **Open (smaller):** expand linter rules (Cray pointers, DEC unions, obsolescent `DATA`
  initialization); fprettify config passthrough (line length / indent) on the format tools;
  `modernize_file` handling of cpp-laced fixed-format source; README note on which tools accept
  directories vs. single files.
