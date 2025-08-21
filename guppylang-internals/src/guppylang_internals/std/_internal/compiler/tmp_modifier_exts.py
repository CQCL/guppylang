# TODO: (k.hirata) WIP
# This file is a temporary file for modifier extensions.
# After Hugr supports modifier extensions, this file will be removed.
import pkgutil
from hugr.ext import Extension

json_str = pkgutil.get_data(__name__, f"tmp_modifier.json")
if json_str is not None:
    MODIFIER_EXTENSION = Extension.from_json(json_str.decode())
