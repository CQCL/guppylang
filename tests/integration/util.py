from typing import Any

import validator


def validate_bytes(hugr: bytes):
    validator.validate(hugr)


class Decorator:
    def __matmul__(self, other):
        return None


# Dummy names to import to avoid errors for `_@functional` pseudo-decorator:
functional = Decorator()
_ = Decorator()


def py(*args: Any) -> Any:
    """Dummy function to import to avoid errors for `py(...)` expressions"""
    raise NotImplementedError
