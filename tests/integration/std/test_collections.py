from guppylang import GuppyModule, guppy
from guppylang.std.collections import Stack, empty_stack


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
    run_int_fn(compiled, sum((i + 1) * x for i, x in enumerate(reversed(list(range(10))))))


