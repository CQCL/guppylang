import builtins
import re

import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


def test_float(validate):
    module = GuppyModule("test")

    @guppy.comptime(module)
    def test(x: int) -> float:
        # Make sure that the mocked float is indistinguishable from the real deal
        assert isinstance(4.0, float)
        assert isinstance(4.0, builtins.float)
        assert isinstance(float(4), float)
        assert isinstance(float(4), builtins.float)
        assert isinstance(float, type)
        assert issubclass(float, float)
        assert issubclass(float, builtins.float)
        assert issubclass(builtins.float, float)
        assert float == builtins.float
        assert not float != builtins.float
        assert float.__name__ == builtins.float.__name__
        assert float.__qualname__ == builtins.float.__qualname__

        for v in (True, False, -42, 1.5, "-0.42"):
            assert float(v) == builtins.float(v)

        # But they are not identical
        assert float is not builtins.float

        # In particular, `builtins.float` doesn't work for GuppyObjects, but our mocked
        # version does
        err = re.escape("GuppyObject.__float__ returned non-float (type GuppyObject)")
        with pytest.raises(TypeError, match=err):
            builtins.float(x)
        return float(x)

    validate(module.compile())


def test_int(validate):
    module = GuppyModule("test")

    @guppy.comptime(module)
    def test(x: float) -> int:
        # Make sure that the mocked int is indistinguishable from the real deal
        assert isinstance(4, int)
        assert isinstance(4, builtins.int)
        assert isinstance(int(4.0), int)
        assert isinstance(int(4.0), builtins.int)
        assert isinstance(int, type)
        assert issubclass(int, int)
        assert issubclass(int, builtins.int)
        assert issubclass(builtins.int, int)
        assert issubclass(bool, int)
        assert int == builtins.int
        assert not int != builtins.int
        assert int.__name__ == builtins.int.__name__
        assert int.__qualname__ == builtins.int.__qualname__

        for v in (True, False, 42, "-123"):
            assert int(v) == builtins.int(v)

        # But they are not identical
        assert int is not builtins.int

        # In particular, `builtins.int` doesn't work for GuppyObjects, but our mocked
        # version does
        err = re.escape("__int__ returned non-int (type GuppyObject)")
        with pytest.raises(TypeError, match=err):
            builtins.int(x)
        return int(x)

    validate(module.compile())


def test_len(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class S:
        x: int

        @guppy(module)
        def __len__(self: "S") -> int:
            return self.x

    @guppy.comptime(module)
    def test(xs: array[int, 10]) -> int:
        # Make sure that the mocked len is indistinguishable from the real deal
        assert len([1, 2, 3, 4, 5]) == 5
        assert len({1, 2}) == 2
        assert len({1: 1}) == 1
        assert len(()) == 0
        assert len(xs) == 10

        # But they are not identical
        assert len != builtins.len
        assert len is not builtins.len

        # In particular, `builtins.len` doesn't work for GuppyObjects, but our mocked
        # version does
        s = S(100)
        err = re.escape("object of type 'GuppyStructObject' has no len()")
        with pytest.raises(TypeError, match=err):
            builtins.len(s)
        return len(s)

    validate(module.compile())

