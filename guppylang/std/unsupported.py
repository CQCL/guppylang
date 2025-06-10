# mypy: disable-error-code="empty-body, no-untyped-def"
"""Python builtins that are not supported yet"""

from guppylang.decorator import guppy
from guppylang.std._internal.checker import UnsupportedChecker


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def aiter(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def all(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def anext(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def any(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def bin(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def breakpoint(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def bytearray(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def bytes(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def chr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def classmethod(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def compile(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def complex(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def delattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def dict(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def dir(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def enumerate(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def eval(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def exec(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def filter(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def format(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def frozenset(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def getattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def globals(): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def hasattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def hash(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def help(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def hex(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def id(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def input(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def isinstance(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def issubclass(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def iter(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def locals(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def map(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def max(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def memoryview(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def min(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def next(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def object(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def oct(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def open(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def ord(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def print(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def property(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def repr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def reversed(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def set(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def setattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def slice(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def sorted(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def staticmethod(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def sum(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def super(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def type(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def vars(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def zip(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def __import__(x): ...
