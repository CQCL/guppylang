from typing import TypeVar

import validator
from guppy.hugr.hugr import Hugr


def validate(hugr: Hugr):
    validator.validate(hugr.serialize())


class Decorator:
    def __matmul__(self, other):
        return None


# Dummy names to import to avoid errors for `_@functional` pseudo-decorator:
functional = Decorator()
_ = Decorator()
