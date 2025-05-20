from __future__ import annotations

from typing import Generic, no_type_check

from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned, panic
from guppylang.std.option import Option, nothing, some

T = guppy.type_var("T", copyable=False, droppable=False)
TCopyable = guppy.type_var("TCopyable", copyable=True, droppable=False)
MAX_SIZE = guppy.nat_var("MAX_SIZE")


@guppy.struct
class Stack(Generic[T, MAX_SIZE]):  # type: ignore[misc]
    """A last-in-first-out (LIFO) growable collection of values.

    To ensure static allocation, the stack maximum stack size must be specified in
    advance and is tracked in the type. For example, the `Stack[int, 10]` is a stack
    that can hold at most 10 integers.

    Use `empty_stack` to construct a new stack.
    """

    #: Underlying buffer holding the stack elements.
    #:
    #: INVARIANT: All array elements up to and including index `self.end - 1` are
    #: `option.some` variants and all further ones are `option.nothing`.
    buf: array[Option[T], MAX_SIZE]  # type: ignore[valid-type, type-arg]

    #: Index of the next free index in `self.buf`.
    end: int

    @guppy
    @no_type_check
    def __len__(self: Stack[T, MAX_SIZE]) -> int:
        """Returns the number of elements currently stored in the stack."""
        return self.end

    @guppy
    @no_type_check
    def push(self: Stack[T, MAX_SIZE] @ owned, elem: T @ owned) -> Stack[T, MAX_SIZE]:
        """Adds an element to the top of the stack.

        Panics if the stack has already reached its maximum size.
        """
        if self.end >= MAX_SIZE:
            panic("Stack.push: max size reached")
        self.buf[self.end].swap(some(elem)).unwrap_nothing()
        return Stack(self.buf, self.end + 1)

    @guppy
    @no_type_check
    def pop(self: Stack[T, MAX_SIZE] @ owned) -> tuple[T, Stack[T, MAX_SIZE]]:
        """
        Removes the top element from the stack and returns it.

        Panics if the stack is empty.
        """
        if self.end <= 0:
            panic("Stack.pop: stack is empty")
        elem = self.buf[self.end - 1].take().unwrap()
        return elem, Stack(self.buf, self.end - 1)

    @guppy
    @no_type_check
    def peek(
        self: Stack[TCopyable, MAX_SIZE] @ owned,
    ) -> tuple[TCopyable, Stack[TCopyable, MAX_SIZE]]:
        """Returns a copy of the top element of the stack without removing it.

        Panics if the stack is empty.

        Note that this operation is only allowed if the stack elements are copyable.
        """
        if self.end <= 0:
            panic("Stack.peel: stack is empty")
        elem = self.buf[self.end - 1].unwrap()
        return elem, Stack(self.buf, self.end)


@guppy
@no_type_check
def empty_stack() -> Stack[T, MAX_SIZE]:
    """Constructs a new empty stack."""
    buf = array(nothing[T]() for _ in range(MAX_SIZE))
    return Stack(buf, 0)
