"""Mocks for a number of builtin functions to be used during tracing.

For example, the builtin `int(x)` function tries calling `x.__int__()` and raises a
`TypeError` if this call doesn't return an `int`. During tracing however, we also want
to allow `int(x)` if `x` is an abstract `GuppyObject`. To allow this, we need to mock
the builtins to avoid raising the `TypeError` in that case.
"""

import builtins
from collections.abc import Callable
from typing import Any

from guppylang.tracing.object import GuppyObject, GuppyStructObject


def _mock_meta(cls: type) -> type:
    """Returns a metaclass that replicates the behaviour of the provided class.

    The only way to distinguishing a `_mock_meta(T)` from an actual `T` is via checking
    reference equality using the `is` operator.
    """

    class MockMeta(type):
        def __instancecheck__(self, instance: Any) -> bool:
            return cls.__instancecheck__(instance)

        def __subclasscheck__(self, subclass: type) -> bool:
            return cls.__subclasscheck__(subclass)

        def __eq__(self, other: object) -> Any:
            return other == cls

        def __ne__(self, other: object) -> Any:
            return other != cls

    MockMeta.__name__ = type.__name__
    MockMeta.__qualname__ = type.__qualname__
    return MockMeta


class float(builtins.float, metaclass=_mock_meta(builtins.float)):  # type: ignore[misc]
    def __new__(cls, x: Any = 0.0, /) -> Any:
        if isinstance(x, GuppyObject):
            return x.__float__()
        return builtins.float(x)


class int(builtins.int, metaclass=_mock_meta(builtins.int)):  # type: ignore[misc]
    def __new__(cls, x: Any = 0, /, **kwargs: Any) -> Any:
        if isinstance(x, GuppyObject):
            return x.__int__(**kwargs)
        return builtins.int(x, **kwargs)


def len(x: Any) -> Any:
    if isinstance(x, GuppyObject | GuppyStructObject):
        return x.__len__()
    return builtins.len(x)


def mock_builtins(f: Callable[..., Any]) -> None:
    f.__globals__.update({"float": float, "int": int, "len": len})
