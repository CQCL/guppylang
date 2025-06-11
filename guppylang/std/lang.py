"""Provides Python objects for builtin language keywords."""

from typing import Any

from typing_extensions import deprecated


class _Comptime:
    """Dummy class to support `@comptime` annotations and `comptime(...)` expressions"""

    def __call__(self, *args: Any) -> Any:
        return tuple(args)

    def __rmatmul__(self, other: Any) -> Any:
        # This method is to make the Python interpreter happy with @comptime at runtime
        return other


#: Function to tag compile-time evaluated Python expressions in a Guppy context.
#:
#: This function acts like the identity when execute in a Python context.
comptime = _Comptime()


#: Deprecated alias for `comptime` expressions
py = deprecated("Use `comptime` instead")(comptime)


class _Owned:
    """Dummy class to support `@owned` annotations."""

    def __rmatmul__(self, other: Any) -> Any:
        return other


owned = _Owned()
