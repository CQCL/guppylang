from guppylang import GuppyModule, guppy
from guppylang.std.builtins import frozenarray, panic, py


def test_len(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: frozenarray[int, 42]) -> int:
        return len(xs)

    @guppy(module)
    def main() -> int:
        xs = py(list(range(42)))
        return foo(xs)

    compiled = module.compile()
    validate(compiled)
    # TODO: Enable execution test once LLVM lowering is done:
    #  https://github.com/CQCL/hugr/issues/1973
    #run_int_fn(compiled, 42)


def test_subscript(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: frozenarray[int, 42]) -> int:
        return xs[10] + xs[10]

    @guppy(module)
    def main() -> int:
        xs = py(list(range(42)))
        return foo(xs)

    compiled = module.compile()
    validate(compiled)
    # TODO: Enable execution test once LLVM lowering is done:
    #  https://github.com/CQCL/hugr/issues/1973
    #run_int_fn(compiled, 20)


def test_iter(validate):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: frozenarray[int, 42]) -> int:
        s = 0
        for x in xs:
            s += x
        return s

    @guppy(module)
    def main() -> int:
        xs = py(list(range(42)))
        return foo(xs)

    compiled = module.compile()
    validate(compiled)
    # TODO: Enable execution test once LLVM lowering is done:
    #  https://github.com/CQCL/hugr/issues/1973
    #run_int_fn(compiled, sum(range(42)))


def test_alias(validate):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: frozenarray[int, 42]) -> int:
        ys = xs
        return xs[0] + ys[1]

    @guppy(module)
    def main() -> int:
        xs = py(list(range(42)))
        return foo(xs)

    compiled = module.compile()
    validate(compiled)
    # TODO: Enable execution test once LLVM lowering is done:
    #  https://github.com/CQCL/hugr/issues/1973
    #run_int_fn(compiled, 1)


def test_mutable_copy(validate):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: frozenarray[int, 42]) -> int:
        ys = xs.mutable_copy()
        s = 0
        for i in range(42):
            if xs[i] != ys[i]:
                panic("Mismatch")
            s += xs[i]
            s += ys[i]
        return s

    @guppy(module)
    def main() -> int:
        xs = py(list(range(42)))
        return foo(xs)

    compiled = module.compile()
    validate(compiled)
    # TODO: Enable execution test once LLVM lowering is done:
    #  https://github.com/CQCL/hugr/issues/1973
    #run_int_fn(compiled, 2 * sum(range(42))


def test_nested_subscript(validate):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: frozenarray[frozenarray[int, 2], 2]) -> int:
        return xs[0][0] + xs[0][1] + xs[1][0] + xs[1][1]

    @guppy(module)
    def main() -> int:
        xs = py([[1, 2], [3, 4]])
        return foo(xs)

    compiled = module.compile()
    validate(compiled)
    # TODO: Enable execution test once LLVM lowering is done:
    #  https://github.com/CQCL/hugr/issues/1973
    #run_int_fn(compiled, 1 + 2 + 3 + 4)


def test_nested_iter(validate):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xss: frozenarray[frozenarray[int, 10], 42]) -> int:
        s = 0
        for xs in xss:
            for x in xs:
                s += x
        return s

    xss = [[i * j for j in range(10)] for i in range(42)]

    @guppy(module)
    def main() -> int:
        return foo(py(xss))

    compiled = module.compile()
    validate(compiled)
    # TODO: Enable execution test once LLVM lowering is done:
    #  https://github.com/CQCL/hugr/issues/1973
    #run_int_fn(compiled, sum([sum(xs) for xs in xss]))


def test_nested_struct(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class S:
        xs: frozenarray[int, 10]
        y: int

    @guppy(module)
    def foo(xss: frozenarray[S, 42]) -> int:
        s = xss[0].y + xss[0].xs[0]
        for ss in xss:
            for x in ss.xs:
                s += x
        return s

    validate(module.compile())

