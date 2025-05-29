# mypy: disable-error-code="empty-body, no-untyped-def"
"""Python builtins that are not supported yet"""

from pathlib import Path

from guppylang.decorator import ModuleIdentifier, guppy
from guppylang.std import builtins
from guppylang.std._internal.checker import UnsupportedChecker

_builtins_module = guppy.get_module(
    ModuleIdentifier(Path(builtins.__file__), "builtins", builtins)
)


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def aiter(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def all(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def anext(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def any(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def bin(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def breakpoint(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def bytearray(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def bytes(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def chr(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def classmethod(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def compile(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def complex(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def delattr(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def dict(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def dir(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def enumerate(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def eval(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def exec(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def filter(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def format(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def forozenset(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def getattr(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def globals(): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def hasattr(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def hash(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def help(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def hex(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def id(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def input(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def isinstance(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def issubclass(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def iter(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def locals(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def map(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def max(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def memoryview(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def min(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def next(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def object(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def oct(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def open(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def ord(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def print(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def property(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def repr(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def reversed(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def set(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def setattr(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def slice(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def sorted(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def staticmethod(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def sum(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def super(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def type(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def vars(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def zip(x): ...


@guppy.custom(
    checker=UnsupportedChecker(), higher_order_value=False, module=_builtins_module
)
def __import__(x): ...
