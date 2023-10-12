from guppy.compiler import guppy
from guppy.hugr import ops


def test_id(validate):
    @guppy
    def identity(x: int) -> int:
        return x

    validate(identity)


def test_void(validate):
    @guppy
    def void() -> None:
        return

    validate(void)


def test_copy(validate):
    @guppy
    def copy(x: int) -> (int, int):
        return x, x

    validate(copy)


def test_discard(validate):
    @guppy
    def discard(x: int) -> None:
        return

    validate(discard)


def test_implicit_return(validate):
    @guppy
    def ret() -> None:
        pass

    validate(ret)


def test_assign(validate):
    @guppy
    def foo(x: bool) -> bool:
        y = x
        return y

    validate(foo)


def test_assign_expr(validate):
    @guppy
    def foo(x: bool) -> bool:
        (y := x)
        return y

    validate(foo)


def test_func_def_name():
    @guppy
    def func_name() -> None:
        return

    [def_op] = [n.op for n in func_name.nodes() if isinstance(n.op, ops.FuncDefn)]
    assert def_op.name == "func_name"


def test_func_decl_name():
    @guppy
    def func_name() -> None:
        ...

    [def_op] = [n.op for n in func_name.nodes() if isinstance(n.op, ops.FuncDecl)]
    assert def_op.name == "func_name"
