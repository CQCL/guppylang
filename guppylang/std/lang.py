"""Provides Python objects for builtin language keywords."""

from typing import Any

from typing_extensions import deprecated


def comptime(*args: Any) -> Any:
    """Function to tag compile-time evaluated Python expressions in a Guppy context.

    This function acts like the identity when execute in a Python context.
    """
    return tuple(args)


#: Deprecated alias for `comptime` expressions
py = deprecated("Use `comptime` instead")(comptime)


class _Owned:
    """Dummy class to support `@owned` annotations."""

    def __rmatmul__(self, other: Any) -> Any:
        return other


owned = _Owned()
