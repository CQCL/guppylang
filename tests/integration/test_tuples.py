from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit


def test_indexing(validate, run_int_fn):
    @guppy
    def main() -> int:
        t = (0.2, 2, 2.2)
        x = t[1]
        return x

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 2)

def test_indexing_input(validate):
    @guppy
    def main(t: tuple[int, float]) -> int:
        return t[0]

    validate(guppy.compile(main))


def test_indexing_drop(validate, run_int_fn):
    @guppy
    def main() -> int:
        return (1, 2, 3)[2]

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 3)


def test_indexing_nesting(validate, run_int_fn):
    @guppy
    def main() -> int:
        t = (1, 2, (3, 4))
        return t[2][0]

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 3)


def test_indexing_struct(validate, run_int_fn):
    @guppy.struct
    class S:
        t: tuple[array[tuple[int, int], 1], int]

    @guppy
    def main() -> int:
        s = S((array((1, 2)), 3))
        return s.t[0][0][0] + 1

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 2)


def test_rest_after_use(validate):
    @guppy.declare
    def use(x: qubit @ owned) -> None: ...

    @guppy
    def main() -> int:
        t = (1, qubit())
        use(t[1])
        return t[0]

    validate(guppy.compile(main))
