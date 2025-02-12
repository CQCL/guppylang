import importlib.util
import inspect
import guppylang as gpy


test_file = "guppy-slice/example_programs/test1.py"

global_state = {}
exec(open(test_file).read(), global_state)

# Remove built-ins to get only user-defined state
user_defined_state = {k: v for k, v in global_state.items() if not k.startswith("__")}

guppy_modules = [obj for obj in user_defined_state.values() if isinstance(obj, gpy.module.GuppyModule)]

for mod in guppy_modules:
    mod.check()

