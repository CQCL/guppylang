from typing import Any

from typing_extensions import Self

ERROR_MSG = (
    "List is immutable. Consider calling `copy()` to obtain a mutable copy of this list"
)


class frozenlist(list):  # type: ignore[type-arg]
    """An immutable list subclass.

    Raises a `TypeError` for any operation that would mutate the list.
    """

    def append(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def copy(self) -> Any:
        return list(self)

    def clear(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def extend(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def insert(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(ERROR_MSG)

    def remove(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def reverse(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def sort(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def __delitem__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(ERROR_MSG)

    def __iadd__(self, *args: Any, **kwargs: Any) -> Self:  # type: ignore[misc]
        raise TypeError(ERROR_MSG)

    def __imul__(self, *args: Any, **kwargs: Any) -> Self:  # type: ignore[misc]
        raise TypeError(ERROR_MSG)

    def __setitem__(self, key: Any, value: Any) -> Any:
        raise TypeError(ERROR_MSG)
