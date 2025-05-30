from guppylang import GuppyModule, guppy
from guppylang.std.collections import (
    Stack,
    empty_stack,
    PriorityQueue,
    empty_priority_queue,
    pq_len,
    pq_push,
    pq_pop,
    pq_peek,
)


def test_stack(validate, run_int_fn) -> None:
    module = GuppyModule("test")
    module.load(Stack, empty_stack)

    @guppy(module)
    def main() -> int:
        stack: Stack[int, 10] = empty_stack()
        for i in range(10):
            stack = stack.push(i)
        s = 0
        i = 1
        while len(stack) > 0:
            x, stack = stack.pop()
            s += x * i
            i += 1
        return s

    compiled = module.compile()
    validate(compiled)
    run_int_fn(
        compiled, sum((i + 1) * x for i, x in enumerate(reversed(list(range(10)))))
    )


def test_priority_queue_basic(validate, run_int_fn) -> None:
    """Test basic priority queue operations."""
    module = GuppyModule("test_pq_basic")
    module.load(PriorityQueue, empty_priority_queue, pq_len, pq_push, pq_pop, pq_peek)

    @guppy(module)
    def main() -> int:
        pq: PriorityQueue[int, 5] = empty_priority_queue()

        # Test empty queue
        if pq_len(pq) != 0:
            return -1

        # Test single element
        pq = pq_push(pq, 42, 10)
        if pq_len(pq) != 1:
            return -2

        # Test peek
        priority, value, pq2 = pq_peek(pq)
        if priority != 10 or value != 42:
            return -3

        # Test pop
        priority, value, pq = pq_pop(pq)
        if priority != 10 or value != 42 or pq_len(pq) != 0:
            return -4

        return 100

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, 100)


def test_priority_queue_ordering(validate, run_int_fn) -> None:
    """Test priority ordering - highest priority first."""
    module = GuppyModule("test_pq_order")
    module.load(PriorityQueue, empty_priority_queue, pq_push, pq_pop)

    @guppy(module)
    def main() -> int:
        pq: PriorityQueue[int, 5] = empty_priority_queue()

        # Add elements: values with priorities (10,1), (20,3), (30,2)
        pq = pq_push(pq, 10, 1)  # Low priority
        pq = pq_push(pq, 20, 3)  # High priority
        pq = pq_push(pq, 30, 2)  # Medium priority

        # Should pop in order: 20(3), 30(2), 10(1)
        priority, value, pq = pq_pop(pq)  # Should be 20
        if value != 20:
            return -1

        priority, value, pq = pq_pop(pq)  # Should be 30
        if value != 30:
            return -2

        priority, value, pq = pq_pop(pq)  # Should be 10
        if value != 10:
            return -3

        return 60  # Sum of values

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, 60)


def test_priority_queue_stress(validate, run_int_fn) -> None:
    """Test with multiple elements to verify heap property."""
    module = GuppyModule("test_pq_stress")
    module.load(PriorityQueue, empty_priority_queue, pq_len, pq_push, pq_pop)

    @guppy(module)
    def main() -> int:
        pq: PriorityQueue[int, 10] = empty_priority_queue()

        # Add elements with various priorities
        pq = pq_push(pq, 1, 5)
        pq = pq_push(pq, 2, 10)  # Highest
        pq = pq_push(pq, 3, 3)
        pq = pq_push(pq, 4, 8)
        pq = pq_push(pq, 5, 1)  # Lowest

        if pq_len(pq) != 5:
            return -1

        # Pop all and ensure decreasing priority order
        last_priority = 11  # Higher than any we added
        s = 0

        for i in range(5):
            priority, value, pq = pq_pop(pq)
            if priority > last_priority:
                return -2  # Not in correct order
            last_priority = priority
            s += value

        if pq_len(pq) != 0:
            return -3

        return s  # Should be 15 (sum of all values)

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, 15)