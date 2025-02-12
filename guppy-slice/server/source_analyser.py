import importlib.util
import inspect
import guppylang as gpy_lang
from guppylang.checker.core import Variable
import guppylang.definition as gpy_lib_def

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dependency_analyser import compute_cfg_dependencies, ProgramDependencies
from lsprotocol.types import Position

test_file = "guppy-slice/examples/example1.py"

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

        mod_deps: dict[str, ProgramDependencies] = {}
        for func in checked_funcs:
            deps = compute_cfg_dependencies(func.cfg, guppy_module._globals)
            mod_deps[func.name] = deps

        return mod_deps


def get_dep_spans_for_var(variable_id, deps):
    positions = []
    for stmt, dep_vars in deps.mapping.items():
        if variable_id in dep_vars:
            start_pos = Position(line=stmt.lineno, character=stmt.col_offset)
            end_pos = Position(line=stmt.end_lineno, character=stmt.end_col_offset)
            positions.append((start_pos, end_pos))
    return positions


deps = compute_dependencies(test_file)
variable_id = Variable.Id("q")
dep_spans = get_dep_spans_for_var(variable_id, deps["test"])
print(dep_spans)
