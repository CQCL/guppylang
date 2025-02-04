from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned

from guppylang.std.quantum import qubit


def test_unpack_array(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def main(qs: array[qubit, 3] @ owned) -> tuple[qubit, qubit, qubit]:
        q1, q2, q3 = qs
        return q1, q2, q3

    validate(module.compile())


def test_unpack_starred(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def main(
        qs: array[qubit, 10] @ owned,
    ) -> tuple[qubit, qubit, qubit, qubit, qubit, qubit, array[qubit, 4]]:
        q1, q2, *qs, q3 = qs
        [q4, *qs] = qs
        *qs, q5, q6 = qs
        [*qs] = qs
        return q1, q2, q3, q4, q5, q6, qs

    validate(module.compile())


def test_unpack_starred_empty(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def main(qs: array[qubit, 2] @ owned) -> tuple[qubit, array[qubit, 0], qubit]:
        q1, *empty, q2 = qs
        return q1, empty, q2

    validate(module.compile())


def test_unpack_big_iterable(validate):
    # Test that the compile-time doesn't scale with the size of the unpacked iterable
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def main(qs: array[qubit, 1000] @ owned) -> tuple[qubit, array[qubit, 998], qubit]:
        q1, *qs, q2 = qs
        return q1, qs, q2

    validate(module.compile())


def test_unpack_range(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        [_, x, *_, y, _] = range(10)
        return x + y

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=9)


def test_unpack_tuple_starred(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> array[int, 2]:
        x, *ys, z = 1, 2, 3, 4
        return ys

    validate(module.compile())


def test_unpack_nested(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main(
        xs: array[array[array[int, 5], 10], 20] @ owned,
    ) -> tuple[
        array[int, 5],  # x
        int,  # y
        array[int, 3],  # z
        array[array[int, 5], 8],  # a
        array[array[array[int, 5], 10], 18],  # b
        array[array[int, 5], 10],  # c
    ]:
        (x, [y, *z, _], *a), *b, c = xs
        return x, y, z, a, b, c

    validate(module.compile())


def test_left_to_right(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def left() -> int:
        [x, x, *_] = range(10)
        return x

    @guppy(module)
    def right() -> int:
        [*_, x, x] = range(10)
        return x

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, fn_name="left", expected=1)
    run_int_fn(compiled, fn_name="right", expected=9)
