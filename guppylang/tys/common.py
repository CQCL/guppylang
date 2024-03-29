from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ToHugr(ABC, Generic[T]):
    """Abstract base class for objects that have a Hugr representation."""

    @abstractmethod
    def to_hugr(self) -> T:
        """Computes the Hugr representation of the object."""


class Visitor(ABC):
    """Abstract base class for a type visitor that transforms types."""

    @abstractmethod
    def visit(self, arg: Any, /) -> bool:
        """This method is called for each visited type.

        Return `False` to continue the recursive descent.
        """


class Transformer(ABC):
    """Abstract base class for a type visitor that transforms types."""

    @abstractmethod
    def transform(self, arg: Any, /) -> Any | None:
        """Transforms the object.

        Return a transformed type or `None` to continue the recursive visit.
        """


class Visitable(ABC):
    """Abstract base class for objects that can be recursively visited."""

    @abstractmethod
    def visit(self, visitor: Visitor, /) -> None:
        """Accepts a visitor on the object.

        Implementors of this method should first invoke the visitor on the object
        itself. If the visitor doesn't handle the object, the visitor should be passed
        to all relevant members of the object.
        """


class Transformable(Visitable, ABC, Generic[T]):
    """Abstract base class for objects that can be recursively transformed."""

    @abstractmethod
    def transform(self, transformer: Transformer, /) -> T:
        """Accepts a transformer on the object.

        Implementors of this method should first invoke the transformer on the object
        itself. If the visitor doesn't handle the object, the visitor should be used to
        transform all relevant members of the object.
        """
