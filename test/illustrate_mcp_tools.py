#!/usr/bin/env python3
import sys
import os
import shutil
import subprocess

# Add src/ directory to path so we can import the module directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from fortran_mcp.server import lint_file, format_code, format_file
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

def run_cmd(args, cwd=None):
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def main():
    print("=" * 60)
    print("   ILLUSTRATING FORTRAN MCP COMPANION TOOLS IN ACTION")
    print("=" * 60)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    legacy_file = os.path.join(current_dir, "unformatted_legacy.f90")
    modern_file = os.path.join(current_dir, "modern_compliant.f90")
    
    # -------------------------------------------------------------
    # 1. ILLUSTRATE LINT_FILE ON LEGACY CODE
    # -------------------------------------------------------------
    print("\n--- [1] Linting Legacy File (unformatted_legacy.f90) ---")
    print(f"File path: {legacy_file}")
    legacy_lint_report = lint_file(legacy_file)
    print(legacy_lint_report)
    
    # -------------------------------------------------------------
    # 2. ILLUSTRATE LINT_FILE ON MODERN CODE
    # -------------------------------------------------------------
    print("\n--- [2] Linting Modern File (modern_compliant.f90) ---")
    print(f"File path: {modern_file}")
    modern_lint_report = lint_file(modern_file)
    print(modern_lint_report)
    
    # -------------------------------------------------------------
    # 3. ILLUSTRATE FORMATTING CODE
    # -------------------------------------------------------------
    print("\n--- [3] Formatting Legacy Code (fprettify integration) ---")
    # Let's format a copy of the legacy file to see the layout formatting
    temp_formatted_file = os.path.join(current_dir, "temp_formatted.f90")
    shutil.copyfile(legacy_file, temp_formatted_file)
    
    print("Before formatting (first 10 lines of temp_formatted.f90):")
    with open(temp_formatted_file, "r") as f:
        before_lines = f.readlines()[:10]
        print("".join(before_lines).strip())
        
    print("\nApplying format_file MCP tool...")
    format_res = format_file(temp_formatted_file)
    print(format_res)
    
    print("\nAfter formatting (first 10 lines of temp_formatted.f90):")
    with open(temp_formatted_file, "r") as f:
        after_lines = f.readlines()[:10]
        print("".join(after_lines).strip())
        
    if os.path.exists(temp_formatted_file):
        os.remove(temp_formatted_file)
        
    # -------------------------------------------------------------
    # 4. COMPILER VERIFICATION DEMO
    # -------------------------------------------------------------
    print("\n--- [4] Strict Compiler Verification Demo ---")
    print("Compiling modern_compliant.f90 using gfortran with strict MCP flags:")
    strict_flags = ["-Wall", "-Wextra", "-Wimplicit-interface", "-fcheck=all", "-std=f2018"]
    print(f"Flags: {' '.join(strict_flags)}")
    
    # Compile
    out_binary = os.path.join(current_dir, "modern_test")
    # Clean old build files if any
    for ext in [".o", ".mod"]:
        fpath = os.path.join(current_dir, "calculator_mod" + ext)
        if os.path.exists(fpath):
            os.remove(fpath)
    if os.path.exists(out_binary):
        os.remove(out_binary)
        
    # Make sure gfortran is available
    if not shutil.which("gfortran"):
        print("Error: 'gfortran' not found on system path. Skipping compile step.")
    else:
        code, stdout, stderr = run_cmd(["gfortran"] + strict_flags + [modern_file, "-o", out_binary], cwd=current_dir)
        if code == 0:
            print("Success! Compilation succeeded with zero warnings.")
            print("Running the compiled binary:")
            run_code, run_out, run_err = run_cmd([out_binary], cwd=current_dir)
            print(f"Exit code: {run_code}")
            print(f"STDOUT:\n{run_out.strip()}")
        else:
            print(f"Error compiling: Exit code {code}")
            print(f"STDERR:\n{stderr}")
        
    # Cleanup compiled artifacts
    for ext in [".o", ".mod"]:
        fpath = os.path.join(current_dir, "calculator_mod" + ext)
        if os.path.exists(fpath):
            os.remove(fpath)
    if os.path.exists(out_binary):
        os.remove(out_binary)
        
    print("\n" + "=" * 60)
    print("   MCP TOOLS ILLUSTRATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
