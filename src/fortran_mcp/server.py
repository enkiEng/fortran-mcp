import os
import sys
import re
import subprocess
import shutil
import tempfile
import importlib.resources
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
def format_code(
    code: str,
    indent: int = 3,
    line_length: int = 132,
    whitespace: int = 2,
    strict_indent: bool = False,
    enable_decl: bool = False
) -> str:
    """Auto-formats a string of Fortran code using fprettify to enforce modern indentation and spacing.
    
    Args:
        code: The Fortran code content to format.
        indent: Relative indentation width (default: 3).
        line_length: Column after which a line should end (default: 132).
        whitespace: Preset (0-4) for the amount of whitespace (default: 2).
        strict_indent: Strictly impose indentation even for nested loops (default: False).
        enable_decl: Enable whitespace formatting of declarations (default: False).
    """
    fprettify_bin = get_fprettify_path()
    if not fprettify_bin:
        return "Error: 'fprettify' formatter tool was not found in the environment."
        
    try:
        cmd = [fprettify_bin, "-i", str(indent), "-l", str(line_length), "-w", str(whitespace)]
        if strict_indent:
            cmd.append("--strict-indent")
        if enable_decl:
            cmd.append("--enable-decl")

        # Run fprettify as subprocess with stdin/stdout
        process = subprocess.Popen(
            cmd,
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
def format_file(
    file_path: str,
    indent: int = 3,
    line_length: int = 132,
    whitespace: int = 2,
    strict_indent: bool = False,
    enable_decl: bool = False
) -> str:
    """Auto-formats a local Fortran file in-place using fprettify to enforce modern indentation and spacing.
    
    Args:
        file_path: Absolute path to the Fortran file.
        indent: Relative indentation width (default: 3).
        line_length: Column after which a line should end (default: 132).
        whitespace: Preset (0-4) for the amount of whitespace (default: 2).
        strict_indent: Strictly impose indentation even for nested loops (default: False).
        enable_decl: Enable whitespace formatting of declarations (default: False).
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"
        
    fprettify_bin = get_fprettify_path()
    if not fprettify_bin:
        return "Error: 'fprettify' formatter tool was not found in the environment."
        
    try:
        cmd = [fprettify_bin, "-i", str(indent), "-l", str(line_length), "-w", str(whitespace)]
        if strict_indent:
            cmd.append("--strict-indent")
        if enable_decl:
            cmd.append("--enable-decl")
        cmd.append(file_path)

        # Run fprettify in-place
        res = subprocess.run(cmd, capture_output=True, text=True)
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

def _locate_patterns_file() -> Optional[str]:
    """Locate design_patterns.md across editable and wheel installs.

    Resolution order:
      1. FORTRAN_MCP_PATTERNS env override (non-standard deployments).
      2. The copy packaged inside fortran_mcp/ (works for wheel + editable installs).
      3. Legacy fallback to the repo root (older source checkouts).
    """
    override = os.environ.get("FORTRAN_MCP_PATTERNS")
    if override:
        return override if os.path.exists(override) else None

    # Packaged data file shipped alongside this module.
    try:
        resource = importlib.resources.files("fortran_mcp").joinpath("design_patterns.md")
        if resource.is_file():
            return str(resource)
    except (ModuleNotFoundError, AttributeError, TypeError):
        pass

    # Legacy: file located at the repo root, two levels up from this module.
    legacy = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "design_patterns.md")
    )
    return legacy if os.path.exists(legacy) else None


def extract_pattern_from_file(pattern_name: str) -> Optional[str]:
    """Helper to dynamically extract pattern sections from the packaged design_patterns.md."""
    file_path = _locate_patterns_file()
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.splitlines()
        section_start = -1
        section_level = 0
        clean_name = pattern_name.lower().strip()
        alias_map = {
            "factory method": "factory method",
            "factory": "factory method",
            "abstract factory": "factory method",
            "singleton": "singleton",
            "adapter": "adapter",
            "wrapper": "adapter",
            "composite": "composite",
            "strategy": "strategy",
            "observer": "observer",
            "command": "command",
            "elemental": "elemental",
            "submodule": "submodule",
            "submodules": "submodule",
            "raii": "raii",
            "destructor": "raii",
            "sorting": "sorting",
            "sort": "sorting",
            "polymorphic sort": "sorting",
            "callback sort": "sorting"
        }
        search_term = alias_map.get(clean_name, clean_name)
        for i, line in enumerate(lines):
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip().lower()
                if search_term in title:
                    section_start = i
                    section_level = level
                    break
        if section_start != -1:
            collected = []
            collected.append(lines[section_start])
            for i in range(section_start + 1, len(lines)):
                line = lines[i]
                if line.startswith("#"):
                    lvl = len(line) - len(line.lstrip("#"))
                    if lvl <= section_level:
                        break
                collected.append(line)
            return "\n".join(collected)
    except Exception:
        pass
    return None

@mcp.tool()
def suggest_design_pattern(pattern_name: str) -> str:
    """Provides boilerplate templates and architectural explanations for modern Fortran design patterns mapping to GoF / Refactoring.Guru.
    
    Args:
        pattern_name: The pattern to retrieve. Supports standard patterns: Factory Method, Abstract Factory, Builder, Singleton, Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy, Chain of Responsibility, Command, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor, RAII.
    """
    name = pattern_name.lower().strip()
    
    # 1. Try to extract from design_patterns.md first
    extracted = extract_pattern_from_file(name)
    if extracted:
        return extracted

    # 2. GoF design pattern dictionary for Fortran fallbacks/completions
    gof_patterns = {
        "builder": """# Builder Pattern in Fortran
The Builder pattern constructs complex objects step-by-step. In modern Fortran (F2003+), we implement this using type-bound functions that return pointers to the builder object, enabling method-chaining (fluent API) at call sites.

## Implementation Example: Mesh Config Builder
```fortran
module builder_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none
  private
  public :: mesh_config_t, mesh_builder_t

  type :: mesh_config_t
    real(dp) :: dx = 0.1_dp
    real(dp) :: dy = 0.1_dp
    integer :: nx = 100
    integer :: ny = 100
    character(len=20) :: mesh_type = "structured"
  end type mesh_config_t

  type :: mesh_builder_t
    private
    type(mesh_config_t) :: config
  contains
    procedure :: set_resolution => builder_set_res
    procedure :: set_dimensions => builder_set_dims
    procedure :: set_type => builder_set_type
    procedure :: build => builder_build
  end type mesh_builder_t

contains

  function builder_set_res(this, dx, dy) result(res_builder)
    class(mesh_builder_t), intent(inout) :: this
    real(dp), intent(in) :: dx, dy
    class(mesh_builder_t), pointer :: res_builder
    this%config%dx = dx
    this%config%dy = dy
    res_builder => this
  end function builder_set_res

  function builder_set_dims(this, nx, ny) result(res_builder)
    class(mesh_builder_t), intent(inout) :: this
    integer, intent(in) :: nx, ny
    class(mesh_builder_t), pointer :: res_builder
    this%config%nx = nx
    this%config%ny = ny
    res_builder => this
  end function builder_set_dims

  function builder_set_type(this, mesh_type) result(res_builder)
    class(mesh_builder_t), intent(inout) :: this
    character(len=*), intent(in) :: mesh_type
    class(mesh_builder_t), pointer :: res_builder
    this%config%mesh_type = mesh_type
    res_builder => this
  end function builder_set_type

  function builder_build(this) result(res_config)
    class(mesh_builder_t), intent(in) :: this
    type(mesh_config_t) :: res_config
    res_config = this%config
  end function builder_build
end module builder_mod
```
""",
        "facade": """# Facade Pattern in Fortran
A Facade provides a simplified, high-level interface to a complex subsystem. In Fortran, this is represented by a module that hides multi-file system complexity and exposes a clean, single-point-of-contact procedural API.

## Implementation Example: Simulation Manager Facade
```fortran
module solver_facade_mod
  use physical_grid_mod, only : grid_t, create_grid
  use numerical_discretizer_mod, only : discretize_system
  use matrix_solver_mod, only : solve_linear_system
  use postprocessor_mod, only : export_vtk
  implicit none
  private
  public :: run_simulation

contains

  subroutine run_simulation(nx, ny, t_max, output_file)
    integer, intent(in) :: nx, ny
    real, intent(in) :: t_max
    character(len=*), intent(in) :: output_file
    
    type(grid_t) :: grid
    real, allocatable :: A(:,:), b(:), u(:)

    ! Facade coordinates subsystem procedures cleanly
    grid = create_grid(nx, ny)
    call discretize_system(grid, A, b)
    allocate(u(size(b)))
    call solve_linear_system(A, b, u)
    call export_vtk(u, grid, output_file)
  end subroutine run_simulation
end module solver_facade_mod
```
""",
        "decorator": """# Decorator Pattern in Fortran
Decorators dynamically attach additional responsibilities to an object. In Fortran, decorators wrap base polymorphic types and delegate operations, adding middleware behaviors like CPU timing, error logging, or scaling.

## Implementation Example: Timer Decorator for Equations Solver
```fortran
module decorators_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none
  private
  public :: solver_t, basic_solver_t, timed_solver_t

  type, abstract :: solver_t
  contains
    procedure(solve_interface), deferred :: solve
  end type solver_t

  abstract interface
    subroutine solve_interface(this, u)
      import :: solver_t, dp
      class(solver_t), intent(inout) :: this
      real(dp), intent(inout) :: u(:)
    end subroutine solve_interface
  end interface

  type, extends(solver_t) :: basic_solver_t
  contains
    procedure :: solve => basic_solve
  end type basic_solver_t

  type, extends(solver_t) :: timed_solver_t
    class(solver_t), allocatable :: wrapped
  contains
    procedure :: solve => timed_solve
  end type timed_solver_t

contains

  subroutine basic_solve(this, u)
    class(basic_solver_t), intent(inout) :: this
    real(dp), intent(inout) :: u(:)
    u = u * 0.9_dp
  end subroutine basic_solve

  subroutine timed_solve(this, u)
    class(timed_solver_t), intent(inout) :: this
    real(dp), intent(inout) :: u(:)
    real :: t1, t2
    
    if (allocated(this%wrapped)) then
       call cpu_time(t1)
       call this%wrapped%solve(u)
       call cpu_time(t2)
       print *, "Solver Time: ", (t2 - t1), " seconds"
    end if
  end subroutine timed_solve
end module decorators_mod
```
""",
        "observer": """# Observer Pattern in Fortran
The Observer pattern establishes a subscription model to notify multiple listeners when events occur. In Fortran, observers are represented by abstract observer types carrying event procedures registered inside solver subjects.

## Implementation Example: Solver Convergence Observer
```fortran
module observer_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none
  private
  public :: observer_t, solver_subject_t

  type, abstract :: observer_t
  contains
    procedure(notify_interface), deferred :: on_iteration_step
  end type observer_t

  abstract interface
    subroutine notify_interface(this, iter, residual)
      import :: observer_t, dp
      class(observer_t), intent(inout) :: this
      integer, intent(in) :: iter
      real(dp), intent(in) :: residual
    end subroutine notify_interface
  end interface

  type :: solver_subject_t
    private
    class(observer_t), pointer :: observers(:) => null()
  contains
    procedure :: register_observer
    procedure :: run_iterations
  end type solver_subject_t

contains

  subroutine register_observer(this, obs)
    class(solver_subject_t), intent(inout) :: this
    class(observer_t), target, intent(in) :: obs
    ! Observers array linking logic...
  end subroutine register_observer

  subroutine run_iterations(this, max_iter)
    class(solver_subject_t), intent(inout) :: this
    integer, intent(in) :: max_iter
    integer :: i
    real(dp) :: res = 0.9_dp

    do i = 1, max_iter
      res = res * 0.5_dp
      ! Broadcast solver progress to registered observers
      if (associated(this%observers)) then
         ! call loop through registered observer callbacks
      end if
    end do
  end subroutine run_iterations
end module observer_mod
```
""",
        "state": """# State Pattern in Fortran
The State pattern alters an object's behavior depending on its active state pointer. In Fortran, context classes delegate calculations to a polymorphic `class(state_t), allocatable :: current_state` instance.

## Implementation Example: Simulation Solver State Transitions
```fortran
module state_mod
  implicit none
  private
  public :: context_t, state_t, init_state_t, running_state_t

  type :: context_t
    class(state_t), allocatable :: current_state
  contains
    procedure :: set_state
    procedure :: request_action
  end type context_t

  type, abstract :: state_t
  contains
    procedure(handle_interface), deferred :: handle
  end type state_t

  abstract interface
    subroutine handle_interface(this, ctx)
      import :: state_t, context_t
      class(state_t), intent(in) :: this
      type(context_t), intent(inout) :: ctx
    end subroutine handle_interface
  end interface

  type, extends(state_t) :: init_state_t
  contains
    procedure :: handle => handle_init
  end type init_state_t

  type, extends(state_t) :: running_state_t
  contains
    procedure :: handle => handle_run
  end type running_state_t

contains

  subroutine set_state(this, next_state)
    class(context_t), intent(inout) :: this
    class(state_t), intent(in) :: next_state
    allocate(this%current_state, source=next_state)
  end subroutine set_state

  subroutine request_action(this)
    class(context_t), intent(inout) :: this
    if (allocated(this%current_state)) then
       call this%current_state%handle(this)
    end if
  end subroutine request_action

  subroutine handle_init(this, ctx)
    class(init_state_t), intent(in) :: this
    type(context_t), intent(inout) :: ctx
    print *, "Initializing simulation grid."
    call ctx%set_state(running_state_t())
  end subroutine handle_init

  subroutine handle_run(this, ctx)
    class(running_state_t), intent(in) :: this
    type(context_t), intent(inout) :: ctx
    print *, "Solving active equations."
  end subroutine handle_run
end module state_mod
```
""",
        "proxy": """# Proxy Pattern in Fortran
A Proxy controls access to another object (e.g. lazy evaluation, authorization, or logging wrappers). In Fortran, proxies wrap a target derived type and intercept calls.

## Implementation Example: Lazy Loaded Matrix Evaluation
```fortran
module proxy_mod
  implicit none
  private
  public :: resource_t, heavy_matrix_t, proxy_matrix_t

  type, abstract :: resource_t
  contains
    procedure(load_interface), deferred :: access_data
  end type resource_t

  abstract interface
    subroutine load_interface(this)
      import :: resource_t
      class(resource_t), intent(inout) :: this
    end subroutine load_interface
  end interface

  type, extends(resource_t) :: heavy_matrix_t
    real, allocatable :: values(:,:)
  contains
    procedure :: access_data => load_values
  end type heavy_matrix_t

  type, extends(resource_t) :: proxy_matrix_t
    private
    type(heavy_matrix_t), allocatable :: real_subject
  contains
    procedure :: access_data => proxy_access
  end type proxy_matrix_t

contains

  subroutine load_values(this)
    class(heavy_matrix_t), intent(inout) :: this
    allocate(this%values(5000,5000))
    print *, "Heavy matrix allocated and loaded."
  end subroutine load_values

  subroutine proxy_access(this)
    class(proxy_matrix_t), intent(inout) :: this
    if (.not. allocated(this%real_subject)) then
       allocate(this%real_subject)
       call this%real_subject%access_data()
    end if
    print *, "Accessing proxy wrapper data stream."
  end subroutine proxy_access
end module proxy_mod
```
""",
        "bridge": """# Bridge Pattern in Fortran
The Bridge pattern decouples abstraction from implementation. In Fortran, this allows us to split Grid calculations (e.g., Structured vs Unstructured) from Solver physics algorithms, so they can vary independently.

## Implementation Example: Decoupled Grid and Solver
```fortran
module bridge_mod
  implicit none
  private
  public :: grid_impl_t, solver_abstraction_t

  ! Implementation boundary (Bridge)
  type, abstract :: grid_impl_t
  contains
    procedure(stencil_interface), deferred :: apply_stencil
  end type grid_impl_t

  abstract interface
    subroutine stencil_interface(this, field)
      import :: grid_impl_t
      class(grid_impl_t), intent(in) :: this
      real, intent(inout) :: field(:)
    end subroutine stencil_interface
  end interface

  ! Abstraction boundary
  type :: solver_abstraction_t
    class(grid_impl_t), allocatable :: grid
  contains
    procedure :: run_step
  end type solver_abstraction_t

contains

  subroutine run_step(this, state)
    class(solver_abstraction_t), intent(inout) :: this
    real, intent(inout) :: state(:)
    if (allocated(this%grid)) then
       call this%grid%apply_stencil(state)
    end if
  end subroutine run_step
end module bridge_mod
```
"""
    }

    # Standard GoF pattern matching
    for key, template in gof_patterns.items():
        if key in name:
            return template

    # Original hardcoded patterns mapping if still needed
    if "oop" in name or "object" in name:
        return extracted if extracted else "OOP Shape Hierarchy not found."
    elif "generic" in name or "overload" in name:
        return extracted if extracted else "Generic interfaces not found."
    elif "raii" in name or "resource" in name or "memory" in name:
        return extracted if extracted else "RAII configurations not found."
    elif "callback" in name or "strategy" in name or "interface" in name:
        return extracted if extracted else "Callback procedures not found."
    elif "c_interop" in name or "c" in name or "bridge" in name:
        return extracted if extracted else "C Bindings and Bridge not found."
    else:
        supported = list(gof_patterns.keys()) + ["oop", "generics", "raii", "callback", "c_interop", "factory method", "singleton", "adapter", "composite", "strategy"]
        return f"Unknown design pattern '{pattern_name}'. Supported patterns include: {', '.join(supported)}."

@mcp.tool()
def suggest_refactoring(code: str, problem_description: Optional[str] = None) -> str:
    """Analyzes a block of Fortran code and suggests modern design patterns and refactoring options mapped to Refactoring Guru.
    
    Args:
        code: The Fortran code snippet to analyze.
        problem_description: Optional description of the problem or requirements.
    """
    suggestions = []
    
    # 1. Analyze common blocks
    if re.search(r'\bcommon\b', code, re.IGNORECASE):
        suggestions.append("""### 1. Refactor COMMON Blocks -> Singleton Pattern / Encapsulated Modules
*   **Problem:** Code contains legacy `COMMON` blocks. These bypass normal namespaces, make parallelization difficult (not thread-safe), and inhibit type safety.
*   **Pattern Solution (Singleton / Encapsulated Module):** Create a modern Fortran module containing private variables and public getter/setter procedures. This encapsulates the state, enables initialization logic, and controls access.
*   **Refactoring Guru Reference:** [Singleton Pattern](https://refactoring.guru/design-patterns/singleton)""")

    # 2. Analyze goto / labels
    if re.search(r'\bgoto\s+[0-9]+\b|\bgo\s+to\s+[0-9]+\b', code, re.IGNORECASE):
        suggestions.append("""### 2. Refactor GOTO Branching -> State Pattern / Structured Flow
*   **Problem:** GOTO statement(s) used for state transitions or error exits. This creates "spaghetti code" that is hard to follow or optimize.
*   **Pattern Solution (State / Command Pattern):** Restructure control flow using modern block constructs (`do/end do`, `cycle`, `exit`). For complex state machines, employ the **State Pattern** by encapsulating behaviors in polymorphic state types.
*   **Refactoring Guru Reference:** [State Pattern](https://refactoring.guru/design-patterns/state) / [Command Pattern](https://refactoring.guru/design-patterns/command)""")

    # 3. Analyze multi-solver conditional branching
    if re.search(r'\bif\b.*\bcall\s+\w+\b.*\belseif\b.*\bcall\s+\w+\b', code, re.IGNORECASE) or \
       re.search(r'\bselect\s+case\b', code, re.IGNORECASE):
        suggestions.append("""### 3. Refactor Conditional Solver Logic -> Strategy Pattern
*   **Problem:** Algorithms or solvers are selected using nested `if-then-else` or `select case` statements based on integer flags. This requires editing the main coordinator file every time a new method is added.
*   **Pattern Solution (Strategy Pattern):** Define an abstract type `solver_t` with deferred binding procedures, and implement specific algorithm implementations as extended types. Use a polymorphic variable (`class(solver_t), allocatable`) to invoke the correct execution path at runtime.
*   **Refactoring Guru Reference:** [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)""")

    # 4. Analyze procedural callbacks
    if re.search(r'\bprocedure\s*\([^)]*\)\s*,\s*pointer\b', code, re.IGNORECASE) or \
       re.search(r'\bexternal\b', code, re.IGNORECASE):
        suggestions.append("""### 4. Refactor Procedural Callbacks -> Abstract Interfaces (Strategy / Template Method)
*   **Problem:** Direct `external` statements or unconstrained procedure pointers are used. This makes it impossible for compilers to verify interface signatures, causing silent runtime stack corruption.
*   **Pattern Solution (Template Method / Strategy Pattern):** Wrap signatures inside standard Fortran `abstract interface` blocks, and declare dummy callback arguments using `procedure(interface_name)` or polymorphic wrapper types.
*   **Refactoring Guru Reference:** [Strategy Pattern](https://refactoring.guru/design-patterns/strategy) / [Template Method](https://refactoring.guru/design-patterns/template-method)""")

    # 5. Analyze long parameter lists
    # Count variables declared or passed in procedure definitions
    procedure_decl = re.findall(r'\b(subroutine|function)\s+\w+\s*\(([^)]*)\)', code, re.IGNORECASE)
    has_long_params = False
    if procedure_decl:
        for match in procedure_decl:
            args_str = match[1]
            args = [a.strip() for a in args_str.split(',') if a.strip()]
            if len(args) > 6:
                has_long_params = True
                break
                
    if has_long_params:
        suggestions.append("""### 5. Refactor Long Parameter Lists -> Builder Pattern / Parameter Type
*   **Problem:** Subroutine signature accepts a large number of parameters (e.g. > 6). This makes call sites hard to read, prone to parameter-swapping bugs, and fragile when new options are added.
*   **Pattern Solution (Builder Pattern):** Consolidate solver configurations into a single parameter/options derived type (`type(config_t)`). Use a **Builder** type with method-chaining procedures to initialize and assemble options step-by-step, then pass the single config instance to the solver.
*   **Refactoring Guru Reference:** [Builder Pattern](https://refactoring.guru/design-patterns/builder)""")

    # 6. Analyze low-level C bindings or raw pointer usage
    if re.search(r'\bbind\s*\(\s*c\b', code, re.IGNORECASE) or re.search(r'\bc_ptr\b', code, re.IGNORECASE):
        suggestions.append("""### 6. Refactor C Interoperability / Raw Pointers -> Adapter Pattern (Wrapper)
*   **Problem:** Low-level C bindings (`bind(c)`) or raw pointers (`type(c_ptr)`) are scattered throughout calculation modules.
*   **Pattern Solution (Adapter Pattern):** Create an object-oriented wrapper module (an **Adapter**) that abstracts C procedures and structures into safe, idiomatic modern Fortran derived types, hiding raw pointer manipulation from the rest of the application.
*   **Refactoring Guru Reference:** [Adapter Pattern](https://refactoring.guru/design-patterns/adapter)""")

    # Fallback/General suggestion based on description
    if problem_description:
        desc = problem_description.lower()
        if "decouple" in desc or "boundary" in desc or "grid" in desc:
            suggestions.append("""### 7. Decouple Math from Structure -> Bridge Pattern
*   **Problem:** Grid topology or boundary structure is tightly coupled to numerical mathematical operators.
*   **Pattern Solution (Bridge Pattern):** Define abstract boundaries between the Grid implementation and Solver algorithms, allowing them to vary independently.
*   **Refactoring Guru Reference:** [Bridge Pattern](https://refactoring.guru/design-patterns/bridge)""")
        if "log" in desc or "track" in desc or "print" in desc:
            suggestions.append("""### 8. Separate Logging from Logic -> Observer Pattern
*   **Problem:** Solver procedures have direct dependencies on terminal print / write statements.
*   **Pattern Solution (Observer Pattern):** Implement an event subscription model allowing logger or visualizer observers to hook into iteration steps without hardcoding write blocks inside physics code.
*   **Refactoring Guru Reference:** [Observer Pattern](https://refactoring.guru/design-patterns/observer)""")

    if not suggestions:
        # No higher-level structural pattern matched. Before declaring the code
        # modern, consult the linter so we don't give a false all-clear on files
        # that still carry legacy syntax (real*8, missing intents, fixed-format).
        lint_warnings = FortranLinter(code).lint()
        if lint_warnings:
            rules = sorted({w["rule"].lower() for w in lint_warnings})
            return ("### Design Patterns & Refactoring Report\n\n"
                    f"No higher-level structural refactoring pattern (COMMON, GOTO, solver "
                    f"branching, long parameter lists, C-interop) was detected, but static "
                    f"analysis flagged {len(lint_warnings)} legacy/style issue(s) "
                    f"({', '.join(rules)}). **This code is not yet modern.**\n\n"
                    "**Recommendation:** Run `lint_file` for the full report and `modernize_file` "
                    "to auto-apply baseline fixes (explicit kinds, modern operators), then "
                    "encapsulate procedures in modules with `implicit none` and explicit argument "
                    "`intent` attributes.")
        return ("### Design Patterns & Refactoring Report\n\n"
                "No legacy code warning flags matched and static analysis is clean. The code looks modern!\n\n"
                "**General Recommendation:** Ensure you are encapsulating procedures inside modules, "
                "specifying explicit intents, and disabling implicit typing with `implicit none`. "
                "Explore structural design patterns such as [Facade](https://refactoring.guru/design-patterns/facade) "
                "or behavioral patterns such as [Strategy](https://refactoring.guru/design-patterns/strategy) "
                "to keep your code modular.")
                
    report = ["# Modern Fortran Refactoring & Design Patterns Report",
              "We analyzed your code and matched structure signatures to Refactoring Guru design patterns. "
              "Here are suggested refactoring pathways to modernize the codebase:\n"]
    report.extend(suggestions)
    return "\n\n".join(report)

@mcp.tool()
def suggest_refactoring_file(file_path: str, problem_description: Optional[str] = None) -> str:
    """Analyzes a local Fortran file and suggests modern design patterns and refactoring options mapped to Refactoring Guru.
    
    Args:
        file_path: Absolute path to the Fortran file to analyze.
        problem_description: Optional description of the problem or requirements.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        return suggest_refactoring(code, problem_description)
    except Exception as e:
        return f"Error analyzing file: {str(e)}"

@mcp.tool()
def modernize_file(file_path: str, output_path: Optional[str] = None) -> str:
    """Performs automated syntax replacements to jumpstart modernizing a legacy Fortran file.
    Updates obsolete operators, converts legacy types, and formats spacing.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # 1. Replace relational operators
        content = re.sub(r'\b\.eq\.\b', '==', content, flags=re.IGNORECASE)
        content = re.sub(r'\b\.ne\.\b', '/=', content, flags=re.IGNORECASE)
        content = re.sub(r'\b\.gt\.\b', '>',  content, flags=re.IGNORECASE)
        content = re.sub(r'\b\.ge\.\b', '>=', content, flags=re.IGNORECASE)
        content = re.sub(r'\b\.lt\.\b', '<',  content, flags=re.IGNORECASE)
        content = re.sub(r'\b\.le\.\b', '<=', content, flags=re.IGNORECASE)
        
        # 2. Replace non-standard types
        content = re.sub(r'\breal\s*\*\s*8\b', 'real(kind=dp)', content, flags=re.IGNORECASE)
        content = re.sub(r'\binteger\s*\*\s*4\b', 'integer(kind=int32)', content, flags=re.IGNORECASE)
        content = re.sub(r'\bdouble\s+precision\b', 'real(kind=dp)', content, flags=re.IGNORECASE)
        
        # 3. Add kind imports if we did replacements
        if 'kind=dp' in content and 'dp => real64' not in content:
            # Try to insert at the beginning of the unit
            content = re.sub(
                r'(\bprogram\s+\w+|\bmodule\s+\w+)',
                r'\1\n  use, intrinsic :: iso_fortran_env, only : dp => real64',
                content,
                count=1,
                flags=re.IGNORECASE
            )
            
        if not output_path:
            base, ext = os.path.splitext(file_path)
            output_path = f"{base}_modernized.f90"
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Auto-format if fprettify is available
        fprettify_bin = get_fprettify_path()
        if fprettify_bin:
            subprocess.run([fprettify_bin, output_path], capture_output=True)
            
        return f"Success: Automated modernization applied. Output saved to '{output_path}'."
    except Exception as e:
        return f"Error during modernization: {str(e)}"

@mcp.tool()
def verify_regression(legacy_exe_command: str, modern_exe_command: str) -> str:
    """Runs a legacy binary and a modernized binary, comparing their outputs to verify that the refactoring has no regressions.
    
    Args:
        legacy_exe_command: Shell command to run the legacy binary.
        modern_exe_command: Shell command to run the modernized binary.
    """
    try:
        # Run legacy
        res_legacy = subprocess.run(legacy_exe_command, shell=True, capture_output=True, text=True)
        # Run modern
        res_modern = subprocess.run(modern_exe_command, shell=True, capture_output=True, text=True)
        
        report = []
        report.append("=== Refactoring Regression Verification Report ===")
        report.append(f"Legacy Command: '{legacy_exe_command}' (Exit: {res_legacy.returncode})")
        report.append(f"Modern Command: '{modern_exe_command}' (Exit: {res_modern.returncode})")
        
        if res_legacy.returncode != res_modern.returncode:
            report.append("❌ FAILURE: Exit codes do not match!")
            
        # Match output text
        diff_detected = False
        legacy_out = res_legacy.stdout.strip()
        modern_out = res_modern.stdout.strip()
        
        if legacy_out != modern_out:
            report.append("❌ WARNING: STDOUT outputs differ!")
            report.append(f"Legacy Output:\n{legacy_out[:200]}...")
            report.append(f"Modern Output:\n{modern_out[:200]}...")
            diff_detected = True
        else:
            report.append("✅ SUCCESS: Standard outputs match exactly!")
            
        if res_legacy.returncode == 0 and res_modern.returncode == 0 and not diff_detected:
            report.append("🎉 VERIFICATION PASSED: No regression detected.")
        else:
            report.append("⚠️ VERIFICATION WARNING: Differences detected in output or exit state.")
            
        return "\n".join(report)
    except Exception as e:
        return f"Error running verification: {str(e)}"

@mcp.tool()
def rename_legacy_identifiers(file_path: str, mapping: dict) -> str:
    """Safely renames legacy variables to descriptive modern names across a file scope.
    Validates scope rules, renames variables in code while preserving comments, and builds using compiler flags to verify correctness.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # Parse coding structures to check scoping
        linter = FortranLinter(content)
        
        # Build list of words already defined in the file (to detect duplicates)
        all_tokens = set(re.findall(r'\b[a-zA-Z_]\w*\b', content.lower()))
        
        # Check mapping for duplicates
        for old_name, new_name in mapping.items():
            if new_name.lower() in all_tokens and new_name.lower() != old_name.lower():
                return f"Error: Cannot rename '{old_name}' to '{new_name}'. The identifier '{new_name}' is already defined/used in this file scope."

        # Perform the actual replacement line by line, preserving comments
        lines = content.splitlines()
        for old_name, new_name in mapping.items():
            rx = re.compile(r'\b' + re.escape(old_name) + r'\b', re.IGNORECASE)
            for idx, line in enumerate(lines):
                # If fixed comment line, skip
                if line and line[0].lower() in ['c', '*']:
                    continue
                parts = line.split('!', 1)
                code_part = parts[0]
                comment_part = parts[1] if len(parts) > 1 else ""
                
                new_code = rx.sub(new_name, code_part)
                if len(parts) > 1:
                    lines[idx] = new_code + "!" + comment_part
                else:
                    lines[idx] = new_code
                    
        new_content = "\n".join(lines)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        # Auto-format in-place
        fprettify_bin = get_fprettify_path()
        if fprettify_bin:
            subprocess.run([fprettify_bin, file_path], capture_output=True)
            
        # Try compilation to verify correctness (if standard Makefile/fpm.toml is present nearby)
        proj_dir = os.path.dirname(file_path)
        comp_output = ""
        if os.path.exists(os.path.join(proj_dir, "Makefile")) or os.path.exists(os.path.join(proj_dir, "fpm.toml")) or \
           os.path.exists(os.path.join(proj_dir, "..", "Makefile")) or os.path.exists(os.path.join(proj_dir, "..", "fpm.toml")):
            # Find closest project directory with configuration
            target_proj = proj_dir
            if not (os.path.exists(os.path.join(target_proj, "Makefile")) or os.path.exists(os.path.join(target_proj, "fpm.toml"))):
                target_proj = os.path.abspath(os.path.join(proj_dir, ".."))
            comp_output = "\n" + compile_project(target_proj)
            
        return f"Success: Legacy identifiers renamed. In-place formatting applied.{comp_output}"
    except Exception as e:
        return f"Error during identifier renaming: {str(e)}"

@mcp.tool()
def convert_common_to_module(file_path: str, block_name: str, module_name: str) -> str:
    """Extracts a legacy COMMON block and generates an encapsulated modern Fortran module.
    Comments out the legacy COMMON statement and inserts matching module imports.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # 1. Match COMMON block line: common /block_name/ var1, var2...
        # Also handles continuation lines
        lines = content.splitlines()
        common_line_idx = -1
        vars_part = ""
        
        # Regex to match the common statement start
        common_start_rx = re.compile(r'^\s*common\s*/\s*' + re.escape(block_name) + r'\s*/', re.IGNORECASE)
        
        for idx, line in enumerate(lines):
            # Clean comments for checking
            clean = line.split('!')[0].strip()
            if not clean:
                continue
            if line and line[0].lower() in ['c', '*']:
                continue
                
            if common_start_rx.match(clean):
                common_line_idx = idx
                # Extract variables list from the common block
                match = re.match(r'^\s*common\s*/\s*' + re.escape(block_name) + r'\s*/\s*([^!\n]+)', line, re.IGNORECASE)
                if match:
                    vars_part = match.group(1).strip()
                    # Check next lines for continuations
                    j = idx + 1
                    while j < len(lines):
                        next_line = lines[j]
                        clean_next = next_line.split('!')[0]
                        # Check fixed-format continuation (non-blank at col 6, or C/* comment skip)
                        if len(next_line) > 5 and next_line[0] == ' ' and next_line[5] not in [' ', '0'] and not clean_next.strip().startswith('!'):
                            vars_part += " " + clean_next[6:].strip()
                            j += 1
                        # Check free-format continuation (preceding line has & or current starts with &)
                        elif clean_next.strip().startswith('&'):
                            vars_part += " " + clean_next.strip()[1:].strip()
                            j += 1
                        else:
                            break
                    break
                    
        if common_line_idx == -1 or not vars_part:
            return f"Error: Could not locate COMMON block named '{block_name}' in '{file_path}'."
            
        # Parse variable names
        var_names = [v.strip() for v in vars_part.split(',') if v.strip()]
        
        # 2. Extract types of these variables from the file
        var_types = {}
        for var in var_names:
            # Look for declaration line of var in the file
            found_type = None
            for line in lines:
                clean_line = line.split('!')[0].strip()
                if not clean_line or clean_line[0].lower() in ['c', '*']:
                    continue
                # Match type declarations
                type_match = re.match(
                    r'^\s*(real\*\d+|integer\*\d+|double precision|real|integer|logical|character\b.*?|complex)(?:\s*,\s*[^:]+)?\s*(?:::\s*)?(?:[^!]*\b)' + re.escape(var) + r'\b',
                    clean_line,
                    re.IGNORECASE
                )
                if type_match:
                    found_type = type_match.group(1).lower().strip()
                    break
                    
            if not found_type:
                # Implicit fallback: I-N integer, else real(dp)
                if var[0].lower() in ['i', 'j', 'k', 'l', 'm', 'n']:
                    found_type = "integer"
                else:
                    found_type = "real(kind=dp)"
            else:
                # Modernize type names
                if "real*8" in found_type or "double precision" in found_type:
                    found_type = "real(kind=dp)"
                elif "integer*4" in found_type:
                    found_type = "integer(kind=int32)"
                    
            var_types[var] = found_type
            
        # 3. Create the module code
        proj_dir = os.path.dirname(file_path)
        module_file_path = os.path.join(proj_dir, f"{module_name}.f90")
        
        module_code = [
            f"module {module_name}",
            "  use, intrinsic :: iso_fortran_env, only : dp => real64, int32",
            "  implicit none",
            "  public",
            ""
        ]
        for var, vtype in var_types.items():
            module_code.append(f"  {vtype} :: {var}")
        module_code.append(f"end module {module_name}\n")
        
        with open(module_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(module_code))
            
        # 4. Comment out COMMON statement and insert USE import statement in the source file
        scoping_start_idx = 0
        scope_rx = re.compile(r'^\s*(program|subroutine|function|module)\s+\w+', re.IGNORECASE)
        for i in range(common_line_idx, -1, -1):
            if scope_rx.match(lines[i].split('!')[0]):
                scoping_start_idx = i
                break
                
        # Insert USE statement right after scoping unit header
        use_stmt = f"  use {module_name}, only : " + ", ".join(var_names)
        
        insert_idx = scoping_start_idx + 1
        implicit_none_rx = re.compile(r'^\s*implicit\s+none\b', re.IGNORECASE)
        for i in range(scoping_start_idx + 1, common_line_idx):
            if implicit_none_rx.match(lines[i].split('!')[0]):
                insert_idx = i + 1
                break
                
        lines.insert(insert_idx, use_stmt)
        common_line_idx += 1
        
        # Comment out the common block line and any subsequent continuation lines
        lines[common_line_idx] = "! " + lines[common_line_idx]
        j = common_line_idx + 1
        while j < len(lines):
            next_line = lines[j]
            clean_next = next_line.split('!')[0]
            if len(next_line) > 5 and next_line[0] == ' ' and next_line[5] not in [' ', '0'] and not clean_next.strip().startswith('!'):
                lines[j] = "! " + lines[j]
                j += 1
            elif clean_next.strip().startswith('&'):
                lines[j] = "! " + lines[j]
                j += 1
            else:
                break
                
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
        # Format both files
        fprettify_bin = get_fprettify_path()
        if fprettify_bin:
            subprocess.run([fprettify_bin, file_path], capture_output=True)
            subprocess.run([fprettify_bin, module_file_path], capture_output=True)
            
        # Compile if compilation is possible
        comp_output = ""
        if os.path.exists(os.path.join(proj_dir, "Makefile")) or os.path.exists(os.path.join(proj_dir, "fpm.toml")) or \
           os.path.exists(os.path.join(proj_dir, "..", "Makefile")) or os.path.exists(os.path.join(proj_dir, "..", "fpm.toml")):
            target_proj = proj_dir
            if not (os.path.exists(os.path.join(target_proj, "Makefile")) or os.path.exists(os.path.join(target_proj, "fpm.toml"))):
                target_proj = os.path.abspath(os.path.join(proj_dir, ".."))
            comp_output = "\n" + compile_project(target_proj)
            
        return f"Success: Converted COMMON block '{block_name}' into module '{module_name}' at '{module_file_path}'.{comp_output}"
    except Exception as e:
        return f"Error converting COMMON block: {str(e)}"

@mcp.tool()
def analyze_pure_candidates(file_path: str) -> str:
    """Scans procedures in a file and identifies subprograms suitable for 'pure' or 'elemental' attributes.
    Helps promote parallelization, vectorization, and side-effect-free code design.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        linter = FortranLinter(code)
        procedures = linter.find_procedures()
        
        if not procedures:
            return "No procedures (subroutines or functions) found in the file to analyze."
            
        report = ["# Candidate PURE Procedures Analysis Report\n"]
        
        for proc in procedures:
            proc_name = proc["name"]
            proc_type = proc["type"]
            start_line = proc["start"]
            end_line = proc["end"]
            
            # Check if already pure
            start_line_text = linter.lines[start_line - 1].lower()
            if "pure" in start_line_text or "elemental" in start_line_text:
                report.append(f"### Procedure '{proc_name}' (Line {start_line})")
                report.append(f"*   Status: Already declared as `{ 'pure' if 'pure' in start_line_text else 'elemental' }`.\n")
                continue
                
            violations = []
            
            # Check for I/O statements in procedure lines
            io_write_rx = re.compile(r'\bwrite\s*\(\s*(?:\*|[0-9]+)\b', re.IGNORECASE)
            io_print_rx = re.compile(r'\bprint\s*\*|\bprint\s+[0-9]+\b', re.IGNORECASE)
            io_read_rx = re.compile(r'\bread\s*\(\s*(?:\*|[0-9]+)\b', re.IGNORECASE)
            io_open_rx = re.compile(r'\bopen\s*\(', re.IGNORECASE)
            io_close_rx = re.compile(r'\bclose\s*\(', re.IGNORECASE)
            io_stop_rx = re.compile(r'^\s*stop\b', re.IGNORECASE)  # Standard stop is illegal in pure
            
            # Gather local variables declarations
            local_vars = set()
            intent_out_inout_args = set()
            intent_in_args = set()
            all_args = [a.lower() for a in proc["args"] if a != '*']
            
            # Extract declarations inside procedure scope to map local variables
            arg_intents = {}
            
            for line_no in range(start_line, end_line):
                line = linter._clean_line(linter.lines[line_no - 1])
                if not line:
                    continue
                
                # Check for I/O
                if io_print_rx.search(line):
                    violations.append(f"Line {line_no}: Contains PRINT statement.")
                if io_write_rx.search(line):
                    violations.append(f"Line {line_no}: Contains WRITE statement to external unit.")
                if io_read_rx.search(line):
                    violations.append(f"Line {line_no}: Contains READ statement.")
                if io_open_rx.search(line):
                    violations.append(f"Line {line_no}: Contains OPEN file operation.")
                if io_close_rx.search(line):
                    violations.append(f"Line {line_no}: Contains CLOSE file operation.")
                if io_stop_rx.match(line):
                    violations.append(f"Line {line_no}: Contains STOP statement (illegal in PURE procedures).")
                    
                # Parse variable declarations to find local variables
                decl_match = re.match(
                    r'^\s*(?:real|integer|logical|character|complex|type\s*\(\s*\w+\s*\))\b',
                    line, re.IGNORECASE
                )
                if decl_match:
                    parts = line.split('::')
                    vars_part = parts[1] if len(parts) > 1 else line
                    declared_names = re.findall(r'\b[a-zA-Z_]\w*\b', vars_part)
                    
                    intent_match = re.search(r'\bintent\s*\(\s*(in|out|inout)\s*\)', line, re.IGNORECASE)
                    if intent_match:
                        intent_val = intent_match.group(1).lower()
                        for v in declared_names:
                            arg_intents[v.lower()] = intent_val
                            if intent_val in ['out', 'inout']:
                                intent_out_inout_args.add(v.lower())
                            else:
                                intent_in_args.add(v.lower())
                    else:
                        for v in declared_names:
                            if v.lower() not in all_args:
                                local_vars.add(v.lower())
                                
            # Check dummy argument intents
            for arg in all_args:
                arg_lower = arg.lower()
                if arg_lower not in arg_intents:
                    violations.append(f"Dummy argument '{arg}' lacks an explicit INTENT attribute.")
                elif proc_type == "function" and arg_intents[arg_lower] != "in":
                    violations.append(f"Function dummy argument '{arg}' has intent({arg_intents[arg_lower]}). In PURE functions, all arguments must be INTENT(IN).")
                    
            # Check for global variable modifications (assignments)
            assign_rx = re.compile(r'^\s*([a-zA-Z_]\w*)(?:\s*\([^)]*\))?\s*=', re.IGNORECASE)
            pointer_assign_rx = re.compile(r'^\s*([a-zA-Z_]\w*)\s*=>', re.IGNORECASE)
            
            for line_no in range(start_line, end_line):
                line = linter._clean_line(linter.lines[line_no - 1])
                if not line:
                    continue
                    
                assigned_var = None
                m1 = assign_rx.match(line)
                if m1:
                    assigned_var = m1.group(1).lower()
                else:
                    m2 = pointer_assign_rx.match(line)
                    if m2:
                        assigned_var = m2.group(1).lower()
                        
                if assigned_var:
                    is_allowed = (
                        assigned_var in local_vars or
                        assigned_var in intent_out_inout_args or
                        assigned_var == proc_name.lower() or
                        assigned_var in all_args
                    )
                    
                    if assigned_var in intent_in_args:
                        violations.append(f"Line {line_no}: Modification of INTENT(IN) argument '{assigned_var}'.")
                    elif not is_allowed and assigned_var not in ['stat', 'errmsg']:
                        violations.append(f"Line {line_no}: Modifies variable '{assigned_var}' which is not declared locally (potential global state write).")
                        
            report.append(f"### Procedure '{proc_name}' ({proc_type.capitalize()}, Line {start_line})")
            if violations:
                report.append("*   Status: **Not PURE-compliant**")
                report.append("*   Violations found:")
                for v in violations:
                    report.append(f"    *   {v}")
            else:
                report.append("*   Status: **✅ PURE Candidate!**")
                report.append("*   Recommendation: This procedure does not contain side effects or illegal I/O operations. Add the `pure` attribute to the procedure signature to enable loop parallelization and compiler optimizations.")
                report.append("*   Refactoring Example:")
                report.append(f"    ```fortran\n    pure {proc_type} {proc_name}(...)\n    ```")
            report.append("")
            
        return "\n".join(report)
    except Exception as e:
        return f"Error during PURE procedure analysis: {str(e)}"

@mcp.tool()
def audit_implicit_interfaces(project_path: str) -> str:
    """Audits the project and lists all subroutine/function calls lacking an explicit interface.
    Prevents runtime memory crashes and type mismatches.
    """
    if not os.path.exists(project_path):
        return f"Error: Project path does not exist: {project_path}"
        
    try:
        source_files = []
        for root, dirs, files in os.walk(project_path):
            if ".venv" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith(('.f90', '.f', '.for', '.f95', '.f03', '.f08', '.fpp', '.F90')):
                    source_files.append(os.path.join(root, f))
                    
        if not source_files:
            return f"No Fortran source files found in project path: {project_path}"
            
        module_procedures = {}
        external_procedures = {}
        file_scoping_units = {}
        
        for filepath in source_files:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            linter = FortranLinter(content)
            units = linter.find_scoping_units()
            file_scoping_units[filepath] = units
            
            procedures = linter.find_procedures()
            for proc in procedures:
                name_lower = proc["name"].lower()
                in_module = None
                for u in units:
                    if u["type"] == "module" and u["start"] <= proc["start"] <= u["end"]:
                        in_module = u["name"]
                        break
                if in_module:
                    module_procedures[name_lower] = in_module
                else:
                    external_procedures[name_lower] = filepath
                    
        violations = []
        call_rx = re.compile(r'\bcall\s+([a-zA-Z_]\w*)', re.IGNORECASE)
        
        for filepath in source_files:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
                
            linter = FortranLinter("\n".join(lines))
            units = file_scoping_units.get(filepath, [])
            for line_no, line in enumerate(lines):
                clean_line = linter._clean_line(line)
                if not clean_line:
                    continue
                if line and line[0].lower() in ['c', '*']:
                    continue
                    
                call_match = call_rx.search(clean_line)
                if call_match:
                    called_proc = call_match.group(1).lower()
                    
                    current_unit = None
                    for u in units:
                        if u["start"] <= line_no + 1 <= u["end"]:
                            current_unit = u
                            break
                            
                    if not current_unit:
                        continue
                        
                    uses_module = set()
                    has_explicit_interface = False
                    
                    unit_start = current_unit["start"]
                    for idx in range(unit_start, line_no + 1):
                        chk_line = linter._clean_line(lines[idx - 1])
                        use_match = re.match(r'^\s*use\s+([a-zA-Z_]\w*)', chk_line, re.IGNORECASE)
                        if use_match:
                            uses_module.add(use_match.group(1).lower())
                            
                        if re.match(r'^\s*interface\b', chk_line, re.IGNORECASE):
                            k = idx
                            while k < len(lines):
                                inner_line = linter._clean_line(lines[k])
                                if re.match(r'^\s*end\s*interface\b', inner_line, re.IGNORECASE):
                                    break
                                if re.search(r'\b(?:subroutine|function)\s+' + re.escape(called_proc) + r'\b', inner_line, re.IGNORECASE):
                                    has_explicit_interface = True
                                    break
                                k += 1
                                
                    is_module_imported = False
                    if called_proc in module_procedures:
                        defining_module = module_procedures[called_proc].lower()
                        if defining_module in uses_module:
                            is_module_imported = True
                            
                    is_local = False
                    for proc in linter.find_procedures():
                        if proc["name"].lower() == called_proc:
                            if current_unit["start"] <= proc["start"] <= current_unit["end"]:
                                is_local = True
                                break
                                
                    if not is_module_imported and not is_local and not has_explicit_interface:
                        defined_location = "external or undefined"
                        if called_proc in external_procedures:
                            defined_location = f"defined as external in {os.path.basename(external_procedures[called_proc])}"
                        elif called_proc in module_procedures:
                            defined_location = f"defined in module '{module_procedures[called_proc]}', but module is not used"
                            
                        violations.append({
                            "file": os.path.basename(filepath),
                            "line": line_no + 1,
                            "proc": called_proc,
                            "unit": current_unit["name"],
                            "location": defined_location,
                            "code": line.strip()
                        })
                        
        if not violations:
            return "✅ Implicit Interface Audit PASSED: All subroutine calls in the project have explicit interfaces!"
            
        report = ["# Implicit Interface Safety Audit Report\n",
                  f"Found {len(violations)} call site(s) with implicit interfaces. Calling subroutines without explicit interfaces bypasses compiler argument checks and causes runtime stack errors.\n",
                  "| File | Line | Scoping Unit | Called Procedure | Status / Target Module |",
                  "| :--- | :--- | :--- | :--- | :--- |"]
                  
        for v in violations:
            report.append(f"| {v['file']} | {v['line']} | {v['unit']} | `{v['proc']}` | {v['location']} |")
            
        report.append("\n### Recommendations for Refactoring:")
        report.append("1.  **Encapsulate Procedures in Modules**: Place the called procedures inside a `module` block and reference them with a `use` statement in the calling scope. This is the recommended modern Fortran standard.")
        report.append("2.  **Add Interface Blocks**: If you must call external procedures (e.g. legacy binaries or C libraries), declare a local `interface` block in the calling scope to specify parameter shapes and intents.")
        
        return "\n".join(report)
    except Exception as e:
        return f"Error auditing implicit interfaces: {str(e)}"

@mcp.tool()
def scaffold_unit_test(file_path: str, procedure_name: str, framework: str = "standard") -> str:
    """Generates unit testing templates for a specific module procedure.
    Inspects dummy arguments, intents, and shapes, and registers the test target.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        linter = FortranLinter(code)
        procedures = linter.find_procedures()
        
        target_proc = None
        for proc in procedures:
            if proc["name"].lower() == procedure_name.lower():
                target_proc = proc
                break
                
        if not target_proc:
            return f"Error: Could not locate procedure '{procedure_name}' in '{file_path}'."
            
        # Find containing module
        units = linter.find_scoping_units()
        module_name = None
        for u in units:
            if u["type"] == "module" and u["start"] <= target_proc["start"] <= u["end"]:
                module_name = u["name"]
                break
                
        if not module_name:
            return f"Error: Procedure '{procedure_name}' must be defined inside a module to scaffold unit tests."
            
        # Parse arguments and intents
        start_line = target_proc["start"]
        end_line = target_proc["end"]
        all_args = [a.lower() for a in target_proc["args"] if a != '*']
        
        arg_declarations = []
        arg_types = {}
        arg_dimensions = {}
        arg_intents = {}
        
        for line_no in range(start_line, end_line):
            line = linter._clean_line(linter.lines[line_no - 1])
            if not line:
                continue
                
            decl_match = re.match(
                r'^\s*(real|integer|logical|character|complex|type\s*\(\s*\w+\s*\))\b',
                line, re.IGNORECASE
            )
            if decl_match:
                parts = line.split('::')
                attr_part = parts[0]
                vars_part = parts[1] if len(parts) > 1 else line
                declared_names = re.findall(r'\b[a-zA-Z_]\w*\b', vars_part)
                
                # Extract dimensions (e.g. x(10) or x(:))
                for v in declared_names:
                    v_lower = v.lower()
                    if v_lower in all_args:
                        # Extract full variable decl with potential array shapes from vars_part
                        var_decl_match = re.search(r'\b' + re.escape(v) + r'\s*\(([^)]+)\)', vars_part, re.IGNORECASE)
                        if var_decl_match:
                            arg_dimensions[v_lower] = var_decl_match.group(1).strip()
                        elif re.search(r'\bdimension\s*\(([^)]+)\)', attr_part, re.IGNORECASE):
                            dim_match = re.search(r'\bdimension\s*\(([^)]+)\)', attr_part, re.IGNORECASE)
                            arg_dimensions[v_lower] = dim_match.group(1).strip()
                            
                        # Store type
                        type_name = decl_match.group(1).lower()
                        # Capture kind if any
                        kind_match = re.search(r'(real|integer)\s*\(([^)]+)\)', attr_part, re.IGNORECASE)
                        if kind_match:
                            type_name = f"{kind_match.group(1)}({kind_match.group(2)})"
                        elif "double precision" in attr_part.lower():
                            type_name = "real(kind=dp)"
                        elif "real*8" in attr_part.lower():
                            type_name = "real(kind=dp)"
                        elif "integer*4" in attr_part.lower():
                            type_name = "integer(kind=int32)"
                        arg_types[v_lower] = type_name
                        
                        # Store intent
                        intent_match = re.search(r'\bintent\s*\(\s*(in|out|inout)\s*\)', attr_part, re.IGNORECASE)
                        if intent_match:
                            arg_intents[v_lower] = intent_match.group(1).lower()
                        else:
                            arg_intents[v_lower] = "inout"
                            
        # Scaffold the test code
        test_vars_decl = []
        test_vars_init = []
        call_args = []
        
        # Add kind parameter helper if dp is used
        has_dp = any("dp" in t for t in arg_types.values())
        
        for arg in target_proc["args"]:
            if arg == '*':
                call_args.append('*')
                continue
            arg_lower = arg.lower()
            atype = arg_types.get(arg_lower, "real(kind=dp)" if has_dp else "real")
            dims = arg_dimensions.get(arg_lower, None)
            intent = arg_intents.get(arg_lower, "inout")
            
            decl_str = f"  {atype}"
            if dims:
                test_dims = dims.replace(":", "10").replace("*", "10")
                decl_str += f", allocatable :: {arg_lower}(:)"
                test_vars_init.append(f"  allocate({arg_lower}(10))")
                if "integer" in atype:
                    test_vars_init.append(f"  {arg_lower} = 1")
                elif "logical" in atype:
                    test_vars_init.append(f"  {arg_lower} = .true.")
                else:
                    test_vars_init.append(f"  {arg_lower} = 1.0_dp" if "dp" in atype else f"  {arg_lower} = 1.0")
            else:
                decl_str += f" :: {arg_lower}"
                if "integer" in atype:
                    test_vars_init.append(f"  {arg_lower} = 1")
                elif "logical" in atype:
                    test_vars_init.append(f"  {arg_lower} = .true.")
                else:
                    test_vars_init.append(f"  {arg_lower} = 1.0_dp" if "dp" in atype else f"  {arg_lower} = 1.0")
                    
            test_vars_decl.append(decl_str)
            call_args.append(arg_lower)
            
        # Write test template
        proj_dir = os.path.dirname(file_path)
        test_dir = os.path.join(proj_dir, "test")
        if not os.path.exists(test_dir):
            test_dir = os.path.join(os.path.dirname(proj_dir), "test")
            if not os.path.exists(test_dir):
                test_dir = proj_dir
                
        test_file_path = os.path.join(test_dir, f"test_{procedure_name}.f90")
        
        test_code = [
            f"program test_{procedure_name}",
            f"  use {module_name}, only : {procedure_name}",
            "  use, intrinsic :: iso_fortran_env, only : dp => real64, int32" if has_dp else "  implicit none",
            "  implicit none" if has_dp else "",
            ""
        ]
        test_code.extend(test_vars_decl)
        test_code.append("")
        test_code.extend(test_vars_init)
        test_code.append("")
        test_code.append(f"  print *, 'Running unit test for {procedure_name}... '")
        test_code.append(f"  call {procedure_name}({', '.join(call_args)})")
        test_code.append("  print *, 'Test execution complete. Asserting post-conditions...'")
        test_code.append("  ! TODO: Add assertions here (e.g. if (output /= expected) call exit(1))")
        test_code.append("  print *, 'Unit test PASSED'")
        test_code.append(f"end program test_{procedure_name}\n")
        
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(test_code))
            
        fprettify_bin = get_fprettify_path()
        if fprettify_bin:
            subprocess.run([fprettify_bin, test_file_path], capture_output=True)
            
        # Register in Makefile if present
        reg_msg = ""
        makefile_path = os.path.join(proj_dir, "Makefile")
        if not os.path.exists(makefile_path):
            makefile_path = os.path.join(os.path.dirname(proj_dir), "Makefile")
            
        if os.path.exists(makefile_path):
            try:
                with open(makefile_path, "r") as mf:
                    mf_content = mf.read()
                target_str = f"test_{procedure_name}"
                if target_str not in mf_content:
                    rule = f"\n\n{target_str}:\n\t$(FC) $(FFLAGS) {os.path.relpath(test_file_path, os.path.dirname(makefile_path))} -o bin/{target_str}\n\t./bin/{target_str}\n"
                    with open(makefile_path, "a") as mf:
                        mf.write(rule)
                    reg_msg = f" Registered target '{target_str}' in Makefile."
            except Exception:
                pass
                
        return f"Success: Unit test scaffolded at '{test_file_path}'.{reg_msg}"
    except Exception as e:
        return f"Error during unit test scaffolding: {str(e)}"

@mcp.tool()
def scaffold_hpc_grid(project_path: str, grid_name: str, dimensions: int) -> str:
    """Bootstraps a modern HPC template for grid/stencil calculations using Coarrays or OpenMP.
    Sets up stencil iteration loops and ghost cell exchange wrappers.
    """
    if not os.path.exists(project_path):
        return f"Error: Project path does not exist: {project_path}"
        
    try:
        src_dir = os.path.join(project_path, "src")
        if not os.path.exists(src_dir):
            src_dir = project_path
            
        grid_file_path = os.path.join(src_dir, f"{grid_name}_grid.f90")
        
        dims_decl = "nx, ny" if dimensions <= 2 else "nx, ny, nz"
        array_shape = "(:,:)" if dimensions <= 2 else "(:,:,:)"
        alloc_shape = "this%nx, this%ny" if dimensions <= 2 else "this%nx, this%ny, this%nz"
        
        loops = []
        if dimensions == 2:
            loops = [
                "    !$omp parallel do private(i, j) shared(this)",
                "    do j = 2, this%ny - 1",
                "       do i = 2, this%nx - 1",
                "          ! 5-point Laplacian stencil example",
                "          next_grid(i,j) = 0.25_dp * (this%u(i+1,j) + this%u(i-1,j) + &",
                "                                      this%u(i,j+1) + this%u(i,j-1))",
                "       end do",
                "    end do",
                "    !$omp end parallel do"
            ]
        else:
            loops = [
                "    !$omp parallel do collapse(2) private(i, j, k) shared(this)",
                "    do k = 2, this%nz - 1",
                "       do j = 2, this%ny - 1",
                "          do i = 2, this%nx - 1",
                "             ! 7-point 3D stencil Laplacian",
                "             next_grid(i,j,k) = (this%u(i+1,j,k) + this%u(i-1,j,k) + &",
                "                                 this%u(i,j+1,k) + this%u(i,j-1,k) + &",
                "                                 this%u(i,j,k+1) + this%u(i,j,k-1)) / 6.0_dp",
                "          end do",
                "       end do",
                "    end do",
                "    !$omp end parallel do"
            ]
            
        code = [
            f"module {grid_name}_grid_mod",
            "  use, intrinsic :: iso_fortran_env, only : dp => real64",
            "  implicit none",
            "  private",
            f"  public :: {grid_name}_grid_t",
            "",
            f"  type :: {grid_name}_grid_t",
            "    integer :: nx, ny" if dimensions <= 2 else "    integer :: nx, ny, nz",
            f"    real(dp), allocatable :: u{array_shape}",
            "  contains",
            "    procedure :: allocate_grid",
            "    procedure :: swap_ghost_cells",
            "    procedure :: execute_stencil",
            f"  end type {grid_name}_grid_t",
            "",
            "contains",
            "",
            f"  subroutine allocate_grid(this, {dims_decl})",
            f"    class({grid_name}_grid_t), intent(inout) :: this",
            f"    integer, intent(in) :: {dims_decl}",
            "    integer :: stat",
            "    character(len=100) :: msg",
            "",
            "    this%nx = nx",
            "    this%ny = ny",
            "    this%nz = nz" if dimensions > 2 else "",
            "",
            f"    allocate(this%u({alloc_shape}), stat=stat, errmsg=msg)",
            "    if (stat /= 0) then",
            "       print *, 'Grid allocation failed: ', trim(msg)",
            "       error stop",
            "    end if",
            "    this%u = 0.0_dp",
            "  end subroutine allocate_grid",
            "",
            f"  subroutine swap_ghost_cells(this)",
            f"    class({grid_name}_grid_t), intent(inout) :: this",
            "    ! TODO: Implement parallel ghost cell exchange boundary swap here.",
            "    ! If using Coarrays: swap boundary elements between images.",
            "    ! If using MPI: call MPI_Sendrecv swap routines.",
            "    print *, 'Ghost cell boundary swap executed.'",
            "  end subroutine swap_ghost_cells",
            "",
            f"  subroutine execute_stencil(this, next_grid)",
            f"    class({grid_name}_grid_t), intent(in) :: this",
            f"    real(dp), intent(inout) :: next_grid{array_shape}",
            "    integer :: i, j" if dimensions <= 2 else "    integer :: i, j, k",
            "",
            "    ! Assert grid shapes match",
            "    if (any(shape(this%u) /= shape(next_grid))) then",
            "       print *, 'Error: Grid dimensions mismatch in execute_stencil!'",
            "       error stop",
            "    end if",
            ""
        ]
        code.extend(loops)
        code.append("  end subroutine execute_stencil")
        code.append(f"end module {grid_name}_grid_mod\n")
        
        with open(grid_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(code))
            
        fprettify_bin = get_fprettify_path()
        if fprettify_bin:
            subprocess.run([fprettify_bin, grid_file_path], capture_output=True)
            
        return f"Success: HPC parallel grid template bootstrapped at '{grid_file_path}' ({dimensions}D stencil, OpenMP parallel structures)."
    except Exception as e:
        return f"Error bootstrapping HPC grid: {str(e)}"

def map_fortran_type_to_c(fortran_type: str) -> str:
    t = re.sub(r'\s+', '', fortran_type.lower())
    if 'doubleprecision' in t or 'real(kind=dp)' in t or 'real(dp)' in t or 'real64' in t or 'real*8' in t:
        return 'real(c_double)'
    elif 'real(kind=4)' in t or 'real*4' in t or 'real32' in t:
        return 'real(c_float)'
    elif 'real' in t:
        return 'real(c_double)' # safer default for Python float
    elif 'integer(kind=8)' in t or 'integer*8' in t or 'int64' in t:
        return 'integer(c_long_long)'
    elif 'integer' in t:
        return 'integer(c_int)'
    elif 'logical' in t:
        return 'logical(c_bool)'
    elif 'character' in t:
        return 'character(kind=c_char)'
    else:
        return fortran_type

def map_c_type_to_ctypes(c_type: str) -> str:
    c_type = c_type.lower()
    if 'c_double' in c_type:
        return 'ctypes.c_double'
    elif 'c_float' in c_type:
        return 'ctypes.c_float'
    elif 'c_int' in c_type:
        return 'ctypes.c_int'
    elif 'c_long_long' in c_type:
        return 'ctypes.c_longlong'
    elif 'c_bool' in c_type:
        return 'ctypes.c_bool'
    elif 'c_char' in c_type:
        return 'ctypes.c_char'
    else:
        return 'ctypes.c_double'

def map_c_type_to_numpy(c_type: str) -> str:
    c_type = c_type.lower()
    if 'c_double' in c_type:
        return 'np.float64'
    elif 'c_float' in c_type:
        return 'np.float32'
    elif 'c_int' in c_type:
        return 'np.int32'
    elif 'c_long_long' in c_type:
        return 'np.int64'
    elif 'c_bool' in c_type:
        return 'np.bool_'
    elif 'c_char' in c_type:
        return 'np.char'
    else:
        return 'np.float64'

@mcp.tool()
def generate_c_bindings(file_path: str, module_name: str) -> str:
    """Auto-generates a standard C binding layer module for a modern Fortran module.
    Maps Fortran types to C-compatible types using iso_c_binding, and generates bind(c) wrapper interfaces.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        linter = FortranLinter(code)
        procedures = linter.find_procedures()
        units = linter.find_scoping_units()
        
        target_mod = None
        for u in units:
            if u["type"] == "module" and u["name"].lower() == module_name.lower():
                target_mod = u
                break
                
        if not target_mod:
            return f"Error: Module '{module_name}' not found in '{file_path}'"
            
        # Parse module level public/private
        mod_lines = linter.lines[target_mod["start"] - 1 : target_mod["end"]]
        default_public = True
        public_procedures = set()
        private_procedures = set()
        
        for line in mod_lines:
            clean = linter._clean_line(line)
            if not clean:
                continue
            clean_lower = clean.lower().strip()
            if clean_lower == "private":
                default_public = False
            elif clean_lower.startswith("private::") or clean_lower.startswith("private ::"):
                names_part = clean_lower.split("::")[1]
                names = [n.strip() for n in names_part.split(",")]
                private_procedures.update(names)
            elif clean_lower.startswith("public::") or clean_lower.startswith("public ::"):
                names_part = clean_lower.split("::")[1]
                names = [n.strip() for n in names_part.split(",")]
                public_procedures.update(names)
                
        mod_procedures = []
        for proc in procedures:
            if target_mod["start"] <= proc["start"] <= target_mod["end"]:
                name_lower = proc["name"].lower()
                is_pub = default_public
                if name_lower in public_procedures:
                    is_pub = True
                if name_lower in private_procedures:
                    is_pub = False
                if is_pub:
                    mod_procedures.append(proc)
                    
        if not mod_procedures:
            return f"No public procedures found in module '{module_name}'."
            
        # Generate wrapper code
        wrapper_code = []
        wrapper_code.append(f"module {module_name}_c_mod")
        wrapper_code.append("  use, intrinsic :: iso_c_binding")
        wrapper_code.append("  implicit none")
        wrapper_code.append("contains")
        wrapper_code.append("")
        
        for proc in mod_procedures:
            proc_name = proc["name"]
            proc_type = proc["type"]
            args = [a.lower() for a in proc["args"] if a != '*']
            
            # Parse arguments
            start_line = proc["start"]
            end_line = proc["end"]
            
            arg_types = {}
            arg_dimensions = {}
            arg_intents = {}
            
            result_name = proc_name.lower()
            start_line_text = linter.lines[start_line - 1].lower()
            res_match = re.search(r'\bresult\s*\(\s*([a-zA-Z_]\w*)\s*\)', start_line_text, re.IGNORECASE)
            if res_match:
                result_name = res_match.group(1).lower()
                
            func_type = None
            type_prefix_match = re.match(
                r'^\s*(real|integer|logical|character|complex|double\s+precision|type\s*\(\s*\w+\s*\))\b',
                start_line_text, re.IGNORECASE
            )
            if type_prefix_match:
                func_type = type_prefix_match.group(1).strip()
                if "double precision" in func_type or "doubleprecision" in func_type:
                    func_type = "real(kind=dp)"
                elif "real*8" in func_type:
                    func_type = "real(kind=dp)"
                elif "integer*4" in func_type:
                    func_type = "integer(kind=int32)"
            
            for line_no in range(start_line, end_line):
                line = linter._clean_line(linter.lines[line_no - 1])
                if not line:
                    continue
                    
                decl_match = re.match(
                    r'^\s*(real|integer|logical|character|complex|double\s+precision|type\s*\(\s*\w+\s*\))\b',
                    line, re.IGNORECASE
                )
                if decl_match:
                    parts = line.split('::')
                    attr_part = parts[0]
                    vars_part = parts[1] if len(parts) > 1 else line
                    declared_names = re.findall(r'\b[a-zA-Z_]\w*\b', vars_part)
                    
                    for v in declared_names:
                        v_lower = v.lower()
                        
                        var_dim = None
                        var_decl_match = re.search(r'\b' + re.escape(v) + r'\s*\(([^)]+)\)', vars_part, re.IGNORECASE)
                        if var_decl_match:
                            var_dim = var_decl_match.group(1).strip()
                        elif re.search(r'\bdimension\s*\(([^)]+)\)', attr_part, re.IGNORECASE):
                            dim_match = re.search(r'\bdimension\s*\(([^)]+)\)', attr_part, re.IGNORECASE)
                            var_dim = dim_match.group(1).strip()
                            
                        type_name = decl_match.group(1).lower()
                        kind_match = re.search(r'(real|integer)\s*\(([^)]+)\)', attr_part, re.IGNORECASE)
                        if kind_match:
                            type_name = f"{kind_match.group(1)}({kind_match.group(2)})"
                        elif "double precision" in attr_part.lower():
                            type_name = "real(kind=dp)"
                        elif "real*8" in attr_part.lower():
                            type_name = "real(kind=dp)"
                        elif "integer*4" in attr_part.lower():
                            type_name = "integer(kind=int32)"
                            
                        intent_match = re.search(r'\bintent\s*\(\s*(in|out|inout)\s*\)', attr_part, re.IGNORECASE)
                        intent = intent_match.group(1).lower() if intent_match else "inout"
                        
                        if v_lower in args:
                            arg_types[v_lower] = type_name
                            arg_intents[v_lower] = intent
                            if var_dim:
                                arg_dimensions[v_lower] = var_dim
                        elif v_lower == result_name and proc_type == "function":
                            func_type = type_name

            # Build bindings signature & body
            size_args_decls = []
            size_args_names = []
            
            # Map types and dimensions
            mapped_types = {}
            mapped_dims = {}
            call_slices = {}
            
            for arg in args:
                atype = arg_types.get(arg, "real")
                c_type = map_fortran_type_to_c(atype)
                mapped_types[arg] = c_type
                
                dims = arg_dimensions.get(arg)
                if dims:
                    dim_parts = [p.strip() for p in dims.split(',')]
                    new_dims = []
                    slices = []
                    
                    for idx, part in enumerate(dim_parts):
                        if part in (':', '*'):
                            # Need size variable
                            size_var = f"{arg}_size_{idx+1}"
                            size_args_names.append(size_var)
                            size_args_decls.append(f"    integer(c_int), value :: {size_var}")
                            new_dims.append(size_var)
                            slices.append(f"1:{size_var}")
                        else:
                            new_dims.append(part)
                            slices.append(f"1:{part}")
                            
                    mapped_dims[arg] = f"({', '.join(new_dims)})"
                    call_slices[arg] = f"{arg}({', '.join(slices)})"
                else:
                    mapped_dims[arg] = ""
                    call_slices[arg] = arg
            
            # Signature args: original args + size args
            sig_args = args + size_args_names
            
            # Generate the binder subroutine or function
            c_name = f"c_{proc_name.lower()}"
            bind_clause = f'bind(c, name="{proc_name.lower()}")'
            
            if proc_type == "subroutine":
                wrapper_code.append(f"  subroutine {c_name}({', '.join(sig_args)}) {bind_clause}")
                wrapper_code.append(f"    use {module_name}, only : {proc_name}")
                # Declarations
                for arg in args:
                    c_type = mapped_types[arg]
                    dim_str = mapped_dims[arg]
                    intent = arg_intents.get(arg, "inout")
                    if dim_str:
                        wrapper_code.append(f"    {c_type}, intent({intent}) :: {arg}{dim_str}")
                    else:
                        wrapper_code.append(f"    {c_type}, intent({intent}) :: {arg}")
                for s_decl in size_args_decls:
                    wrapper_code.append(s_decl)
                
                # Body call
                call_args = [call_slices[arg] for arg in args]
                wrapper_code.append(f"    call {proc_name}({', '.join(call_args)})")
                wrapper_code.append(f"  end subroutine {c_name}")
                wrapper_code.append("")
            else: # function
                c_func_type = map_fortran_type_to_c(func_type or "real")
                wrapper_code.append(f"  function {c_name}({', '.join(sig_args)}) {bind_clause} result(res)")
                wrapper_code.append(f"    use {module_name}, only : {proc_name}")
                wrapper_code.append(f"    {c_func_type} :: res")
                # Declarations
                for arg in args:
                    c_type = mapped_types[arg]
                    dim_str = mapped_dims[arg]
                    intent = arg_intents.get(arg, "inout")
                    if dim_str:
                        wrapper_code.append(f"    {c_type}, intent({intent}) :: {arg}{dim_str}")
                    else:
                        wrapper_code.append(f"    {c_type}, intent({intent}) :: {arg}")
                for s_decl in size_args_decls:
                    wrapper_code.append(s_decl)
                
                # Body call
                call_args = [call_slices[arg] for arg in args]
                wrapper_code.append(f"    res = {proc_name}({', '.join(call_args)})")
                wrapper_code.append(f"  end function {c_name}")
                wrapper_code.append("")
                
        wrapper_code.append(f"end module {module_name}_c_mod\n")
        
        # Write output file
        c_mod_file_path = os.path.join(os.path.dirname(file_path), f"{module_name}_c_mod.f90")
        with open(c_mod_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(wrapper_code))
            
        fprettify_bin = get_fprettify_path()
        if fprettify_bin:
            subprocess.run([fprettify_bin, c_mod_file_path], capture_output=True)
            
        return f"Success: C binding wrapper module generated at '{c_mod_file_path}'"
    except Exception as e:
        return f"Error generating C bindings: {str(e)}"

@mcp.tool()
def generate_python_interface(file_path: str, module_name: str) -> str:
    """Auto-generates ctypes/numpy binding wrapper scripts for Python integration.
    Also calls generate_c_bindings first to ensure the C-binding Fortran code is present.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    try:
        # 1. Run generate_c_bindings
        bind_res = generate_c_bindings(file_path, module_name)
        if bind_res.startswith("Error"):
            return f"Error in generate_c_bindings dependency: {bind_res}"
            
        # Re-parse module and procedures to build Python wrappers
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        linter = FortranLinter(code)
        procedures = linter.find_procedures()
        units = linter.find_scoping_units()
        
        target_mod = None
        for u in units:
            if u["type"] == "module" and u["name"].lower() == module_name.lower():
                target_mod = u
                break
                
        if not target_mod:
            return f"Error: Module '{module_name}' not found"
            
        # Parse module level public/private
        mod_lines = linter.lines[target_mod["start"] - 1 : target_mod["end"]]
        default_public = True
        public_procedures = set()
        private_procedures = set()
        
        for line in mod_lines:
            clean = linter._clean_line(line)
            if not clean:
                continue
            clean_lower = clean.lower().strip()
            if clean_lower == "private":
                default_public = False
            elif clean_lower.startswith("private::") or clean_lower.startswith("private ::"):
                names_part = clean_lower.split("::")[1]
                names = [n.strip() for n in names_part.split(",")]
                private_procedures.update(names)
            elif clean_lower.startswith("public::") or clean_lower.startswith("public ::"):
                names_part = clean_lower.split("::")[1]
                names = [n.strip() for n in names_part.split(",")]
                public_procedures.update(names)
                
        mod_procedures = []
        for proc in procedures:
            if target_mod["start"] <= proc["start"] <= target_mod["end"]:
                name_lower = proc["name"].lower()
                is_pub = default_public
                if name_lower in public_procedures:
                    is_pub = True
                if name_lower in private_procedures:
                    is_pub = False
                if is_pub:
                    mod_procedures.append(proc)
                    
        # Scaffold Python wrapper
        py_code = []
        py_code.append(f"# Auto-generated Python wrapper for Fortran module: {module_name}")
        py_code.append("# Generated by Fortran Companion MCP Server")
        py_code.append("")
        py_code.append("import os")
        py_code.append("import sys")
        py_code.append("import ctypes")
        py_code.append("import numpy as np")
        py_code.append("")
        py_code.append("_lib = None")
        py_code.append("_lib_path = None")
        py_code.append("")
        py_code.append("def load_library(path=None):")
        py_code.append("    global _lib, _lib_path")
        py_code.append("    if path is not None:")
        py_code.append("        _lib = ctypes.CDLL(path)")
        py_code.append("        _lib_path = path")
        py_code.append("        return _lib")
        py_code.append("        ")
        py_code.append("    base_dir = os.path.dirname(os.path.abspath(__file__))")
        py_code.append("    lib_names = []")
        py_code.append("    if sys.platform == 'win32':")
        py_code.append(f"        lib_names = ['{module_name}_c_mod.dll', 'lib{module_name}_c_mod.dll']")
        py_code.append("    elif sys.platform == 'darwin':")
        py_code.append(f"        lib_names = ['lib{module_name}_c_mod.dylib', '{module_name}_c_mod.dylib', 'lib{module_name}_c_mod.so']")
        py_code.append("    else:")
        py_code.append(f"        lib_names = ['lib{module_name}_c_mod.so', '{module_name}_c_mod.so']")
        py_code.append("        ")
        py_code.append("    search_dirs = [base_dir, os.path.join(base_dir, 'build'), os.path.join(base_dir, 'lib'), os.getcwd()]")
        py_code.append("    ")
        py_code.append("    for d in search_dirs:")
        py_code.append("        for name in lib_names:")
        py_code.append("            full_path = os.path.join(d, name)")
        py_code.append("            if os.path.exists(full_path):")
        py_code.append("                try:")
        py_code.append("                    _lib = ctypes.CDLL(full_path)")
        py_code.append("                    _lib_path = full_path")
        py_code.append("                    return _lib")
        py_code.append("                except Exception:")
        py_code.append("                    pass")
        py_code.append("    for name in lib_names:")
        py_code.append("        try:")
        py_code.append("            _lib = ctypes.CDLL(name)")
        py_code.append("            _lib_path = name")
        py_code.append("            return _lib")
        py_code.append("        except Exception:")
        py_code.append("            pass")
        py_code.append(f"    raise ImportError('Could not find or load compiled shared library for {module_name}_c_mod.')")
        py_code.append("")
        
        for proc in mod_procedures:
            proc_name = proc["name"]
            proc_type = proc["type"]
            args = [a.lower() for a in proc["args"] if a != '*']
            
            # Re-parse argument types and dimensions
            start_line = proc["start"]
            end_line = proc["end"]
            
            arg_types = {}
            arg_dimensions = {}
            arg_intents = {}
            
            result_name = proc_name.lower()
            start_line_text = linter.lines[start_line - 1].lower()
            res_match = re.search(r'\bresult\s*\(\s*([a-zA-Z_]\w*)\s*\)', start_line_text, re.IGNORECASE)
            if res_match:
                result_name = res_match.group(1).lower()
                
            func_type = None
            type_prefix_match = re.match(
                r'^\s*(real|integer|logical|character|complex|double\s+precision|type\s*\(\s*\w+\s*\))\b',
                start_line_text, re.IGNORECASE
            )
            if type_prefix_match:
                func_type = type_prefix_match.group(1).strip()
                if "double precision" in func_type or "doubleprecision" in func_type:
                    func_type = "real(kind=dp)"
                elif "real*8" in func_type:
                    func_type = "real(kind=dp)"
                elif "integer*4" in func_type:
                    func_type = "integer(kind=int32)"
                    
            for line_no in range(start_line, end_line):
                line = linter._clean_line(linter.lines[line_no - 1])
                if not line:
                    continue
                decl_match = re.match(
                    r'^\s*(real|integer|logical|character|complex|double\s+precision|type\s*\(\s*\w+\s*\))\b',
                    line, re.IGNORECASE
                )
                if decl_match:
                    parts = line.split('::')
                    attr_part = parts[0]
                    vars_part = parts[1] if len(parts) > 1 else line
                    declared_names = re.findall(r'\b[a-zA-Z_]\w*\b', vars_part)
                    
                    for v in declared_names:
                        v_lower = v.lower()
                        var_dim = None
                        var_decl_match = re.search(r'\b' + re.escape(v) + r'\s*\(([^)]+)\)', vars_part, re.IGNORECASE)
                        if var_decl_match:
                            var_dim = var_decl_match.group(1).strip()
                        elif re.search(r'\bdimension\s*\(([^)]+)\)', attr_part, re.IGNORECASE):
                            dim_match = re.search(r'\bdimension\s*\(([^)]+)\)', attr_part, re.IGNORECASE)
                            var_dim = dim_match.group(1).strip()
                            
                        type_name = decl_match.group(1).lower()
                        kind_match = re.search(r'(real|integer)\s*\(([^)]+)\)', attr_part, re.IGNORECASE)
                        if kind_match:
                            type_name = f"{kind_match.group(1)}({kind_match.group(2)})"
                        elif "double precision" in attr_part.lower():
                            type_name = "real(kind=dp)"
                        elif "real*8" in attr_part.lower():
                            type_name = "real(kind=dp)"
                        elif "integer*4" in attr_part.lower():
                            type_name = "integer(kind=int32)"
                            
                        intent_match = re.search(r'\bintent\s*\(\s*(in|out|inout)\s*\)', attr_part, re.IGNORECASE)
                        intent = intent_match.group(1).lower() if intent_match else "inout"
                        
                        if v_lower in args:
                            arg_types[v_lower] = type_name
                            arg_intents[v_lower] = intent
                            if var_dim:
                                arg_dimensions[v_lower] = var_dim
                        elif v_lower == result_name and proc_type == "function":
                            func_type = type_name

            # Build Python wrapper
            py_func_args = []
            for arg in args:
                if arg in arg_dimensions or arg_intents.get(arg, "inout") in ("in", "inout"):
                    py_func_args.append(arg)
                    
            py_code.append(f"def {proc_name.lower()}({', '.join(py_func_args)}):")
            py_code.append(f"    '''Python wrapper for Fortran procedure {proc_name}'''")
            py_code.append("    global _lib")
            py_code.append("    if _lib is None:")
            py_code.append("        load_library()")
            py_code.append("")
            
            input_conversions = []
            call_params = []
            argtypes_list = []
            size_args_names = []
            size_conversions = []
            
            for arg in args:
                atype = arg_types.get(arg, "real")
                c_type = map_fortran_type_to_c(atype)
                ctypes_t = map_c_type_to_ctypes(c_type)
                np_t = map_c_type_to_numpy(c_type)
                
                intent = arg_intents.get(arg, "inout")
                dims = arg_dimensions.get(arg)
                
                if dims:
                    input_conversions.append(f"    {arg}_arr = np.ascontiguousarray({arg}, dtype={np_t})")
                    call_params.append(f"{arg}_arr.ctypes.data_as(ctypes.POINTER({ctypes_t}))")
                    argtypes_list.append(f"ctypes.POINTER({ctypes_t})")
                    
                    dim_parts = [p.strip() for p in dims.split(',')]
                    for idx, part in enumerate(dim_parts):
                        if part in (':', '*'):
                            size_var = f"{arg}_size_{idx+1}"
                            size_args_names.append(size_var)
                            size_conversions.append(f"    {size_var} = ctypes.c_int({arg}_arr.shape[{idx}])")
                else:
                    if intent in ("in", "inout"):
                        input_conversions.append(f"    {arg}_c = {ctypes_t}({arg})")
                    else:
                        input_conversions.append(f"    {arg}_c = {ctypes_t}()")
                    call_params.append(f"ctypes.byref({arg}_c)")
                    argtypes_list.append(f"ctypes.POINTER({ctypes_t})")
            
            for size_var in size_args_names:
                call_params.append(size_var)
                argtypes_list.append("ctypes.c_int")
                
            restype_str = "None"
            if proc_type == "function":
                f_c_type = map_fortran_type_to_c(func_type or "real")
                restype_str = map_c_type_to_ctypes(f_c_type)
                
            py_code.append(f"    _lib.{proc_name.lower()}.argtypes = [{', '.join(argtypes_list)}]")
            py_code.append(f"    _lib.{proc_name.lower()}.restype = {restype_str}")
            py_code.append("")
            
            py_code.extend(input_conversions)
            py_code.extend(size_conversions)
            py_code.append("")
            
            if proc_type == "function":
                py_code.append(f"    res_val = _lib.{proc_name.lower()}({', '.join(call_params)})")
            else:
                py_code.append(f"    _lib.{proc_name.lower()}({', '.join(call_params)})")
            py_code.append("")
            
            post_call = []
            for arg in args:
                if arg in arg_dimensions and arg_intents.get(arg, "inout") in ("out", "inout"):
                    post_call.append(f"    if isinstance({arg}, np.ndarray) and {arg}_arr is not {arg}:")
                    post_call.append(f"        {arg}[...] = {arg}_arr")
            py_code.extend(post_call)
            
            returns = []
            if proc_type == "function":
                returns.append("res_val")
            for arg in args:
                if arg not in arg_dimensions:
                    intent = arg_intents.get(arg, "inout")
                    if intent in ("out", "inout"):
                        returns.append(f"{arg}_c.value")
                else:
                    returns.append(f"{arg}_arr")
                    
            if len(returns) == 0:
                py_code.append("    return None")
            elif len(returns) == 1:
                py_code.append(f"    return {returns[0]}")
            else:
                py_code.append(f"    return ({', '.join(returns)})")
                
            py_code.append("")
            
        py_file_path = os.path.join(os.path.dirname(file_path), f"{module_name}.py")
        with open(py_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(py_code))
            
        return f"Success: Python interface wrapper generated at '{py_file_path}' (dependency C-binding layer generated at '{os.path.dirname(file_path)}/{module_name}_c_mod.f90')"
    except Exception as e:
        return f"Error generating Python interface: {str(e)}"

@mcp.tool()
def project_metrics(project_path: str) -> str:
    """Computes project-wide quality metrics and generates a 'legacy heatmap'.
    Scans all Fortran files in the project, aggregates lines of code, comment density,
    counts legacy constructs (COMMON, EQUIVALENCE, GOTO, etc.), and assigns a modernization score.
    """
    import os
    import json
    
    if not os.path.isdir(project_path):
        return f"Error: Project path not found or is not a directory: {project_path}"
        
    fortran_extensions = {".f90", ".f", ".f95", ".f03", ".f08", ".for", ".f77", ".ftn"}
    
    files_analyzed = 0
    total_lines = 0
    total_code = 0
    total_comment = 0
    total_empty = 0
    
    # Aggregated legacy counts
    aggregated_rules = {}
    
    # Files details
    per_file_metrics = []
    
    # Exclude typical build/venv directories
    exclude_dirs = {".git", ".venv", "__pycache__", "build", "dist"}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in fortran_extensions:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                    
                    linter = FortranLinter(code)
                    metrics = linter.get_metrics()
                    
                    rel_path = os.path.relpath(file_path, project_path)
                    
                    files_analyzed += 1
                    total_lines += metrics["lines_total"]
                    total_code += metrics["lines_code"]
                    total_comment += metrics["lines_comment"]
                    total_empty += metrics["lines_empty"]
                    
                    for rule, count in metrics["rule_counts"].items():
                        aggregated_rules[rule] = aggregated_rules.get(rule, 0) + count
                        
                    per_file_metrics.append({
                        "file": rel_path,
                        "lines_total": metrics["lines_total"],
                        "lines_code": metrics["lines_code"],
                        "lines_comment": metrics["lines_comment"],
                        "lines_empty": metrics["lines_empty"],
                        "modernization_score": metrics["modernization_score"],
                        "warnings_count": metrics["warnings_count"],
                        "modern_features": metrics["modern_features"]
                    })
                except Exception:
                    pass
                    
    if files_analyzed == 0:
        return "No Fortran files found in the specified project path."
        
    worst_offenders = sorted(per_file_metrics, key=lambda x: x["modernization_score"])[:10]
    god_files = sorted(per_file_metrics, key=lambda x: x["lines_code"], reverse=True)[:10]
    
    avg_score = sum(x["modernization_score"] for x in per_file_metrics) / files_analyzed
    
    summary = {
        "files_analyzed": files_analyzed,
        "total_lines": total_lines,
        "total_code": total_code,
        "total_comment": total_comment,
        "total_empty": total_empty,
        "comment_density_pct": round((total_comment / total_lines * 100.0) if total_lines > 0 else 0.0, 1),
        "average_modernization_score": round(avg_score, 1),
        "aggregated_rule_violations": aggregated_rules,
        "worst_offenders": [
            {"file": x["file"], "score": x["modernization_score"], "code_lines": x["lines_code"]}
            for x in worst_offenders
        ],
        "god_files": [
            {"file": x["file"], "code_lines": x["lines_code"], "total_lines": x["lines_total"]}
            for x in god_files
        ]
    }
    
    result = {
        "summary": summary,
        "per_file": per_file_metrics
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
def dependency_graph(project_path: str) -> str:
    """Computes module dependency graph and detects modules exposing mutable public state.
    Scans all Fortran modules in the project, identifies 'use' statements (excluding standard intrinsics),
    computes fan-in/fan-out metrics, and generates a Mermaid diagram representing the module hierarchy.
    """
    import os
    import re
    import json
    
    if not os.path.isdir(project_path):
        return f"Error: Project path not found or is not a directory: {project_path}"
        
    fortran_extensions = {".f90", ".f", ".f95", ".f03", ".f08", ".for", ".f77", ".ftn"}
    all_modules = {}
    exclude_dirs = {".git", ".venv", "__pycache__", "build", "dist"}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in fortran_extensions:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                        
                    linter = FortranLinter(code)
                    rel_path = os.path.relpath(file_path, project_path)
                    
                    units = linter.find_scoping_units()
                    module_units = [u for u in units if u["type"] == "module"]
                    
                    for u in module_units:
                        mod_name = u["name"]
                        mod_name_lower = mod_name.lower()
                        start_line = u["start"]
                        end_line = u["end"]
                        
                        limit_line = end_line
                        for line_no in range(start_line, end_line):
                            line = linter._clean_line(linter.lines[line_no - 1])
                            if re.match(r'^\s*contains\b', line, re.IGNORECASE):
                                limit_line = line_no
                                break
                                
                        dependencies = set()
                        public_vars = []
                        is_default_private = False
                        explicit_public_vars = set()
                        explicit_private_vars = set()
                        declared_vars = []
                        
                        use_rx = re.compile(r'^\s*use\s*(?:,\s*(?:non_)?intrinsic\s*::)?\s*([a-zA-Z_]\w*)', re.IGNORECASE)
                        intrinsic_modules = {"iso_fortran_env", "iso_c_binding", "ieee_exceptions", "ieee_arithmetic", "ieee_features"}
                        
                        decl_rx = re.compile(r'^\s*(?:real|integer|logical|character|complex|type\s*\(\s*\w+\s*\))\b', re.IGNORECASE)
                        private_stmt_rx = re.compile(r'^\s*private\b', re.IGNORECASE)
                        public_stmt_rx = re.compile(r'^\s*public\b', re.IGNORECASE)
                        
                        for line_no in range(start_line, limit_line):
                            line = linter._clean_line(linter.lines[line_no - 1])
                            if not line:
                                continue
                                
                            use_match = use_rx.match(line)
                            if use_match:
                                dep_name = use_match.group(1).lower()
                                is_intrinsic = "intrinsic" in line.lower()
                                if dep_name not in intrinsic_modules and not is_intrinsic:
                                    dependencies.add(dep_name)
                                continue
                                
                            if private_stmt_rx.match(line):
                                parts = line.split('::')
                                if len(parts) > 1:
                                    vars_part = parts[1]
                                    for v in re.findall(r'\b[a-zA-Z_]\w*\b', vars_part):
                                        explicit_private_vars.add(v.lower())
                                else:
                                    if re.match(r'^\s*private\s*$', line, re.IGNORECASE):
                                        is_default_private = True
                                continue
                                
                            if public_stmt_rx.match(line):
                                parts = line.split('::')
                                if len(parts) > 1:
                                    vars_part = parts[1]
                                    for v in re.findall(r'\b[a-zA-Z_]\w*\b', vars_part):
                                        explicit_public_vars.add(v.lower())
                                continue
                                
                            if decl_rx.match(line):
                                is_param = "parameter" in line.lower()
                                is_decl_private = "private" in line.lower()
                                is_decl_public = "public" in line.lower()
                                
                                parts = line.split('::')
                                vars_part = parts[1] if len(parts) > 1 else line
                                vars_part_no_init = re.sub(r'=[^,]*', '', vars_part)
                                names = re.findall(r'\b[a-zA-Z_]\w*\b', vars_part_no_init)
                                
                                for name in names:
                                    name_lower = name.lower()
                                    declared_vars.append({
                                        "name": name_lower,
                                        "is_parameter": is_param,
                                        "is_private": is_decl_private,
                                        "is_public": is_decl_public
                                    })
                                    
                        for var in declared_vars:
                            name_lower = var["name"]
                            if var["is_parameter"]:
                                continue
                            is_private = var["is_private"]
                            if not is_private:
                                if name_lower in explicit_private_vars:
                                    is_private = True
                                elif is_default_private and name_lower not in explicit_public_vars:
                                    is_private = True
                            if not is_private:
                                public_vars.append(name_lower)
                                
                        all_modules[mod_name_lower] = {
                            "name": mod_name,
                            "file": rel_path,
                            "dependencies": sorted(list(dependencies)),
                            "exposes_mutable_public_state": len(public_vars) > 0,
                            "public_variables": public_vars,
                            "fan_in": 0,
                            "fan_out": len(dependencies)
                        }
                except Exception:
                    pass
                    
    project_module_names = set(all_modules.keys())
    for mod_lower, mod_info in all_modules.items():
        valid_deps = [d for d in mod_info["dependencies"] if d in project_module_names]
        mod_info["dependencies"] = valid_deps
        mod_info["fan_out"] = len(valid_deps)
        
    for mod_lower, mod_info in all_modules.items():
        for dep in mod_info["dependencies"]:
            if dep in all_modules:
                all_modules[dep]["fan_in"] += 1
                
    keystones = sorted(
        [info for name, info in all_modules.items()],
        key=lambda x: x["fan_in"],
        reverse=True
    )
    
    mermaid_lines = ["graph TD"]
    for mod_lower, mod_info in all_modules.items():
        style = ""
        if mod_info["exposes_mutable_public_state"]:
            style = f"style {mod_info['name']} fill:#ffdddd,stroke:#ff5555,stroke-width:2px"
            
        mermaid_lines.append(f"    {mod_info['name']}")
        if style:
            mermaid_lines.append(f"    {style}")
            
        for dep in mod_info["dependencies"]:
            dep_name = all_modules[dep]["name"]
            mermaid_lines.append(f"    {mod_info['name']} --> {dep_name}")
            
    mermaid_graph = "\n".join(mermaid_lines)
    
    result = {
        "modules": all_modules,
        "keystones": [
            {"name": x["name"], "fan_in": x["fan_in"], "fan_out": x["fan_out"], "exposes_mutable_public_state": x["exposes_mutable_public_state"]}
            for x in keystones
        ],
        "mermaid": mermaid_graph
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
def find_large_units(project_path: str) -> str:
    """Detects oversized procedures and modules (complexity / 'god-unit' analysis).
    Analyzes physical lines, actual code lines, maximum control-flow nesting depth,
    and SELECT CASE arity across the project. Highly useful for detecting decomposition targets.
    """
    import os
    import re
    import json
    
    if not os.path.isdir(project_path):
        return f"Error: Project path not found or is not a directory: {project_path}"
        
    fortran_extensions = {".f90", ".f", ".f95", ".f03", ".f08", ".for", ".f77", ".ftn"}
    
    large_units = []
    exclude_dirs = {".git", ".venv", "__pycache__", "build", "dist"}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in fortran_extensions:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                        
                    linter = FortranLinter(code)
                    rel_path = os.path.relpath(file_path, project_path)
                    
                    units = linter.find_scoping_units()
                    procedures = linter.find_procedures()
                    
                    def get_code_lines_count(start, end):
                        count = 0
                        for idx in range(start - 1, end):
                            line = linter.lines[idx]
                            stripped = line.strip()
                            if not stripped:
                                continue
                            if linter.is_fixed_format and linter.fixed_comment_rx.match(line):
                                continue
                            if stripped.startswith('!'):
                                continue
                            count += 1
                        return count
                        
                    for u in units:
                        if u["type"] in ["module", "program"]:
                            start = u["start"]
                            end = u["end"]
                            total_lines = end - start + 1
                            code_lines = get_code_lines_count(start, end)
                            
                            large_units.append({
                                "name": u["name"],
                                "type": u["type"],
                                "file": rel_path,
                                "line_start": start,
                                "line_end": end,
                                "lines_total": total_lines,
                                "lines_code": code_lines,
                                "max_nesting_depth": 0,
                                "select_case_count": 0,
                                "max_select_case_arity": 0
                            })
                            
                    for proc in procedures:
                        start = proc["start"]
                        end = proc["end"]
                        total_lines = end - start + 1
                        code_lines = get_code_lines_count(start, end)
                        
                        max_depth = 0
                        current_depth = 0
                        select_case_count = 0
                        max_select_case_arity = 0
                        select_case_stack = []
                        
                        block_start_rx = re.compile(r'^\s*block\b', re.IGNORECASE)
                        associate_start_rx = re.compile(r'^\s*associate\b', re.IGNORECASE)
                        select_case_start_rx = re.compile(r'^\s*select\s*case\b', re.IGNORECASE)
                        do_start_rx = re.compile(r'^\s*(?:\w+\s*:)?\s*do\b', re.IGNORECASE)
                        if_then_rx = re.compile(r'^\s*(?:\w+\s*:)?\s*if\s*\(.*\)\s*then\b', re.IGNORECASE)
                        
                        end_block_rx = re.compile(r'^\s*end\s*block\b', re.IGNORECASE)
                        end_associate_rx = re.compile(r'^\s*end\s*associate\b', re.IGNORECASE)
                        end_select_rx = re.compile(r'^\s*end\s*select\b', re.IGNORECASE)
                        end_do_rx = re.compile(r'^\s*end\s*do\b', re.IGNORECASE)
                        end_if_rx = re.compile(r'^\s*end\s*if\b', re.IGNORECASE)
                        
                        case_rx = re.compile(r'^\s*case\b', re.IGNORECASE)
                        
                        for line_no in range(start, end + 1):
                            line = linter._clean_line(linter.lines[line_no - 1])
                            if not line:
                                continue
                                
                            if select_case_start_rx.match(line):
                                select_case_count += 1
                                select_case_stack.append(0)
                                current_depth += 1
                                if current_depth > max_depth:
                                    max_depth = current_depth
                                continue
                                
                            if end_select_rx.match(line):
                                if select_case_stack:
                                    arity = select_case_stack.pop()
                                    if arity > max_select_case_arity:
                                        max_select_case_arity = arity
                                current_depth = max(0, current_depth - 1)
                                continue
                                
                            if case_rx.match(line):
                                if select_case_stack:
                                    select_case_stack[-1] += 1
                                continue
                                
                            if block_start_rx.match(line) or associate_start_rx.match(line) or do_start_rx.match(line) or if_then_rx.match(line):
                                current_depth += 1
                                if current_depth > max_depth:
                                    max_depth = current_depth
                                continue
                                
                            if end_block_rx.match(line) or end_associate_rx.match(line) or end_do_rx.match(line) or end_if_rx.match(line):
                                current_depth = max(0, current_depth - 1)
                                continue
                                
                        while select_case_stack:
                            arity = select_case_stack.pop()
                            if arity > max_select_case_arity:
                                max_select_case_arity = arity
                                
                        large_units.append({
                            "name": proc["name"],
                            "type": proc["type"],
                            "file": rel_path,
                            "line_start": start,
                            "line_end": end,
                            "lines_total": total_lines,
                            "lines_code": code_lines,
                            "max_nesting_depth": max_depth,
                            "select_case_count": select_case_count,
                            "max_select_case_arity": max_select_case_arity
                        })
                except Exception:
                    pass
                    
    ranked_units = sorted(large_units, key=lambda x: x["lines_total"], reverse=True)
    return json.dumps(ranked_units, indent=2)


# ---------------------------------------------------------------------------
# AST-backed syntax validation (fparser2)
# ---------------------------------------------------------------------------

# fparser2 supports only the 'f2003' and 'f2008' grammars. Map the broader set
# of standard names agents use onto that ceiling. f2008 is a permissive superset
# (submodules, coarrays, do concurrent, block, ...) and parses real-world modern
# F2018 codebases cleanly, so it is the default.
def _map_to_fparser_std(fortran_version: str) -> str:
    v = (fortran_version or "").lower().strip().lstrip("f").replace("-", "").replace("_", "")
    if v in ("2008", "2018", "2023", "18", "23", "08"):
        return "f2008"
    return "f2003"

# Detect C-preprocessor directives that require a preprocessing pass before the
# source is valid Fortran (e.g. function-like macros such as SG_CHECKMEM(...)).
_CPP_DIRECTIVE_RX = re.compile(r"(?m)^\s*#\s*(include|define|if|ifdef|ifndef|else|elif|endif|undef|pragma)\b")

def _detect_fixed_format(code: str) -> bool:
    """Reuse the linter's heuristic: a 'C'/'c'/'*' comment in column 1 marks fixed-format."""
    fixed_comment_rx = re.compile(r'^[Cc\*](?:\s|[^\w]|$)')
    for line in code.splitlines()[:50]:
        if fixed_comment_rx.match(line):
            return True
    return False

def _preprocess_source(file_path: str, include_dirs: Optional[List[str]]) -> dict:
    """Run a Fortran-aware C preprocessor (gfortran -cpp -E -P) over a file.

    gfortran's preprocessor is used in preference to plain 'cpp' because it
    tolerates Fortran tokens (e.g. empty string literals '') that trip cpp.
    Returns {'ok': bool, 'text': str|None, 'error': str|None}.
    """
    gfortran = shutil.which("gfortran")
    if not gfortran:
        return {"ok": False, "text": None,
                "error": "gfortran not found on PATH; cannot preprocess. Install gfortran or pass already-preprocessed source."}
    cmd = [gfortran, "-cpp", "-E", "-P", "-I", os.path.dirname(os.path.abspath(file_path))]
    for d in (include_dirs or []):
        cmd += ["-I", d]
    cmd.append(file_path)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return {"ok": False, "text": None, "error": f"Error invoking gfortran preprocessor: {e}"}
    if res.returncode != 0:
        return {"ok": False, "text": None,
                "error": f"Preprocessing failed (exit {res.returncode}):\n{res.stderr.strip()}"}
    return {"ok": True, "text": res.stdout, "error": None}

def _parse_fortran(code: str, fparser_std: str) -> dict:
    """Parse a Fortran source string with fparser2. Returns a result dict with
    'passed', and on failure 'line'/'snippet'/'message'."""
    try:
        from fparser.two.parser import ParserFactory
        from fparser.common.readfortran import FortranStringReader
        from fparser.common.sourceinfo import FortranFormat
        from fparser.two.utils import FortranSyntaxError, walk
        from fparser.two import Fortran2003 as F
    except ImportError as e:
        return {"passed": False, "error": f"fparser is not installed ({e}). Add 'fparser' to the environment."}

    try:
        reader = FortranStringReader(code, ignore_comments=True)
        # Tell the reader the layout explicitly; FortranStringReader defaults to
        # free-format, so fixed-format (F77) source must be flagged or it fails.
        reader.set_format(FortranFormat(not _detect_fixed_format(code), False))
        tree = ParserFactory().create(std=fparser_std)(reader)
    except FortranSyntaxError as e:
        msg = str(e)
        m = re.search(r"at line (\d+)", msg)
        line = int(m.group(1)) if m else None
        snippet = ""
        for part in msg.split("\n"):
            if part.strip().startswith(">>>"):
                snippet = part.replace(">>>", "").strip()
                break
        return {"passed": False, "syntax_error": True, "line": line,
                "snippet": snippet, "message": msg.strip()}
    except Exception as e:
        return {"passed": False, "error": f"{type(e).__name__}: {e}"}

    # Light structural summary so a passing result is also informative.
    try:
        summary = {
            "modules": len(walk(tree, F.Module)),
            "subroutines": len(walk(tree, F.Subroutine_Subprogram)),
            "functions": len(walk(tree, F.Function_Subprogram)),
        }
    except Exception:
        summary = {}
    return {"passed": True, "summary": summary}


@mcp.tool()
def validate_syntax(code: str, fortran_version: str = "f2018") -> str:
    """Validate that a string of Fortran is syntactically parseable, using the fparser2 AST.

    This is a fast, build-free syntax gate distinct from compile_project: it needs no
    build system and no other modules present, making it ideal for a tight self-correction
    loop. Note fparser2's grammar ceiling is Fortran 2003 + partial 2008, so newer/exotic
    F2018 constructs may report as syntax errors even when valid.

    Args:
        code: The Fortran source to validate.
        fortran_version: Standard hint (e.g. 'f2003', 'f2008', 'f2018'). Mapped onto
            fparser2's supported grammars ('f2003'/'f2008'); defaults to 'f2018' -> f2008.
    """
    std = _map_to_fparser_std(fortran_version)
    has_cpp = bool(_CPP_DIRECTIVE_RX.search(code))
    result = _parse_fortran(code, std)

    if result.get("passed"):
        s = result.get("summary", {})
        extra = ""
        if s:
            extra = f" ({s.get('modules',0)} module(s), {s.get('subroutines',0)} subroutine(s), {s.get('functions',0)} function(s))"
        return f"✅ Syntax OK (parsed with fparser2 std={std}){extra}."

    if result.get("error"):
        return f"⚠️ Could not validate: {result['error']}"

    # Syntax error path.
    loc = f" at line {result['line']}" if result.get("line") else ""
    lines = [f"❌ Syntax error{loc} (fparser2 std={std}):"]
    if result.get("snippet"):
        lines.append(f"  >>> {result['snippet']}")
    if has_cpp:
        lines.append("")
        lines.append("Note: this source contains C-preprocessor directives (#include/#define/...). "
                     "fparser2 does not expand macros, so the failure may be an unexpanded macro rather "
                     "than a real syntax error. Use validate_syntax_file(..., preprocess='auto') to "
                     "preprocess first.")
    return "\n".join(lines)


@mcp.tool()
def validate_syntax_file(
    file_path: str,
    fortran_version: str = "f2018",
    preprocess: str = "auto",
    include_dirs: Optional[List[str]] = None,
) -> str:
    """Validate a Fortran source file's syntax using the fparser2 AST, preprocessing if needed.

    A build-free syntax gate (see validate_syntax). Many real codebases rely on C-preprocessor
    macros (e.g. function-like macros that are not valid Fortran until expanded); this tool can
    run a Fortran-aware preprocessor (gfortran -cpp -E -P) before parsing so those files validate.

    Args:
        file_path: Path to the Fortran file (.f90, .f, .F90, ...).
        fortran_version: Standard hint; mapped onto fparser2's 'f2003'/'f2008' (default f2018 -> f2008).
        preprocess: 'auto' (preprocess only if cpp directives are detected), 'always', or 'never'.
        include_dirs: Extra '-I' include directories for the preprocessor (the file's own
            directory is always included).
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"

    std = _map_to_fparser_std(fortran_version)
    has_cpp = bool(_CPP_DIRECTIVE_RX.search(raw))
    do_pp = preprocess == "always" or (preprocess == "auto" and has_cpp)

    code = raw
    pp_note = ""
    if do_pp:
        pp = _preprocess_source(file_path, include_dirs)
        if pp["ok"]:
            code = pp["text"]
            pp_note = " (preprocessed)"
        else:
            # If preprocessing was only auto-triggered, fall through to a raw parse but
            # surface the preprocessing failure so the agent can act on it.
            if preprocess == "always":
                return f"⚠️ Preprocessing required but failed for '{os.path.basename(file_path)}':\n{pp['error']}"
            pp_note = f" (preprocessing attempted but failed: {pp['error']})"

    result = _parse_fortran(code, std)

    if result.get("passed"):
        s = result.get("summary", {})
        extra = ""
        if s:
            extra = f" ({s.get('modules',0)} module(s), {s.get('subroutines',0)} subroutine(s), {s.get('functions',0)} function(s))"
        return f"✅ {os.path.basename(file_path)}: Syntax OK (fparser2 std={std}{pp_note}){extra}."

    if result.get("error"):
        return f"⚠️ {os.path.basename(file_path)}: Could not validate: {result['error']}"

    loc = f" at line {result['line']}" if result.get("line") else ""
    lines = [f"❌ {os.path.basename(file_path)}: Syntax error{loc} (fparser2 std={std}{pp_note}):"]
    if result.get("snippet"):
        lines.append(f"  >>> {result['snippet']}")
    if has_cpp and not do_pp:
        lines.append("")
        lines.append("Note: this file contains C-preprocessor directives but was not preprocessed. "
                     "Re-run with preprocess='auto' or 'always' to expand macros before validating.")
    elif has_cpp and do_pp and result.get("snippet"):
        lines.append("")
        lines.append("This failure is after preprocessing, so it is likely a genuine syntax error "
                     "(or a construct beyond fparser2's F2003/F2008 grammar).")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

