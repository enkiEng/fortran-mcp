#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import platform

# Insert src/ to path so we can import the mcp module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fortran_mcp.server import generate_python_interface

def main():
    print("=" * 60)
    print("        TESTING PHASE 4 BINDING GENERATORS")
    print("=" * 60)

    test_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(test_dir, "interop_test_mod.f90")
    module_name = "interop_test_mod"

    # Clean old generated files
    c_mod_file = os.path.join(test_dir, f"{module_name}_c_mod.f90")
    py_wrapper_file = os.path.join(test_dir, f"{module_name}.py")
    if os.path.exists(c_mod_file):
        os.remove(c_mod_file)
    if os.path.exists(py_wrapper_file):
        os.remove(py_wrapper_file)

    # 1. Run generator
    print("Running generate_python_interface...")
    result = generate_python_interface(file_path, module_name)
    print(f"Result: {result}")

    if not os.path.exists(c_mod_file) or not os.path.exists(py_wrapper_file):
        print("❌ FAIL: Generated files not found.")
        sys.exit(1)
    print("✅ Success: Generated wrapper files.")

    # 2. Compile shared library
    if not shutil.which("gfortran"):
        print("⚠️ Skipped compilation check: gfortran not found in path.")
        sys.exit(0)

    # Platform specific library name
    system = platform.system()
    if system == "Darwin":
        lib_name = f"lib{module_name}_c_mod.dylib"
    elif system == "Windows":
        lib_name = f"{module_name}_c_mod.dll"
    else:
        lib_name = f"lib{module_name}_c_mod.so"

    lib_path = os.path.join(test_dir, lib_name)
    if os.path.exists(lib_path):
        os.remove(lib_path)

    print(f"Compiling shared library to {lib_path}...")
    compile_cmd = [
        "gfortran",
        "-shared",
        "-fPIC",
        "-O2",
        file_path,
        c_mod_file,
        "-o",
        lib_path
    ]
    res = subprocess.run(compile_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ FAIL: Compilation failed.")
        print(res.stdout)
        print(res.stderr)
        sys.exit(1)
    print("✅ Success: Compiled shared library.")

    # 3. Add test directory to path and import the wrapper
    sys.path.insert(0, test_dir)
    try:
        import interop_test_mod
    except Exception as e:
        print(f"❌ FAIL: Could not import generated Python wrapper: {e}")
        sys.exit(1)

    import numpy as np

    # Test [1]: Function add_numbers
    try:
        a = 3.5
        b = 4.2
        expected = a + b
        res = interop_test_mod.add_numbers(a, b)
        print(f"Test add_numbers: {a} + {b} = {res} (Expected: {expected})")
        assert abs(res - expected) < 1e-9, f"Expected {expected}, got {res}"
        print("✅ Test add_numbers passed.")
    except Exception as e:
        print(f"❌ FAIL: Test add_numbers failed: {e}")
        sys.exit(1)

    # Test [2]: Subroutine double_array (1D array)
    try:
        arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        expected = arr * 2.0
        res_arr = interop_test_mod.double_array(arr)
        print(f"Test double_array: Input: {arr}, Output: {res_arr} (Expected: {expected})")
        assert np.allclose(res_arr, expected), f"Expected {expected}, got {res_arr}"
        print("✅ Test double_array passed.")
    except Exception as e:
        print(f"❌ FAIL: Test double_array failed: {e}")
        sys.exit(1)

    # Test [3]: Subroutine scale_matrix (2D array)
    try:
        matrix = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
        scale = 3.0
        expected = matrix * scale
        res_matrix = interop_test_mod.scale_matrix(matrix, scale)
        print(f"Test scale_matrix: Scale: {scale}\nInput Matrix:\n{matrix}\nOutput Matrix:\n{res_matrix}\nExpected:\n{expected}")
        assert np.allclose(res_matrix, expected), f"Expected:\n{expected}\ngot:\n{res_matrix}"
        print("✅ Test scale_matrix passed.")
    except Exception as e:
        print(f"❌ FAIL: Test scale_matrix failed: {e}")
        sys.exit(1)

    # Clean up generated files and artifacts
    for f in [c_mod_file, py_wrapper_file, lib_path]:
        if os.path.exists(f):
            os.remove(f)

    # Delete __pycache__ inside test/
    pycache = os.path.join(test_dir, "__pycache__")
    if os.path.exists(pycache):
        shutil.rmtree(pycache)

    print("=" * 60)
    print("     ALL INTEROP BINDING GENERATION TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    main()
