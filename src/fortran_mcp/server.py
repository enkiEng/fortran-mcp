import os
import sys
import subprocess
import shutil
import tempfile
from typing import Optional, List
from fastmcp import FastMCP

from fortran_mcp.linter import FortranLinter

# Initialize FastMCP Server
mcp = FastMCP("Fortran Companion")

def get_fprettify_path() -> Optional[str]:
    """Helper to locate fprettify executable in the environment."""
    # Check current active python prefix bin
    venv_bin = os.path.join(sys.prefix, 'bin', 'fprettify')
    if os.path.exists(venv_bin):
        return venv_bin
        
    # Check local relative .venv
    local_venv = os.path.join(os.getcwd(), '.venv', 'bin', 'fprettify')
    if os.path.exists(local_venv):
        return local_venv
        
    # Fallback to system PATH
    sh_path = shutil.which("fprettify")
    if sh_path:
        return sh_path
        
    return None

@mcp.tool()
def explain_best_practices() -> str:
    """Returns a comprehensive guide of modern Fortran coding standards, design patterns, and practices."""
    return """# Modern Fortran Best Practices Guide

This guide describes coding practices that prevent common bugs and enhance readability and maintenance of Fortran programs. Enforce these design patterns when generating or modifying code:

## 1. Safety and Scoping
* **Always Declare `implicit none`**: Place `implicit none` at the beginning of every module and program. Never rely on Fortran's default implicit typing (I-N integers, others reals).
* **Use Modules for Procedures**: Encapsulate subroutines and functions inside `module` blocks and define them inside a `contains` section. This forces the compiler to check argument interfaces and types at compile time.
* **Avoid External Procedures**: Do not use standalone, un-encapsulated subroutines unless calling legacy code or interfacing with C.

## 2. Type Precision
* **Avoid Non-Standard Types**: Never use legacy syntax like `real*8` or `integer*4`. These are vendor extensions and are not standard-compliant.
* **Avoid `double precision`**: While standard, it is less flexible.
* **Use Named KIND Constants**: Define a double-precision parameter (often named `dp` or `wp`) using the intrinsic module `iso_fortran_env`:
  ```fortran
  use, intrinsic :: iso_fortran_env, only : dp => real64, ip => int64
  real(kind=dp) :: variable_name
  ```
* **Declare Constants with Suffixes**: When declaring literal constants, append the kind parameter to prevent precision truncation during evaluation:
  ```fortran
  real(dp) :: x
  x = 3.141592653589793_dp  ! Enforces evaluation at dp precision
  ```

## 3. Procedure Arguments
* **Always Declare `intent`**: Every dummy argument in a subroutine or function MUST have an explicit intent attribute:
  * `intent(in)`: Argument is read-only.
  * `intent(out)`: Argument is write-only (gets re-initialized at call site).
  * `intent(inout)`: Argument is both read and written.
* **Pass Arrays as Assumed-Shape**: Declare dummy arrays as `real(dp) :: array(:)` instead of legacy explicit dimensions (`real :: array(N)`) or assumed-size (`real :: array(*)`). Assumed-shape arrays carry dimension metadata.

## 4. Modern Control Flow & Design
* **Use Block Constructs**: Do not use line-numbered loops (`do 10 i = 1, n` / `10 continue`) or `goto` statements. Use standard loop structures (`do i = 1, n ... end do`) and structural jump keywords (`cycle`, `exit`).
* **Use Modern Array Operations**: Prefer array slicing (`y = x(1:5)`) and intrinsic array functions (e.g. `sum`, `matmul`, `size`, `shape`) over manual loops where applicable.
* **Error Handling with Allocation**: When dynamically allocating arrays, always supply the `stat` and `errmsg` arguments to gracefully handle memory exhaustion:
  ```fortran
  allocate(array(10000), stat=status, errmsg=msg)
  if (status /= 0) then
      print *, "Allocation failed: ", trim(msg)
      error stop
  end if
  ```
"""

@mcp.tool()
def lint_code(code: str) -> str:
    """Statically analyzes a string of Fortran code for legacy syntax, implicit typing, missing intents, and bad practices."""
    linter = FortranLinter(code)
    warnings = linter.lint()
    
    if not warnings:
        return "Lint check complete: No issues or legacy practices found! Code follows modern design patterns."
        
    report = [f"Fortran Static Analysis Report: Found {len(warnings)} issue(s)\n" + "="*50]
    for w in warnings:
        report.append(f"Line {w['line']}: [{w['rule'].upper()}] ({w['severity']})")
        report.append(f"  Code: {w['code']}")
        report.append(f"  Issue: {w['message']}")
        report.append("-" * 30)
    return "\n".join(report)

@mcp.tool()
def lint_file(file_path: str) -> str:
    """Statically analyzes a local Fortran source file for legacy syntax, implicit typing, missing intents, and bad practices."""
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        return lint_code(code)
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"

@mcp.tool()
def format_code(code: str) -> str:
    """Auto-formats a string of Fortran code using fprettify to enforce modern indentation and spacing."""
    fprettify_bin = get_fprettify_path()
    if not fprettify_bin:
        return "Error: 'fprettify' formatter tool was not found in the environment."
        
    try:
        # Run fprettify as subprocess with stdin/stdout
        process = subprocess.Popen(
            [fprettify_bin],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=code)
        
        if process.returncode != 0:
            return f"Formatting failed: {stderr}"
            
        return stdout
    except Exception as e:
        return f"Error formatting code: {str(e)}"

@mcp.tool()
def format_file(file_path: str) -> str:
    """Auto-formats a local Fortran file in-place using fprettify to enforce modern indentation and spacing."""
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"
        
    fprettify_bin = get_fprettify_path()
    if not fprettify_bin:
        return "Error: 'fprettify' formatter tool was not found in the environment."
        
    try:
        # Run fprettify in-place
        res = subprocess.run([fprettify_bin, "-i", file_path], capture_output=True, text=True)
        if res.returncode != 0:
            return f"Formatting failed: {res.stderr}"
        return f"Success: File '{file_path}' formatted in-place using fprettify."
    except Exception as e:
        return f"Error formatting file: {str(e)}"

@mcp.tool()
def initialize_project(project_path: str, project_name: str, fortran_version: str = "f2018") -> str:
    """Initializes a new, modern Fortran project at the specified path. Uses fpm if available, or bootstraps a standard layout with a Makefile.
    
    Args:
        project_path: The directory path to create the project in.
        project_name: The name of the project.
        fortran_version: The Fortran standard version to configure (e.g. 'f90', 'f95', 'f2003', 'f2008', 'f2018', 'f2023'). Defaults to 'f2018'.
    """
    os.makedirs(project_path, exist_ok=True)
    
    # Check if fpm is installed
    fpm_bin = shutil.which("fpm")
    if fpm_bin:
        try:
            # We initialize via fpm in the directory parent
            parent_dir = os.path.dirname(project_path.rstrip(os.sep))
            base_name = os.path.basename(project_path.rstrip(os.sep))
            if not parent_dir:
                parent_dir = "."
                
            res = subprocess.run(
                [fpm_bin, "new", base_name, "--with-executable"],
                cwd=parent_dir,
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                # Also add standard compiler flags to fpm.toml if we want,
                # but standard fpm defaults are usually fine.
                return f"Success: Initialized modern Fortran project '{project_name}' using fpm at '{project_path}'."
        except Exception:
            pass
            
    # Fallback/Manual setup of a modern project structure
    try:
        src_dir = os.path.join(project_path, "src")
        app_dir = os.path.join(project_path, "app")
        test_dir = os.path.join(project_path, "test")
        
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(app_dir, exist_ok=True)
        os.makedirs(test_dir, exist_ok=True)
        
        # 1. Write standard module
        module_code = f"""module {project_name}_module
  ! Force explicit declaration of all variables
  implicit none

  ! Modern kind parameter selection (double precision)
  use, intrinsic :: iso_fortran_env, only : dp => real64

contains

  ! Subroutine with explicit argument intents
  subroutine greet(name, greeting)
    character(len=*), intent(in) :: name
    character(len=*), intent(out) :: greeting

    greeting = "Hello, " // name // "!"
  end subroutine greet

end module {project_name}_module
"""
        with open(os.path.join(src_dir, f"{project_name}_module.f90"), "w") as f:
            f.write(module_code)
            
        # 2. Write main application entrypoint
        app_code = f"""program main
  use {project_name}_module, only : greet
  implicit none

  character(len=100) :: message

  call greet("Fortran Developer", message)
  print *, trim(message)

end program main
"""
        with open(os.path.join(app_dir, "main.f90"), "w") as f:
            f.write(app_code)
            
        # 3. Write basic unit test runner
        test_code = f"""program main_test
  use {project_name}_module, only : greet
  implicit none

  character(len=100) :: message

  call greet("Tester", message)
  if (trim(message) == "Hello, Tester!") then
     print *, "Test PASSED"
  else
     print *, "Test FAILED"
     call exit(1)
  end if

end program main_test
"""
        with open(os.path.join(test_dir, "main_test.f90"), "w") as f:
            f.write(test_code)
            
        # 4. Write Makefile configured for strict checking and standard version
        makefile_code = f"""FC = gfortran
FFLAGS = -Wall -Wextra -Wimplicit-interface -fcheck=all -std={fortran_version} -Iobj
SRC_DIR = src
APP_DIR = app
TEST_DIR = test
OBJ_DIR = obj
BIN_DIR = bin

all: build

build:
	mkdir -p $(OBJ_DIR) $(BIN_DIR)
	$(FC) $(FFLAGS) -c $(SRC_DIR)/{project_name}_module.f90 -o $(OBJ_DIR)/{project_name}_module.o -J$(OBJ_DIR)
	$(FC) $(FFLAGS) $(OBJ_DIR)/{project_name}_module.o $(APP_DIR)/main.f90 -o $(BIN_DIR)/main -J$(OBJ_DIR)

test:
	mkdir -p $(OBJ_DIR) $(BIN_DIR)
	$(FC) $(FFLAGS) -c $(SRC_DIR)/{project_name}_module.f90 -o $(OBJ_DIR)/{project_name}_module.o -J$(OBJ_DIR)
	$(FC) $(FFLAGS) $(OBJ_DIR)/{project_name}_module.o $(TEST_DIR)/main_test.f90 -o $(BIN_DIR)/test_runner -J$(OBJ_DIR)
	./$(BIN_DIR)/test_runner

run: build
	./$(BIN_DIR)/main

clean:
	rm -rf $(OBJ_DIR) $(BIN_DIR)
"""
        with open(os.path.join(project_path, "Makefile"), "w") as f:
            f.write(makefile_code)
            
        return (f"Success: Bootstrapped modern Fortran template structure at '{project_path}' (standard: {fortran_version}) "
                f"(Includes src/module, app/main, test/runner, and standard Makefile with strict flags).")
    except Exception as e:
        return f"Error bootstrapping project: {str(e)}"

@mcp.tool()
def compile_project(project_path: str, fortran_version: str = "f2018") -> str:
    """Compiles the Fortran project. Automatically detects and runs 'fpm build' or 'make' depending on layout.
    
    Args:
        project_path: The path of the project.
        fortran_version: The Fortran standard version to enforce (e.g. 'f95', 'f2003', 'f2008', 'f2018', 'f2023'). Defaults to 'f2018'.
    """
    if not os.path.exists(project_path):
        return f"Error: Project path does not exist: {project_path}"
        
    is_fpm = os.path.exists(os.path.join(project_path, "fpm.toml"))
    is_makefile = os.path.exists(os.path.join(project_path, "Makefile"))
    
    if is_fpm:
        fpm_bin = shutil.which("fpm")
        if not fpm_bin:
            return "Error: Found 'fpm.toml' but fpm is not installed in the environment."
        try:
            res = subprocess.run([fpm_bin, "build", "--flag", f"-std={fortran_version}"], cwd=project_path, capture_output=True, text=True)
            output = f"FPM Build Completed (Exit code: {res.returncode})\nSTDOUT:\n{res.stdout}"
            if res.stderr:
                output += f"\nSTDERR:\n{res.stderr}"
            return output
        except Exception as e:
            return f"Error executing fpm build: {str(e)}"
            
    if is_makefile:
        make_bin = shutil.which("make")
        if not make_bin:
            return "Error: Found 'Makefile' but make is not installed in the environment."
        try:
            # Overwrite FFLAGS in the Makefile to specify standard flag
            res = subprocess.run(
                [make_bin, "build", f"FFLAGS=-Wall -Wextra -Wimplicit-interface -fcheck=all -std={fortran_version} -Iobj"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            if res.returncode != 0:
                res = subprocess.run(
                    [make_bin, f"FFLAGS=-Wall -Wextra -Wimplicit-interface -fcheck=all -std={fortran_version} -Iobj"],
                    cwd=project_path,
                    capture_output=True,
                    text=True
                )
                
            output = f"Make Build Completed (Exit code: {res.returncode})\nSTDOUT:\n{res.stdout}"
            if res.stderr:
                output += f"\nSTDERR:\n{res.stderr}"
            return output
        except Exception as e:
            return f"Error executing make: {str(e)}"
            
    return ("Error: Could not find build configuration. "
            "Please ensure either 'fpm.toml' or 'Makefile' is present in the project path.")

@mcp.tool()
def run_tests(project_path: str) -> str:
    """Runs tests for the project. Automatically detects and runs 'fpm test' or 'make test' depending on layout."""
    if not os.path.exists(project_path):
        return f"Error: Project path does not exist: {project_path}"
        
    is_fpm = os.path.exists(os.path.join(project_path, "fpm.toml"))
    is_makefile = os.path.exists(os.path.join(project_path, "Makefile"))
    
    if is_fpm:
        fpm_bin = shutil.which("fpm")
        if not fpm_bin:
            return "Error: Found 'fpm.toml' but fpm is not installed in the environment."
        try:
            res = subprocess.run([fpm_bin, "test"], cwd=project_path, capture_output=True, text=True)
            output = f"FPM Test Executed (Exit code: {res.returncode})\nSTDOUT:\n{res.stdout}"
            if res.stderr:
                output += f"\nSTDERR:\n{res.stderr}"
            return output
        except Exception as e:
            return f"Error executing fpm test: {str(e)}"
            
    if is_makefile:
        make_bin = shutil.which("make")
        if not make_bin:
            return "Error: Found 'Makefile' but make is not installed in the environment."
        try:
            res = subprocess.run([make_bin, "test"], cwd=project_path, capture_output=True, text=True)
            output = f"Make Test Executed (Exit code: {res.returncode})\nSTDOUT:\n{res.stdout}"
            if res.stderr:
                output += f"\nSTDERR:\n{res.stderr}"
            return output
        except Exception as e:
            return f"Error executing make test: {str(e)}"
            
    return "Error: Could not find testing configuration. Please ensure either 'fpm.toml' or 'Makefile' is present."

@mcp.tool()
def suggest_design_pattern(pattern_name: str) -> str:
    """Provides boilerplate templates and architectural explanations for modern Fortran design patterns (OOP, generics, RAII, callbacks, C interop).
    
    Args:
        pattern_name: The pattern to retrieve. Supported options:
                      - 'oop': Object-oriented programming (derived types, inheritance, polymorphism, deferred bindings).
                      - 'generics': Generic interfaces and function overloading based on dummy argument types.
                      - 'raii': Resource Acquisition Is Initialization and automated heap memory management using 'allocatable'.
                      - 'callback': Strategy pattern and callback functions using abstract interfaces and procedure pointers.
                      - 'c_interop': Standardized interoperability with C/C++ or bindings for Python (using iso_c_binding).
    """
    name = pattern_name.lower()
    if "oop" in name or "object" in name:
        return """# Object-Oriented Programming (OOP) in Fortran
Modern Fortran (F2003 and later) supports object-oriented principles, including type extension (inheritance), polymorphism (`class` vs `type`), type-bound procedures, and abstract types with deferred bindings.

## Boilerplate Example: Shapes Hierarchy
```fortran
module shapes_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none
  private
  public :: shape_t, circle_t, square_t

  ! Abstract Base Class
  type, abstract :: shape_t
    character(len=20) :: name = "Generic Shape"
  contains
    ! Deferred procedure acts like a pure virtual function
    procedure(get_area_interface), deferred :: get_area
  end type shape_t

  ! Abstract interface for the deferred binding
  abstract interface
    function get_area_interface(this) result(area)
      import :: shape_t, dp
      class(shape_t), intent(in) :: this
      real(dp) :: area
    end function get_area_interface
  end interface

  ! Extended Class: Circle (Inherits from shape_t)
  type, extends(shape_t) :: circle_t
    real(dp) :: radius
  contains
    procedure :: get_area => get_circle_area
  end type circle_t

  ! Extended Class: Square (Inherits from shape_t)
  type, extends(shape_t) :: square_t
    real(dp) :: side
  contains
    procedure :: get_area => get_square_area
  end type square_t

contains

  function get_circle_area(this) result(area)
    class(circle_t), intent(in) :: this
    real(dp) :: area
    real(dp), parameter :: pi = 3.141592653589793_dp
    area = pi * this%radius**2
  end function get_circle_area

  function get_square_area(this) result(area)
    class(square_t), intent(in) :: this
    real(dp) :: area
    area = this%side**2
  end function get_square_area
end module shapes_mod
```
"""
    elif "generic" in name or "overload" in name:
        return """# Generic Programming via Interface Overloading
Fortran does not support C++ style templates or Rust generics. Instead, it utilizes generic interfaces to map a single generic procedure name to multiple specific implementations depending on the types of the dummy arguments passed.

## Boilerplate Example: Generic Addition Overloading
```fortran
module math_utils_mod
  implicit none
  private
  public :: add

  ! Generic interface that overloads the name 'add'
  interface add
     module procedure add_integers
     module procedure add_reals
  end interface add

contains

  elemental function add_integers(a, b) result(res)
    integer, intent(in) :: a, b
    integer :: res
    res = a + b
  end function add_integers

  elemental function add_reals(a, b) result(res)
    real, intent(in) :: a, b
    real :: res
    res = a + b
  end function add_reals
end module math_utils_mod
```
"""
    elif "raii" in name or "resource" in name or "memory" in name:
        return """# RAII & Resource Management in Modern Fortran
Fortran handles memory safety and cleanups automatically through the `allocatable` attribute. Any allocatable array or derived-type element is automatically deallocated by the compiler when it goes out of scope, avoiding memory leaks.

## Boilerplate Example: Safe Managed Buffer Wrapper
```fortran
module raii_mod
  implicit none
  private
  public :: safe_buffer_t

  type :: safe_buffer_t
     ! Allocatable arrays are automatically cleaned up (no destructor needed)
     real, allocatable :: data(:)
  contains
     procedure :: init => init_buffer
     ! If raw pointer variables are used, define a custom destructor:
     ! final :: finalize_buffer
  end type safe_buffer_t

contains
  subroutine init_buffer(this, n)
     class(safe_buffer_t), intent(inout) :: this
     integer, intent(in) :: n
     integer :: stat
     character(len=100) :: err_msg

     ! Allocate with status checking (prevents silent allocation crashes)
     allocate(this%data(n), stat=stat, errmsg=err_msg)
     if (stat /= 0) then
        print *, "Error allocating buffer: ", trim(err_msg)
        error stop
     end if
  end subroutine init_buffer
end module raii_mod
```
"""
    elif "callback" in name or "strategy" in name or "interface" in name:
        return """# Callback & Strategy Pattern via Procedure Pointers
Fortran procedures can be passed as arguments or stored as pointers in derived types, allowing dynamic callbacks and modular implementations of algorithms (Strategy pattern).

## Boilerplate Example: Integrator Callback
```fortran
module integration_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none
  private
  public :: integrand_func, integrate_midpoint

  ! Abstract interface defining the callback signature
  abstract interface
     function integrand_func(x) result(y)
        import :: dp
        real(dp), intent(in) :: x
        real(dp) :: y
     end function integrand_func
  end interface

contains

  ! Performs midpoint rule integration using the pluggable callback 'f'
  function integrate_midpoint(f, a, b, n) result(integral)
     procedure(integrand_func) :: f ! Pluggable callback procedure
     real(dp), intent(in) :: a, b
     integer, intent(in) :: n
     real(dp) :: integral

     real(dp) :: h, x
     integer :: i

     h = (b - a) / n
     integral = 0.0_dp
     do i = 1, n
        x = a + (i - 0.5_dp) * h
        integral = integral + f(x)
     end do
     integral = integral * h
  end function integrate_midpoint
end module integration_mod
```
"""
    elif "c_interop" in name or "c" in name or "bridge" in name:
        return """# C Interoperability (Bridge Pattern)
Fortran 2003 introduced `iso_c_binding` to establish a standard-compliant binding layer for C. It matches data sizes across systems and compiles procedures without compiler-dependent Fortran name-mangling, making it easy to call Fortran from C/C++/Python.

## Boilerplate Example: C Bindings module
```fortran
module c_bindings_mod
  use, intrinsic :: iso_c_binding
  implicit none
  private
  public :: compute_square

contains

  ! Exposes the function to C with the linker symbol 'compute_square'
  subroutine compute_square(c_in, c_out) bind(c, name="compute_square")
    ! Ensure parameters use types prefixed with c_
    real(c_double), intent(in), value :: c_in
    real(c_double), intent(out) :: c_out

    c_out = c_in * c_in
  end subroutine compute_square
end module c_bindings_mod
```
"""
    else:
        return f"Unknown design pattern '{pattern_name}'. Supported patterns: oop, generics, raii, callback, c_interop."

if __name__ == "__main__":
    mcp.run()

