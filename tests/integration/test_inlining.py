from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

from guppylang.std.quantum import qubit, discard_array
import guppylang.std.quantum as quantum

# TODO: Remove this file
def test_inlining1(validate, run_int_fn):
    module = GuppyModule("test")


    @guppy(module)
    def main() -> int:
        xs = array(1, 2, 4)
        ys = array(8, 16)
        i = xs[0] 
        j = xs[1]
        k = ys[0]
        return i + j + k


    # print(module.compile_hugr().render_dot())

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=11)


# TODO: Remove this file
def test_inlining2(validate, run_int_fn):
    module = GuppyModule("test")


    @guppy(module)
    def main() -> int:
        xs = array(1)
        ys = array(1)
        xs[0] = 2
        ys[0] = 4
        return xs[0] + ys[0]


    # print(module.compile_hugr().render_dot())

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=6)


def test_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def foo(arr: array[qubit, 2]) -> None:
        return
    
    @guppy(module)
    def bar(q: qubit) -> None:
        return

    @guppy(module)
    def main() -> None:
        xs = array(qubit(), qubit())
        foo(xs)
        bar(xs[0])
        discard_array(xs)

    # print(module.compile_hugr().render_dot())

    compiled = module.compile()
    validate(compiled)


def test_multiple_functions(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def first(arr: array[int, 2]) -> int:
        return arr[0]
    
    @guppy(module)
    def second(arr: array[int, 2]) -> int:
        return arr[1]


    @guppy(module)
    def main() -> int:
        xs = array(1, 2)
        return first(xs) + second(xs)

    print(module.compile_hugr().render_dot())
    assert False

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=3)



