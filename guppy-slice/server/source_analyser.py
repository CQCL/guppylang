import importlib.util
import inspect
import guppylang as gpy_lang
from guppylang.checker.core import Variable
import guppylang.definition as gpy_lib_def

import sys
import os
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dependency_analyser import compute_cfg_dependencies, ProgramDependencies
from lsprotocol.types import Position

test_file = "guppy-slice/examples/example1.py"

def get_function_lineno(parsed_code, function_name):
    for node in ast.walk(parsed_code):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node.lineno
    return None

def compute_dependencies(test_file):
    spec = importlib.util.spec_from_file_location("source_module", test_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    guppy_modules = [
        obj for _, obj in inspect.getmembers(mod) if isinstance(obj, gpy_lang.GuppyModule)
    ]

    for guppy_module in guppy_modules:
        try:
            guppy_module.check()
        except Exception as e:
            print(f"Error checking guppy module {guppy_module.name}: {e}")

        checked_funcs = [
            checked_def
            for checked_def in guppy_module._checked_defs.values()
            if isinstance(checked_def, gpy_lib_def.function.CheckedFunctionDef)
        ]

        mod_deps: dict[str, tuple[ProgramDependencies, int]] = {}

        # For finding function offset in the file.
        with open(test_file, 'r') as file:
            source_code = file.read()
        parsed_code = compile(source_code, test_file, 'exec', ast.PyCF_ONLY_AST)

        for func in checked_funcs:
            deps = compute_cfg_dependencies(func.cfg, guppy_module._globals)
            func_offset = get_function_lineno(parsed_code, func.name)
            mod_deps[func.name] = (deps, func_offset)

        return mod_deps

def adjust_pos(pos: Position, line_offset) -> Position:
    # -2 for guppy decorator and function definition
    return Position(line=pos.line + line_offset - 2, character=pos.character - 1)

def get_dep_spans_for_var(variable_id, deps: tuple[ProgramDependencies, int]):
    positions = []
    for stmt, dep_vars in deps[0].mapping.items():
        if variable_id in dep_vars:
            start_pos = adjust_pos(Position(line=stmt.lineno, character=stmt.col_offset), deps[1])
            end_pos = adjust_pos(Position(line=stmt.end_lineno, character=stmt.end_col_offset), deps[1])
            positions.append((start_pos, end_pos))
    return positions

def compute_inverse_spans(file_path, spans):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    inverse_spans = []
    current_pos = Position(line=0, character=0)

    for span in spans:
        start, end = span

        # Add span from current_pos to start of the current span
        if current_pos.line < start.line or (current_pos.line == start.line and current_pos.character < start.character):
            inverse_spans.append((current_pos, start))

        # Update current_pos to the end of the current span
        current_pos = Position(line=end.line, character=end.character)

    # Add span from the end of the last span to the end of the file
    if current_pos.line < len(lines) or (current_pos.line == len(lines) and current_pos.character < len(lines[-1])):
        inverse_spans.append((current_pos, Position(line=len(lines), character=len(lines[-1]))))

    return inverse_spans


deps = compute_dependencies(test_file)
variable_id = Variable.Id("q")
dep_spans = get_dep_spans_for_var(variable_id, deps["test"])
print(compute_inverse_spans(test_file, dep_spans))
