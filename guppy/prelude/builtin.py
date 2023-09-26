"""Guppy standard extension for builtin types and methods.

Instance methods for builtin types are defined in their own files
"""

import ast
from typing import Union, Literal, Any

from pydantic import BaseModel

from guppy.compiler_base import CallCompiler
from guppy.error import GuppyError, GuppyTypeError
from guppy.expression import check_num_args
from guppy.extension import GuppyExtension, NotImplementedCompiler
from guppy.guppy_types import SumType, TupleType, GuppyType, FunctionType
from guppy.hugr import tys, val
from guppy.hugr.hugr import OutPortV
from guppy.hugr.tys import TypeBound


extension = GuppyExtension("builtin", [])


# We have to define and register the bool type by hand since we want it to be a
# subclass of `SumType`


class BoolType(SumType):
    """The type of booleans."""

    linear = False
    name = "bool"

    def __init__(self) -> None:
        # Hugr bools are encoded as Sum((), ())
        super().__init__([TupleType([]), TupleType([])])

    @staticmethod
    def build(*args: GuppyType, node: Union[ast.Name, ast.Subscript]) -> GuppyType:
        if len(args) > 0:
            raise GuppyError("Type `bool` is not parametric", node)
        return BoolType()

    def __str__(self) -> str:
        return "bool"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, BoolType)


extension.register_type("bool", BoolType)


INT_WIDTH = 6  # 2^6 = 64 bit

IntType: type[GuppyType] = extension.new_type(
    name="int",
    hugr_repr=tys.Opaque(
        extension="arithmetic.int.types",
        id="int",
        args=[tys.BoundedNatArg(n=INT_WIDTH)],
        bound=TypeBound.Copyable,
    ),
)

FloatType: type[GuppyType] = extension.new_type(
    name="float",
    hugr_repr=tys.Opaque(
        extension="arithmetic.float.types",
        id="float64",
        args=[],
        bound=TypeBound.Copyable,
    ),
)

StringType: type[GuppyType] = extension.new_type(
    name="str",
    hugr_repr=tys.Opaque(
        extension="TODO",  # String hugr extension doesn't exist yet
        id="string",
        args=[],
        bound=TypeBound.Copyable,
    ),
)


class ConstIntS(BaseModel):
    """Hugr representation of signed integers in the arithmetic extension."""

    c: Literal["ConstIntS"] = "ConstIntS"
    log_width: int
    value: int


class ConstF64(BaseModel):
    """Hugr representation of floats in the arithmetic extension."""

    c: Literal["ConstF64"] = "ConstF64"
    value: float


def bool_value(b: bool) -> val.Value:
    """Returns the Hugr representation of a boolean value."""
    return val.Sum(tag=int(b), value=val.Tuple(vs=[]))


def int_value(i: int) -> val.Value:
    """Returns the Hugr representation of an integer value."""
    return val.Prim(val=val.ExtensionVal(c=(ConstIntS(log_width=INT_WIDTH, value=i),)))


def float_value(f: float) -> val.Value:
    """Returns the Hugr representation of a float value."""
    return val.Prim(val=val.ExtensionVal(c=(ConstF64(value=f),)))


class CallableCompiler(CallCompiler):
    """Call compiler for the builtin `callable` function"""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        check_num_args(1, len(args), self.node)
        [arg] = args
        is_callable = (
            isinstance(arg.ty, FunctionType)
            or self.globals.get_instance_func(arg.ty, "__call__") is not None
        )
        const = self.graph.add_constant(bool_value(is_callable), BoolType()).out_port(0)
        return [self.graph.add_load_constant(const).out_port(0)]


class BuiltinCompiler(CallCompiler):
    """Call compiler for builtin functions that call out to dunder instance methods"""

    dunder_name: str
    num_args: int

    def __init__(self, dunder_name: str, num_args: int = 1):
        self.dunder_name = dunder_name
        self.num_args = num_args

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        check_num_args(self.num_args, len(args), self.node)
        [arg] = args
        func = self.globals.get_instance_func(arg.ty, self.dunder_name)
        if func is None:
            raise GuppyTypeError(
                f"Builtin function `{self.func.name}` is not defined for argument of "
                "type `{arg.ty}`",
                self.node.args[0] if isinstance(self.node, ast.Call) else self.node,
            )
        return func.compile_call(args, self.dfg, self.graph, self.globals, self.node)


extension.new_func("abs", BuiltinCompiler("__abs__"), higher_order_value=False)
extension.new_func("bool", BuiltinCompiler("__bool__"), higher_order_value=False)
extension.new_func("callable", CallableCompiler(), higher_order_value=False)
extension.new_func("divmod", BuiltinCompiler("__divmod__"), higher_order_value=False)
extension.new_func("float", BuiltinCompiler("__float__"), higher_order_value=False)
extension.new_func("int", BuiltinCompiler("__int__"), higher_order_value=False)
extension.new_func("len", BuiltinCompiler("__len__"), higher_order_value=False)
extension.new_func(
    "pow", BuiltinCompiler("__pow__", num_args=2), higher_order_value=False
)
extension.new_func("repr", BuiltinCompiler("__repr__"), higher_order_value=False)
extension.new_func("round", BuiltinCompiler("__round__"), higher_order_value=False)
extension.new_func("str", BuiltinCompiler("__str__"), higher_order_value=False)


# Python builtins that are not supported yet
extension.new_func("aiter", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("all", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("anext", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("any", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("ascii", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("aiter", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("bin", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("breakpoint", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("bytearray", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("bytes", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("chr", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("classmethod", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("compile", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("complex", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("delattr", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("dict", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("dir", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("enumerate", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("eval", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("exec", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("filter", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("format", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("frozenset", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("getattr", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("globals", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("hasattr", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("hash", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("help", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("hex", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("id", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("input", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("isinstance", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("issubclass", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("iter", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("list", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("locals", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("map", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("max", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("memoryview", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("min", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("next", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("object", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("oct", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("open", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("ord", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("print", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("property", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("range", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("reversed", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("set", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("setattr", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("slice", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("sorted", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("staticmethod", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("sum", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("super", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("tuple", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("type", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("vars", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("zip", NotImplementedCompiler(), higher_order_value=False)
extension.new_func("__import__", NotImplementedCompiler(), higher_order_value=False)
