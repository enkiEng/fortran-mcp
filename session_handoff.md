# Session Handoff: Fortran Companion MCP Server

Hello! If you are an AI assistant starting a new session in this workspace, this handoff
documents the current status of the project. Last reconciled against the code on
**2026-06-25** (v0.2.0, `main` clean and up to date with `origin/main`; no open PRs; the only
remote branch is `origin/main`).

> **Last session (2026-06-25):** reconciled this handoff with the code; evaluated **fparser2**
> as an AST backend (ran a coverage spike — 100% parse on one large modern codebase, ~100% on a
> second after preprocessing) and **adopted it**; shipped the `validate_syntax` /
> `validate_syntax_file` tools with CI coverage; expanded the README (How It Works / Who It's For
> / 26-tool catalog); and added a prioritized backlog with build order to `docs/FEATURE_IDEAS.md`.
> **Work is deferred to a future session** — `main` is shippable; no PR opened yet. The next
> build is **#6 (pure-candidate blocker reporting)** — see Next Tasks.
>
> **⚠️ Pushing:** this repo's `origin` is `enkiEng/fortran-mcp`; the machine's default `gh`
> account is `NRCgg`, which **lacks write access** (push fails with 403). Before pushing:
> `gh auth switch --hostname github.com --user enkiEng` → push → switch back to `NRCgg`.
>
> **⚠️ Names:** do **not** mention the real evaluation codebases or the internal analysis tool by
> name in any tracked repo file — refer to them generically ("a large modern codebase", "a
> field-used analysis tool"). These local session notes are the only place names may appear, and
> even here they're kept generic.

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
- **Dependencies:** `fastmcp`, `fprettify`, `numpy`, and **`fparser`** (added for the AST-backed
  `validate_syntax` tools — pure-Python, BSD-3, validated on Python 3.14).
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

2. **MCP Server Entrypoint ([server.py](src/fortran_mcp/server.py), ~3200 lines):**
   Exposes **26 MCP tools**. Grouped:
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
   * **AST syntax validation (fparser2):** `validate_syntax`, `validate_syntax_file` — a
     build-free syntax gate backed by the fparser2 AST (distinct from `compile_project`: no
     build system, no other modules needed). `validate_syntax_file` is **preprocess-aware**:
     it auto-detects C-preprocessor directives and runs `gfortran -cpp -E -P` before parsing,
     so cpp-macro-laced source (e.g. function-like macros that are not valid Fortran until
     expanded) validates correctly.
     Standard names are mapped onto fparser2's grammar ceiling (f2003 / partial-f2008);
     `f2018`/`f2023` map to `f2008`.
   * `modernize_file` converts `.eq.`/`.le.` etc. to relational symbols, swaps `double
     precision` to parameterized kind constants, injects `iso_fortran_env`, and runs
     `fprettify`. `verify_regression` runs a legacy and a modernized binary and compares output
     streams + exit status to guarantee no computational regression.

3. **Design Patterns Documentation ([design_patterns.md](src/fortran_mcp/design_patterns.md)):**
   Architectural reference for Creational (Factory, Singleton), Structural (Adapter, Composite),
   and Behavioral (Strategy, Observer, Command) patterns in modern Fortran, plus the
   **Object Sorting Problem** (generic polymorphic `comparable_t` interfaces, procedural
   callback pointers, and indirect index sorting). Resolved package-relative at runtime.

4. **Test Suite ([test/](test/)):** `run_benchmarks.py` is the regression harness with five
   sections — (1) linter benchmarks, (2) strict F2018 compiler verification, (3) interop binding
   generation, (4) the metrics/dependency/large-unit tools, (5) AST syntax validation
   (`validate_syntax`: clean-pass, legacy-F77-pass, broken-flagged, cpp-macro-hint). Fixtures:
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
The live, prioritized backlog is **[docs/FEATURE_IDEAS.md](docs/FEATURE_IDEAS.md)** — it now
carries a **Prioritization & build order** section (the methodology + tiered sequence). The
`#1–#9` numbers there are stable identifiers, *not* a ranking; tiers are the ranking.

**✅ Done (recent):** CI benchmark integration; FEATURE_IDEAS items 1–3 (`project_metrics`,
`dependency_graph`, `find_large_units`); **fparser2 AST backend evaluated + adopted** —
`validate_syntax`/`validate_syntax_file` shipped with CI coverage. Coverage spike across two
large modern codebases: 100% parse on the first (~395 files / ~489k LOC), ~100% on the second
after preprocessing (its only raw failures were unexpanded cpp macros, not grammar-ceiling
issues). fparser2 is the recommended **analysis** backend — *not* a format-preserving rewriter,
so keep `modernize_file` on regex/fprettify.

**▶️ Build order (from FEATURE_IDEAS — start at the top):**
1. **Tier 1 · #6 Pure-candidate blocker reporting** *(next build)* — make `analyze_pure_candidates`
   report *why* a procedure isn't pure (I/O, global/module-state writes, pointer aliasing, missing
   `intent`). Per-procedure, **built on the fparser2 AST** (blockers map to node types); chosen as
   next because it's tractable, high-confidence, and proves the AST-analysis pattern before the
   hard cross-module work.
2. **Tier 1 · `modernize_file` cpp handling** — now cheap: reuse the `_preprocess_source` helper
   already built for `validate_syntax` (in `server.py`) instead of mangling cpp/fixed-format source.
3. **Tier 2 · #5 Characterization-test scaffolding** — `scaffold_characterization_test` mode that
   pins current output within tolerance (FRUIT/Julienne); pairs with `verify_regression`.
4. **Tier 2 · #4 Higher-signal `suggest_refactoring` detectors** — scope to the *new* levers
   (pointer-to-global aliasing, string-keyed accessors); mutable-public-state and `SELECT CASE`
   arity are already partly covered by `dependency_graph` / `find_large_units`.
5. **Tier 3 · #7 Call graph + call-path queries** — biggest *capability* gap (we only build the
   module-`use` graph today), but highest effort/risk: needs cross-module symbol binding fparser2
   does **not** provide. Defer until #6 validates the approach.
6. **Tier 3 · #8 Dead-code & dangling references** — gated on #7.
7. **Tier 4 · #9 USE hygiene & recursion sanity**, plus smaller items: expand linter rules (Cray
   pointers, DEC unions, obsolescent `DATA` init); fprettify config passthrough (line length /
   indent); README note on which tools accept directories vs. single files.

**Cross-cutting (opportunistic):** migrate existing regex analysis tools (`dependency_graph`,
`find_large_units`) onto fparser2 for accuracy as they're touched, keeping a regex fallback for
files that fail to parse.
