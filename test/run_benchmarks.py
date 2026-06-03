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
