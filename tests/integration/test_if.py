import pytest

from guppy.decorator import guppy


def test_if_no_else(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        return y

    validate(foo)


def test_if_else(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        else:
            y -= 1
        return y

    validate(foo)


def test_if_elif(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        elif y > 4:
            y *= 7
        return y

    validate(foo)


def test_if_elif_else(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        elif y > 4:
            y *= 7
        else:
            y = 1337
        return y

    validate(foo)


def test_if_expr(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        return y + 1 if x else 42

    validate(foo)


def test_if_expr_nested(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        a = y + 1 if x else y * y if 0 < y <= 10 else 42
        b = a if a < 5 or (not x and -7 >= a > 42) else -a
        return a if a > b else b

    validate(foo)


def test_if_expr_tuple(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> (int, int, int):
        t = (y + 1 if x else 42), 8, (y * 2 if x else 64)
        return t

    validate(foo)


def test_if_expr_assign_both(validate):
    @guppy(compile=True)
    def foo(x: bool) -> int:
        (z := 5) if x else (z := 42)
        return z

    validate(foo)


def test_if_expr_assign_cond(validate):
    @guppy(compile=True)
    def foo(x: bool) -> bool:
        return z if (z := x) else False

    validate(foo)


def test_if_expr_reassign(validate):
    @guppy(compile=True)
    def foo(x: bool) -> int:
        y = 5
        (y := 1) if x else 6
        6 if x else (y := 2)
        (y := 3) if x else (y := 4)
        return y

    validate(foo)


def test_if_expr_reassign_cond(validate):
    @guppy(compile=True)
    def foo(x: bool) -> int:
        y = 5
        return y if (y := 42) > 5 else 64 if x else y

    validate(foo)


def test_if_expr_double_type_change(validate):
    @guppy(compile=True)
    def foo(x: bool) -> int:
        y = 4
        (y := 1) if (y := x) else (y := 6)
        return y

    validate(foo)


def test_if_return(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        if x:
            return y
        y *= 32
        return y

    validate(foo)


def test_else_return(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        if x:
            y += 3
        else:
            y //= 4
            return y
        return y

    validate(foo)


def test_both_return(validate):
    @guppy(compile=True)
    def foo(x: bool, y: int) -> int:
        if x:
            y += 3
            return y
        else:
            y //= 4
            return y

    validate(foo)


def test_nested_return(validate):
    @guppy(compile=True)
    def foo(x: int, y: int) -> int:
        if x > 5:
            if y == 4:
                x *= 4
            else:
                return y
        return x

    validate(foo)


def test_return_defined1(validate):
    @guppy(compile=True)
    def foo(x: int, y: int) -> int:
        if x > 5:
            return y
        else:
            z = 5
        return z

    validate(foo)


def test_return_defined2(validate):
    @guppy(compile=True)
    def foo(x: int) -> int:
        if x > 5:
            z = 45
        else:
            return x
        return z

    validate(foo)


def test_break_different_types1(validate):
    @guppy(compile=True)
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = False
                break
            else:
                z = 8
            z += x
        return 0

    validate(foo)


def test_break_different_types2(validate):
    @guppy(compile=True)
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = 8
            else:
                z = True
                break
            z += x
        return 0

    validate(foo)


@pytest.mark.skip("Known bug")
def test_continue_different_types1(validate):
    @guppy(compile=True)
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = False
                continue
            else:
                z = 8
            z += x
        return z

    validate(foo)


@pytest.mark.skip("Known bug")
def test_continue_different_types2(validate):
    @guppy(compile=True)
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = 8
            else:
                z = False
                continue
            z += x
        return z

    validate(foo)
