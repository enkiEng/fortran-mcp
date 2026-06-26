#!/usr/bin/env python3
"""
Test Suite & Benchmarking Harness for Fortran Companion MCP Server.
Runs static lint regression tests and compiler warnings verification.
"""
import sys
import os
import shutil
import subprocess

# Ensure we can import the module directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fortran_mcp.linter import FortranLinter

def run_compile(filepath, strict_flags, output_obj):
    if not shutil.which("gfortran"):
        return None, "gfortran not found"
    
    cmd = ["gfortran"] + strict_flags + ["-c", filepath, "-o", output_obj]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr

def main():
    print("=" * 60)
    print("      FORTRAN MCP REGRESSION & BENCHMARKING HARNESS")
    print("=" * 60)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Test cases mapping (filename -> expected_lint_status)
    # expected_lint_status is a dictionary specifying expected warning rules
    test_cases = [
        {
            "name": "unformatted_legacy.f90",
            "path": os.path.join(current_dir, "unformatted_legacy.f90"),
            "expect_warnings": True,
            "min_warnings": 10
        },
        {
            "name": "modern_compliant.f90",
            "path": os.path.join(current_dir, "modern_compliant.f90"),
            "expect_warnings": False,
            "min_warnings": 0
        },
        {
            "name": "lmdif.f",
            "path": os.path.join(current_dir, "lmdif.f"),
            "expect_warnings": True,
            "min_warnings": 25
        },
        {
            "name": "modern_lmdif.f90",
            "path": os.path.join(current_dir, "modern_lmdif.f90"),
            "expect_warnings": False,
            "min_warnings": 0
        }
    ]

    failed = False

    # 1. RUN LINT BENCHMARKS
    print("\n--- [1] Running Static Analysis Linter Benchmarks ---")
    for case in test_cases:
        if not os.path.exists(case["path"]):
            print(f"❌ Error: Test file not found: {case['path']}")
            failed = True
            continue

        with open(case["path"], "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        linter = FortranLinter(code)
        warnings = linter.lint()
        warn_count = len(warnings)

        print(f"File: {case['name']} (Fixed format: {linter.is_fixed_format})")
        print(f"  -> Found {warn_count} issue(s).")
        
        if case["expect_warnings"]:
            if warn_count < case["min_warnings"]:
                print(f"  ❌ FAILURE: Expected at least {case['min_warnings']} warnings, got {warn_count}.")
                failed = True
            else:
                print(f"  ✅ SUCCESS: Legacy warnings correctly caught.")
        else:
            if warn_count > 0:
                print(f"  ❌ FAILURE: Expected 0 warnings, got {warn_count}.")
                for w in warnings:
                    print(f"    Line {w['line']}: [{w['rule']}] {w['message']}")
                failed = True
            else:
                print(f"  ✅ SUCCESS: Code is 100% compliant with modern best practices.")

    # 2. RUN STRICT COMPILATION BENCHMARKS
    print("\n--- [2] Running Strict Compiler Verification Benchmarks ---")
    strict_flags = ["-Wall", "-Wextra", "-Wimplicit-interface", "-fcheck=all", "-std=f2018"]
    
    compile_cases = [
        "modern_compliant.f90",
        "modern_lmdif.f90"
    ]

    for filename in compile_cases:
        filepath = os.path.join(current_dir, filename)
        output_obj = os.path.join(current_dir, filename.replace(".f90", ".o"))
        
        # Clean old objects
        if os.path.exists(output_obj):
            os.remove(output_obj)
            
        # Clean mod files if generated
        mod_file = os.path.join(current_dir, "calculator_mod.mod")
        if os.path.exists(mod_file):
            os.remove(mod_file)
        mod_lmdif_file = os.path.abspath(os.path.join(current_dir, "..", "minpack_lmdif_mod.mod"))
        if os.path.exists(mod_lmdif_file):
            os.remove(mod_lmdif_file)
        mod_lmdif_file_local = os.path.join(current_dir, "minpack_lmdif_mod.mod")
        if os.path.exists(mod_lmdif_file_local):
            os.remove(mod_lmdif_file_local)

        code, message = run_compile(filepath, strict_flags, output_obj)
        
        if code is None:
            print(f"File: {filename} -> ⚠️ Skipped ({message})")
            continue
            
        if code == 0:
            print(f"File: {filename} -> ✅ SUCCESS: Compiled cleanly with standard F2018 flags.")
        else:
            print(f"File: {filename} -> ❌ FAILURE: Compilation failed with exit code {code}.")
            print(f"Compiler details:\n{message}")
            failed = True

        # Cleanup artifacts
        if os.path.exists(output_obj):
            os.remove(output_obj)
        if os.path.exists(mod_file):
            os.remove(mod_file)
        if os.path.exists(mod_lmdif_file):
            os.remove(mod_lmdif_file)
        if os.path.exists(mod_lmdif_file_local):
            os.remove(mod_lmdif_file_local)

    # 3. RUN INTEROPERABILITY BINDING GENERATION TESTS
    print("\n--- [3] Running Interoperability Binding Generation Tests ---")
    interop_script = os.path.join(current_dir, "test_interop_run.py")
    if os.path.exists(interop_script):
        res = subprocess.run([sys.executable, interop_script])
        if res.returncode != 0:
            print("  ❌ FAILURE: Interoperability binding tests failed.")
            failed = True
        else:
            print("  ✅ SUCCESS: Interoperability binding tests passed.")
    else:
        print("  ⚠️ Skipped: test_interop_run.py not found.")

    # 4. RUN NEW ENHANCEMENTS TESTS
    print("\n--- [4] Running New MCP Tools (Metrics, Dependencies, Large Units) ---")
    try:
        from fortran_mcp.server import project_metrics, dependency_graph, find_large_units
        import json
        
        project_path = os.path.abspath(os.path.join(current_dir, ".."))
        
        # Test project_metrics
        print("Running project_metrics...")
        metrics_raw = project_metrics(project_path)
        metrics_data = json.loads(metrics_raw)
        print(f"  Files analyzed: {metrics_data['summary']['files_analyzed']}")
        print(f"  Average modernization score: {metrics_data['summary']['average_modernization_score']}")
        if metrics_data['summary']['files_analyzed'] > 0:
            print("  ✅ project_metrics passed.")
        else:
            print("  ❌ project_metrics failed: no files analyzed.")
            failed = True
            
        # Test dependency_graph
        print("Running dependency_graph...")
        dep_raw = dependency_graph(project_path)
        dep_data = json.loads(dep_raw)
        print(f"  Modules found: {len(dep_data['modules'])}")
        print(f"  Keystone modules count: {len(dep_data['keystones'])}")
        if len(dep_data['modules']) > 0:
            print("  ✅ dependency_graph passed.")
        else:
            print("  ❌ dependency_graph failed: no modules found.")
            failed = True
            
        # Test find_large_units
        print("Running find_large_units...")
        units_raw = find_large_units(project_path)
        units_data = json.loads(units_raw)
        print(f"  Large/Total units found: {len(units_data)}")
        if len(units_data) > 0:
            print("  ✅ find_large_units passed.")
        else:
            print("  ❌ find_large_units failed: no units found.")
            failed = True
            
    except Exception as e:
        print(f"  ❌ FAILURE testing new MCP tools: {str(e)}")
        failed = True

    # ------------------------------------------------------------------
    # [5] AST-backed syntax validation (fparser2)
    # ------------------------------------------------------------------
    print("\n--- [5] Running AST Syntax Validation (validate_syntax) ---")
    try:
        from fortran_mcp.server import validate_syntax, validate_syntax_file

        # A clean modern file must validate.
        clean = validate_syntax_file(os.path.join(current_dir, "modern_lmdif.f90"))
        if clean.startswith("✅"):
            print("  ✅ Clean F2018 file validated.")
        else:
            print(f"  ❌ Clean file unexpectedly failed: {clean}")
            failed = True

        # A legacy fixed-format F77 file must validate under the older grammar.
        legacy = validate_syntax_file(os.path.join(current_dir, "lmdif.f"), fortran_version="f2003")
        if legacy.startswith("✅"):
            print("  ✅ Legacy F77 fixed-format file validated.")
        else:
            print(f"  ❌ Legacy F77 file unexpectedly failed: {legacy}")
            failed = True

        # Broken source must be reported as a syntax error with a line number.
        broken = validate_syntax("module m\n  implicit none\n  integer :: i =\nend module m\n")
        if broken.startswith("❌") and "line" in broken:
            print("  ✅ Broken source correctly flagged with a line number.")
        else:
            print(f"  ❌ Broken source not flagged as expected: {broken}")
            failed = True

        # Unexpanded cpp macros must produce the preprocessing hint, not a silent pass.
        cpp = validate_syntax('#include "x.h"\nsubroutine s()\n  SG_CHECKMEM("bad")\nend subroutine s\n')
        if cpp.startswith("❌") and "preprocess" in cpp.lower():
            print("  ✅ Unexpanded cpp macro flagged with preprocessing guidance.")
        else:
            print(f"  ❌ cpp macro case not handled as expected: {cpp}")
            failed = True

    except Exception as e:
        print(f"  ❌ FAILURE testing validate_syntax: {str(e)}")
        failed = True

    print("\n" + "=" * 60)
    if failed:
        print("   ❌ BENCHMARKS FAILED: Regression checks encountered errors.")
        print("=" * 60)
        sys.exit(1)
    else:
        print("   ✅ ALL BENCHMARKS AND REGRESSION TESTS PASSED")
        print("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    main()
