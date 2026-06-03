import re
from typing import List, Dict, Any

class FortranLinter:
    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.warnings: List[Dict[str, Any]] = []

    def lint(self) -> List[Dict[str, Any]]:
        self.warnings = []
        
        # Step 1: Find all scoping units (modules, programs, subroutines, functions)
        units = self.find_scoping_units()
        
        # Step 2: Check for missing 'implicit none'
        self.check_implicit_none(units)
        
        # Step 3: Check for obsolete type representations
        self.check_obsolete_types()
        
        # Step 4: Check for missing intent on dummy arguments
        procedures = self.find_procedures()
        self.check_procedure_intents(procedures)
        
        # Step 5: Check for fixed-format layout issues
        self.check_fixed_format()
        
        # Step 6: Check for obsolete/deprecated statements
        self.check_obsolete_constructs()
        
        # Sort warnings by line number
        self.warnings.sort(key=lambda x: x["line"])
        return self.warnings

    def find_scoping_units(self) -> List[Dict[str, Any]]:
        units = []
        active_stack = []
        
        program_start_rx = re.compile(r'^\s*program\s+([a-zA-Z_]\w*)', re.IGNORECASE)
        module_start_rx = re.compile(r'^\s*module\s+(?!procedure|function\b)([a-zA-Z_]\w*)', re.IGNORECASE)
        subroutine_start_rx = re.compile(r'^\s*(?:(?:pure|elemental|recursive)\s+)*subroutine\s+([a-zA-Z_]\w*)', re.IGNORECASE)
        function_start_rx = re.compile(r'^\s*(?:[a-zA-Z_]\w*(?:\([^)]*\))?\s+)*(?:(?:pure|elemental|recursive)\s+)*function\s+([a-zA-Z_]\w*)', re.IGNORECASE)
        
        for i, line in enumerate(self.lines):
            line_no_comment = line.split('!')[0].strip()
            if not line_no_comment:
                continue
                
            # Check end of unit
            end_match = re.match(r'^\s*end\s*(?:program|module|subroutine|function)?\b', line_no_comment, re.IGNORECASE)
            if end_match:
                if active_stack:
                    closed_unit = active_stack.pop()
                    closed_unit["end"] = i + 1
                    units.append(closed_unit)
                continue
                
            # Check start of program
            prog_m = program_start_rx.match(line_no_comment)
            if prog_m:
                new_unit = {
                    "type": "program",
                    "name": prog_m.group(1),
                    "start": i + 1,
                    "end": None,
                    "parent": active_stack[-1]["name"] if active_stack else None,
                    "parent_type": active_stack[-1]["type"] if active_stack else None
                }
                active_stack.append(new_unit)
                continue
                
            # Check start of module
            mod_m = module_start_rx.match(line_no_comment)
            if mod_m:
                new_unit = {
                    "type": "module",
                    "name": mod_m.group(1),
                    "start": i + 1,
                    "end": None,
                    "parent": active_stack[-1]["name"] if active_stack else None,
                    "parent_type": active_stack[-1]["type"] if active_stack else None
                }
                active_stack.append(new_unit)
                continue
                
            # Check start of subroutine
            sub_m = subroutine_start_rx.match(line_no_comment)
            if sub_m:
                new_unit = {
                    "type": "subroutine",
                    "name": sub_m.group(1),
                    "start": i + 1,
                    "end": None,
                    "parent": active_stack[-1]["name"] if active_stack else None,
                    "parent_type": active_stack[-1]["type"] if active_stack else None
                }
                active_stack.append(new_unit)
                continue
                
            # Check start of function
            fun_m = function_start_rx.match(line_no_comment)
            if fun_m and not re.match(r'^\s*end\b', line_no_comment, re.IGNORECASE):
                new_unit = {
                    "type": "function",
                    "name": fun_m.group(1),
                    "start": i + 1,
                    "end": None,
                    "parent": active_stack[-1]["name"] if active_stack else None,
                    "parent_type": active_stack[-1]["type"] if active_stack else None
                }
                active_stack.append(new_unit)
                continue
                
        while active_stack:
            closed_unit = active_stack.pop()
            closed_unit["end"] = len(self.lines)
            units.append(closed_unit)
            
        return units

    def check_implicit_none(self, units: List[Dict[str, Any]]):
        has_implicit_none = {}
        units_sorted = sorted(units, key=lambda x: x["start"])
        
        for u in units_sorted:
            start_idx = u["start"]
            end_idx = u["end"]
            
            # Find declaration limit (e.g. contains or nested unit start)
            limit_idx = end_idx
            for j in range(start_idx, end_idx):
                line = self.lines[j].split('!')[0].strip()
                if not line:
                    continue
                if re.match(r'^\s*contains\b', line, re.IGNORECASE):
                    limit_idx = j + 1
                    break
                if re.match(r'^\s*(?:program|module|subroutine|function)\b', line, re.IGNORECASE) and j + 1 > start_idx:
                    limit_idx = j + 1
                    break
                    
            declared = False
            implicit_none_rx = re.compile(r'\bimplicit\s+none\b', re.IGNORECASE)
            for j in range(start_idx, limit_idx):
                line = self.lines[j - 1].split('!')[0]
                if implicit_none_rx.search(line):
                    declared = True
                    break
                    
            has_implicit_none[u["name"].lower()] = declared
            
            need_warning = False
            reason = ""
            
            if u["type"] in ["program", "module"]:
                if not declared:
                    need_warning = True
                    reason = f"Every {u['type']} unit ('{u['name']}') should declare 'implicit none' to disable legacy implicit typing rules."
            else:  # subroutine or function
                if not declared:
                    parent_has_it = False
                    if u["parent"] and u["parent_type"] == "module":
                        parent_has_it = has_implicit_none.get(u["parent"].lower(), False)
                    
                    if not parent_has_it:
                        need_warning = True
                        if u["parent"]:
                            reason = f"Procedure '{u['name']}' is missing 'implicit none' and its containing module '{u['parent']}' also lacks it."
                        else:
                            reason = f"External procedure '{u['name']}' is missing 'implicit none'. Every procedure must declare 'implicit none' or be placed inside a module that does."
                            
            if need_warning:
                self.warnings.append({
                    "line": start_idx,
                    "code": self.lines[start_idx - 1].strip(),
                    "rule": "missing_implicit_none",
                    "severity": "warning",
                    "message": reason
                })

    def check_obsolete_types(self):
        obsolete_type_rx = re.compile(r'\b(real|integer|complex|logical|character)\s*\*\s*([0-9]+)\b', re.IGNORECASE)
        for i, line in enumerate(self.lines):
            line_no_comment = line.split('!')[0]
            match = obsolete_type_rx.search(line_no_comment)
            if match:
                t, p = match.groups()
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "obsolete_types",
                    "severity": "warning",
                    "message": f"Non-standard '{t}*{p}' syntax used. Use modern standard KIND parameters, e.g. '{t}(kind=dp)' or '{t}(kind=int64)'."
                })
            
            if re.search(r'\bdouble\s+precision\b', line_no_comment, re.IGNORECASE):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "legacy_types",
                    "severity": "info",
                    "message": "Use of 'double precision' is standard but legacy. Consider using 'real(kind=dp)' with 'dp' defined via intrinsic 'iso_fortran_env' for modern code consistency."
                })

    def find_procedures(self) -> List[Dict[str, Any]]:
        procedures = []
        subroutine_start_rx = re.compile(
            r'^\s*(?:(?:pure|elemental|recursive)\s+)*subroutine\s+([a-zA-Z_]\w*)\s*(?:\(([^)]*)\))?',
            re.IGNORECASE
        )
        function_start_rx = re.compile(
            r'^\s*(?:[a-zA-Z_]\w*(?:\([^)]*\))?\s+)*(?:(?:pure|elemental|recursive)\s+)*function\s+([a-zA-Z_]\w*)\s*(?:\(([^)]*)\))?',
            re.IGNORECASE
        )
        
        for i, line in enumerate(self.lines):
            line_no_comment = line.split('!')[0].strip()
            if not line_no_comment:
                continue
                
            sub_match = subroutine_start_rx.match(line_no_comment)
            if sub_match:
                name, args_str = sub_match.groups()
                # Dummy args can contain continuation lines, but we just split on comma for standard ones
                args = [a.strip() for a in args_str.split(',')] if args_str else []
                args = [a for a in args if a]
                procedures.append({
                    "type": "subroutine",
                    "name": name,
                    "args": args,
                    "start": i + 1,
                    "end": None
                })
                continue
                
            fun_match = function_start_rx.match(line_no_comment)
            if fun_match and not re.match(r'^\s*end\b', line_no_comment, re.IGNORECASE):
                name, args_str = fun_match.groups()
                args = [a.strip() for a in args_str.split(',')] if args_str else []
                args = [a for a in args if a]
                procedures.append({
                    "type": "function",
                    "name": name,
                    "args": args,
                    "start": i + 1,
                    "end": None
                })
                continue

        # Determine procedure ends
        for proc in procedures:
            start_idx = proc["start"]
            for j in range(start_idx, len(self.lines)):
                curr_line = self.lines[j].split('!')[0].strip()
                end_match = re.match(r'^\s*end\s*(?:subroutine|function)?\b', curr_line, re.IGNORECASE)
                if end_match:
                    name_part = curr_line.split()
                    if len(name_part) > 2 and name_part[-1].lower() == proc["name"].lower():
                        proc["end"] = j + 1
                        break
                    elif len(name_part) == 2 and name_part[1].lower() in ["subroutine", "function"]:
                        proc["end"] = j + 1
                        break
                    elif len(name_part) == 1 and name_part[0].lower() == "end":
                        proc["end"] = j + 1
                        break
            if proc["end"] is None:
                proc["end"] = len(self.lines)
                
        return procedures

    def check_procedure_intents(self, procedures: List[Dict[str, Any]]):
        for proc in procedures:
            args = proc["args"]
            if not args:
                continue
            
            start_idx = proc["start"]
            end_idx = proc["end"]
            
            for arg in args:
                # Don't check '*' dummy arguments (alternative return labels in subroutines)
                if arg == '*':
                    continue
                    
                found_intent = False
                for line_no in range(start_idx, end_idx):
                    line = self.lines[line_no - 1].split('!')[0]
                    if not line.strip():
                        continue
                    if not re.search(r'\bintent\s*\(', line, re.IGNORECASE):
                        continue
                    
                    if '::' in line:
                        decl_parts = line.split('::')
                        vars_part = decl_parts[1]
                    else:
                        vars_part = line
                        
                    if re.search(r'\b' + re.escape(arg) + r'\b', vars_part, re.IGNORECASE):
                        found_intent = True
                        break
                
                if not found_intent:
                    self.warnings.append({
                        "line": start_idx,
                        "code": self.lines[start_idx - 1].strip(),
                        "rule": "missing_intent",
                        "severity": "warning",
                        "message": f"Argument '{arg}' in procedure '{proc['name']}' has no explicit INTENT (intent(in), intent(out), or intent(inout)) declared."
                    })

    def check_fixed_format(self):
        # Scan for lines starting with 'C' or '*' in column 1 followed by space/non-word (classic fixed-format comments)
        fixed_comment_rx = re.compile(r'^[Cc\*](?:\s|[^\w]|$)[^\n]*')
        
        for i, line in enumerate(self.lines):
            # Only inspect first 20 lines to determine if fixed format warning should be triggered
            if i > 20:
                break
            if fixed_comment_rx.match(line):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "fixed_format",
                    "severity": "warning",
                    "message": "Fixed-format style comment block or layout detected. Modern Fortran uses free-format layout (standardizing on '.f90' file extension)."
                })
                break

    def check_obsolete_constructs(self):
        common_rx = re.compile(r'\bcommon\b', re.IGNORECASE)
        equivalence_rx = re.compile(r'\bequivalence\b', re.IGNORECASE)
        goto_rx = re.compile(r'\bgoto\s+[0-9]+\b|\bgo\s+to\s+[0-9]+\b', re.IGNORECASE)
        assigned_goto_rx = re.compile(r'\bassign\s+[0-9]+\s+to\b', re.IGNORECASE)
        pause_rx = re.compile(r'\bpause\b', re.IGNORECASE)
        arithmetic_if_rx = re.compile(r'\bif\s*\(.*\)\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\b', re.IGNORECASE)
        dimension_stmt_rx = re.compile(r'^\s*dimension\b', re.IGNORECASE)

        for i, line in enumerate(self.lines):
            line_no_comment = line.split('!')[0]
            if common_rx.search(line_no_comment):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "common_block",
                    "severity": "warning",
                    "message": "Common blocks are obsolete. Use modules to share global state and variables."
                })
            if equivalence_rx.search(line_no_comment):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "equivalence",
                    "severity": "warning",
                    "message": "EQUIVALENCE statement is obsolete and unsafe. Use pointers or the TRANSFER function instead."
                })
            if goto_rx.search(line_no_comment):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "goto",
                    "severity": "warning",
                    "message": "GOTO statement is legacy. Use modern structural flow control (e.g. IF/ELSE blocks, CYCLE, EXIT)."
                })
            if assigned_goto_rx.search(line_no_comment):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "assigned_goto",
                    "severity": "error",
                    "message": "ASSIGN and assigned GOTO are deleted features in modern Fortran standards."
                })
            if pause_rx.search(line_no_comment):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "pause",
                    "severity": "warning",
                    "message": "PAUSE statement is deleted in modern Fortran. Use standard read(*,*) to wait for input instead."
                })
            if arithmetic_if_rx.search(line_no_comment):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "arithmetic_if",
                    "severity": "warning",
                    "message": "Arithmetic IF is obsolescent. Use standard logical block IF/ELSEIF statements."
                })
            if dimension_stmt_rx.search(line_no_comment):
                self.warnings.append({
                    "line": i + 1,
                    "code": line.strip(),
                    "rule": "dimension_statement",
                    "severity": "warning",
                    "message": "Standalone DIMENSION statements are obsolete. Declare dimensions directly inside type statements, e.g. 'real :: x(10)'."
                })
