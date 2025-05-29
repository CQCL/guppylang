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

    To ensure static allocation, the maximum stack size must be specified in advance and
    is tracked in the type. For example, the `Stack[int, 10]` is a stack that can hold
    at most 10 integers.

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


@guppy.struct
class PriorityQueue(Generic[T, MAX_SIZE]):  # type: ignore[misc]
    """A priority queue implemented as a binary max-heap.

    Elements with higher priority values are served first. The maximum queue size
    must be specified in advance and is tracked in the type. For example,
    `PriorityQueue[str, 20]` is a priority queue that can hold at most 20 strings.

    Use `empty_priority_queue` to construct a new priority queue.
    """

    #: Underlying buffer holding priority-element pairs as a binary heap.
    #: INVARIANT: All array elements up to and including index `self.size - 1` are
    #: `option.some` variants and all further ones are `option.nothing`.
    buf: array[Option[tuple[int, T]], MAX_SIZE]  # type: ignore[valid-type, type-arg]

    #: Number of elements currently in the queue.
    size: int


@guppy
@no_type_check
def pq_len(self: PriorityQueue[T, MAX_SIZE]) -> int:
    """Returns the number of elements currently stored in the priority queue."""
    return self.size


@guppy
@no_type_check
def _pq_parent_index(index: int) -> int:
    """Returns the parent index of node at index i."""
    return (index - 1) // 2


@guppy
@no_type_check
def _pq_left_child_index(index: int) -> int:
    """Returns the left child index of node at index i."""
    return 2 * index + 1


@guppy
@no_type_check
def _pq_right_child_index(index: int) -> int:
    """Returns the right child index of node at index i."""
    return 2 * index + 2


@guppy
@no_type_check
def _pq_bubble_up(
    self: PriorityQueue[T, MAX_SIZE] @ owned, index: int
) -> PriorityQueue[T, MAX_SIZE]:
    """Maintains max-heap property by bubbling element at index upward."""
    if index <= 0:
        return self

    parent_idx = _pq_parent_index(index)
    current_priority = self.buf[index].unwrap()[0]
    parent_priority = self.buf[parent_idx].unwrap()[0]

    if current_priority > parent_priority:
        # Swap with parent
        current_elem = self.buf[index].take().unwrap()
        parent_elem = self.buf[parent_idx].take().unwrap()
        self.buf[index].swap(some(parent_elem)).unwrap_nothing()
        self.buf[parent_idx].swap(some(current_elem)).unwrap_nothing()
        return _pq_bubble_up(self, parent_idx)

    return self


@guppy
@no_type_check
def _pq_bubble_down(
    self: PriorityQueue[T, MAX_SIZE] @ owned, index: int
) -> PriorityQueue[T, MAX_SIZE]:
    """Maintains max-heap property by bubbling element at index downward."""
    left_idx = _pq_left_child_index(index)
    right_idx = _pq_right_child_index(index)
    largest_idx = index

    # Find the largest among current node and its children
    if (
        left_idx < self.size
        and self.buf[left_idx].unwrap()[0] > self.buf[largest_idx].unwrap()[0]
    ):
        largest_idx = left_idx

    if (
        right_idx < self.size
        and self.buf[right_idx].unwrap()[0] > self.buf[largest_idx].unwrap()[0]
    ):
        largest_idx = right_idx

    # If largest is not the current node, swap and continue
    if largest_idx != index:
        current_elem = self.buf[index].take().unwrap()
        largest_elem = self.buf[largest_idx].take().unwrap()
        self.buf[index].swap(some(largest_elem)).unwrap_nothing()
        self.buf[largest_idx].swap(some(current_elem)).unwrap_nothing()
        return _pq_bubble_down(self, largest_idx)

    return self


@guppy
@no_type_check
def pq_push(
    self: PriorityQueue[T, MAX_SIZE] @ owned, value: T @ owned, priority: int
) -> PriorityQueue[T, MAX_SIZE]:
    """Adds an element with the given priority to the queue.

    Panics if the queue has already reached its maximum size.
    """
    if self.size >= MAX_SIZE:
        panic("PriorityQueue.push: max size reached")

    # Insert new element at the end
    self.buf[self.size].swap(some((priority, value))).unwrap_nothing()
    new_queue = PriorityQueue(self.buf, self.size + 1)

    # Bubble up to maintain heap property
    return _pq_bubble_up(new_queue, self.size)


@guppy
@no_type_check
def pq_pop(
    self: PriorityQueue[T, MAX_SIZE] @ owned,
) -> tuple[int, T, PriorityQueue[T, MAX_SIZE]]:
    """Removes and returns the element with the highest priority.

    Returns a tuple of (priority, element, new_queue).
    Panics if the queue is empty.
    """
    if self.size <= 0:
        panic("PriorityQueue.pop: queue is empty")

    # Get the root element (highest priority)
    root_elem = self.buf[0].take().unwrap()
    priority, value = root_elem

    if self.size == 1:
        # Queue becomes empty
        return priority, value, PriorityQueue(self.buf, 0)

    # Move last element to root and bubble down
    last_elem = self.buf[self.size - 1].take().unwrap()
    self.buf[0].swap(some(last_elem)).unwrap_nothing()
    new_queue = PriorityQueue(self.buf, self.size - 1)

    return priority, value, _pq_bubble_down(new_queue, 0)


@guppy
@no_type_check
def pq_peek(
    self: PriorityQueue[TCopyable, MAX_SIZE] @ owned,
) -> tuple[int, TCopyable, PriorityQueue[TCopyable, MAX_SIZE]]:
    """Returns the element with the highest priority without removing it.

    Returns a tuple of (priority, element, queue).
    Panics if the queue is empty.

    Note that this operation is only allowed if the queue elements are copyable.
    """
    if self.size <= 0:
        panic("PriorityQueue.peek: queue is empty")

    priority, value = self.buf[0].unwrap()
    return priority, value, self


@guppy
@no_type_check
def empty_priority_queue() -> PriorityQueue[T, MAX_SIZE]:
    """Constructs a new empty priority queue."""
    buf = array(nothing[tuple[int, T]]() for _ in range(MAX_SIZE))
    return PriorityQueue(buf, 0)
