# Feature Ideas

Insights gathered from exercising fortran-mcp against a large, real-world modern-Fortran
codebase (~490k LOC across ~390 free-form modules) during an architecture review and a
test-harness build-out. Listed roughly in priority order. Each item notes the gap that was
hit and a sketch of the proposed tool/enhancement.

## Validated in real use
- **`audit_implicit_interfaces`** surfaced hundreds of implicit-interface call sites across a
  multi-file subsystem — useful as-is and worth highlighting in the README.
- **`suggest_design_pattern` → Strategy** is the single most applicable pattern on large legacy
  bases: oversized dispatchers built from one big `SELECT CASE` map cleanly to a per-variant
  Strategy / dispatch-table. Keep and expand the Strategy material.
- Fixed in 0.1.1 from this same exercise: package-relative `design_patterns.md` resolution,
  the `suggest_refactoring` false "looks modern" all-clear, and wheel packaging of the data file.

## High-value new tools / enhancements

> **Items 1–3 below were implemented in `afff5ba`** as the `project_metrics`,
> `dependency_graph`, and `find_large_units` MCP tools. They are kept here for context
> (the gap each one closed); see the tools themselves for current behavior.

### 1. Project-wide metrics & "legacy heatmap"  (biggest gap) — ✅ Implemented (`afff5ba`, `project_metrics`)
All current analysis is per-file (`lint_file`) or per-directory (`audit_implicit_interfaces`).
Reviewing a ~390-file codebase required hand-rolling a sweep to compute per-file metrics and
aggregates. Promote that into a first-class tool.

**Proposed:** `project_metrics(project_path) -> {per_file: [...], summary: {...}}` emitting, per file:
LOC / code / comment, `implicit none` present, counts of COMMON / equivalence / goto /
numbered-do / non-standard types / derived types / `pure` / `elemental` / allocatable / pointer,
missing-`intent` count, a composite *modernization score*, plus ranked worst-offenders and
"god-files". Output JSON/CSV so agents can aggregate without re-parsing source.

### 2. Module dependency / use-graph + global-state detection — ✅ Implemented (`afff5ba`, `dependency_graph`)
There is no way to see the module `use` graph. Finding the architectural keystones required
building the graph by hand — and the highest-value finding (a few mutable global-state modules
depended on by ~60% of files) fell straight out of fan-in analysis.

**Proposed:** `dependency_graph(project_path)` returning module `use` edges, fan-in/fan-out per
module, ranked keystone modules, and a flag for modules that expose **mutable public state**
(the dominant coupling/testability/parallelism smell). Optionally emit DOT/Mermaid.

### 3. Complexity / "god-unit" detection — ✅ Implemented (`afff5ba`, `find_large_units`)
Oversized procedures and modules dominate the maintainability problem (e.g., a single 2000-line
subroutine built around a ~80-way `SELECT CASE`). These had to be found by manual profiling.

**Proposed:** `find_large_units(project_path)` reporting oversized procedures/modules by line
count, `SELECT CASE` arity, and nesting depth — i.e., the decomposition targets.

### 4. Higher-signal `suggest_refactoring` patterns
The current matcher keys on COMMON/GOTO/select-case/external/long-params/C-interop. On already
format-modern code the real levers are different. Add detectors for:
- **module-level mutable public state** (global state) → encapsulate / `protected`;
- **pointer-to-global aliasing** (module pointers re-pointed into global arrays each call) →
  pass explicit arguments (unblocks `pure`/parallelism);
- **repeated `SELECT CASE` on the same selector across procedures** (a {feature}×{variant}
  dispatch matrix) → Strategy / dispatch table;
- **string-keyed field accessors** (`SELECT CASE(name)` returning a pointer to a field;
  reflection-by-string) → typed or enum-indexed access.

### 5. Characterization-test scaffolding (refactor-safety)
The reusable pattern for safe refactoring is: *init → call a routine → pin its current output*
(a golden value + tolerance). `scaffold_unit_test` currently emits a bare program; add a
**characterization** mode.

**Proposed:** `scaffold_characterization_test(file, procedure, inputs, framework)` that generates
a test capturing the routine's current output and asserting it within tolerance, targeting an
established framework (FRUIT or Julienne) rather than a bare `program`. Pairs naturally with the
existing `verify_regression` (same idea at the binary level).

### 6. Pure-candidate blocker reporting
`analyze_pure_candidates` answers "is it pure?"; the more actionable question during a
purification effort is *why not*. Enhance it to name the specific blocker per procedure: I/O,
write to global/module state, aliasing through module pointers, or a missing `intent`. (Converting
side-effecting routines to `pure`/`do concurrent` is a common, high-value modernization goal.)

## Whole-program graph analyses

Derived from evaluating a mature, field-used whole-program Fortran analysis tool against the
same class of large codebase. That tool is a regex-based *relationship/call-graph analyzer*
(not a parser) hardwired to one project's layout — but its battery of reports is a validated
catalog of the analyses that matter at scale. Several map onto tools we already have
(`dependency_graph` ≈ its module-use graph, `audit_implicit_interfaces` ≈ its missing-implicit-none
report, `find_large_units`, `project_metrics`); the items below are the gaps it exposes that we do
**not** yet cover. All of these are best built on the fparser2 AST (now a dependency) rather than
regex — that gives the same analyses with grammar-accurate scope/call resolution, and generically
(not tied to any one project's directory conventions).

### 7. Call graph + call-path queries (biggest gap)
We build the module **`use`** graph (`dependency_graph`) but not a **call** graph. Add per-procedure
caller/callee edges and the ability to answer "what calls X", "what does X call", and "show the
call path(s) from A to B". This is the single most-used capability of the reference tool and the
keystone for impact analysis, refactor blast-radius, and understanding an unfamiliar codebase.

**Proposed:** `call_graph(project_path)` returning caller/callee edges per procedure (with fan-in/
fan-out and recursion flags), and `call_paths(project_path, source, target)` returning the
path(s) between two procedures. Optionally emit DOT/Mermaid. Flag scope-ambiguous edges
separately rather than guessing.

### 8. Dead-code & dangling-reference detection
- **Orphans** — procedures that are defined but never called (dead-code / removal candidates).
- **missing routines** — call sites whose target procedure is never defined anywhere in scope.
- **missing modules** — `use` of a module that is never defined in the project.
The latter two are genuine correctness signals (typos, broken refactors, build-order assumptions),
not just hygiene. Falls straight out of the call/use graph once #7 exists.

**Proposed:** `find_orphans(project_path)` and `find_dangling_references(project_path)`.

### 9. USE hygiene & recursion sanity
- **Duplicate `use`** of the same module within one scope, and **transitive/inherited `use` bloat**
  (a module pulled in only because a parent or a called module exposed it) → tighten `only:` clauses.
- **Recursion sanity**: flag procedures that call themselves but are not declared `recursive`, and
  those declared `recursive` that never actually recurse.
- **Keyword-name collisions**: entities named after Fortran keywords/intrinsics.
- **Accessibility problems**: names in a `public`/`private` statement that are never defined.

**Proposed:** fold into an expanded `audit_*` family (e.g. `audit_use_statements`,
`audit_recursion`) or surface as additional `project_metrics` findings.

## Smaller / nice-to-have
- `modernize_file` is rough on cpp-laced fixed-format source; preserve/handle `#`-preprocessor and
  fixed-format comment lines instead of mangling them.
- `scaffold_unit_test` could optionally emit FRUIT/Julienne idioms, not just a standalone program.
- A note in the README that several tools accept whole directories vs. single files (and which).
