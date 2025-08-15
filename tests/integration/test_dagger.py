import pytest
from guppylang.decorator import guppy
from guppylang.std.quantum import discard, qubit, h
import sys

# TODO (k.hirata)
def test_dagger_1(validate):
    @guppy
    def foo(a: qubit) -> None:
        pass
    @guppy
    def main() -> int:
        a = qubit()
        b = False
        c = 48
        with True:
            if b:
                foo(a)
        # a + 611
        discard(a)
        if b:
            return c - 6
        return 42



    print("  main = ", str(main)[:50], "...")
    with pytest.raises(Exception) as exc_info:
        compiled = main.compile()
        validate(compiled)
        assert (0 == 1)
    tb = exc_info.tb
    sys.excepthook(exc_info.type, exc_info.value.with_traceback(tb), tb)
    compiled = main.compile()
    h = compiled.modules[0]
    # print h.render_dot() to file
    with open("tests/integration/test_dagger_output.dot", "w") as f:
        f.write(h.render_dot().source)
    # print("  dot =\n  ", h.render_dot())
    validate(compiled)
    assert (0 == 1)


# TODO (k.hirata)


# def test_dagger_2(validate):
#     @guppy
#     def main() -> None:
#         a = qubit()
#         b = False
#         c = 48
#         with True:
#             h(a)
#         discard(a)

#     print("  main = ", str(main)[:50], "...")
#     compiled = main.compile()
#     validate(compiled)
#     h = compiled.modules[0]
#     print("  dot =\n  ", h.render_dot())
#     assert (0 == 1)

# # TODO (k.hirata)


# def test_dagger_3(run_int_fn):
#     @guppy
#     def main() -> int:
#         with True:
#             pass
#         return 42

#     run_int_fn(main, 42)

# def test_aaaaaaaaaaaaaaaaaa(validate):
#     @guppy
#     def main(q: qubit) -> qubit:
#         with control(q):
#             pass

#     validate(main.compile())

# def test_as_not_defined(validate):
#     @guppy
#     def main(q: qubit) -> qubit:
#         with dagger as c:
#             return c
#     validate(main.compile())

# def test_return_in_with(validate):
#     @guppy
#     def main() -> None:
#         with dagger:
#             return
#     validate(main.compile())
