"""This module contains JSON definitions for external extensions."""

import pkgutil

from hugr._serialization.extension import Extension as PdExtension
from hugr.ext import Extension


def load_extension(name: str) -> Extension:
    replacement = name.replace(".", "/")
    json_str = pkgutil.get_data(__name__, f"{replacement}.json")
    assert json_str is not None
    # TODO: Replace with `Extension.from_json` once that is implemented
    # https://github.com/CQCL/hugr/issues/1523
    return PdExtension.model_validate_json(json_str).deserialize()
