"""Guppy standard extension for builtin types and methods.

Instance methods for builtin types are defined in their own files
"""
import ast
from typing import Union, Literal

from pydantic import BaseModel

from guppy.compiler_base import CallCompiler
from guppy.error import GuppyError, GuppyTypeError
from guppy.expression import check_num_args
from guppy.extension import GuppyExtension
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


extension.register_type("bool", BoolType)


def bool_value(b: bool) -> val.Value:
    return val.Sum(tag=int(b), value=val.Tuple(vs=[]))


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


class ConstIntS(BaseModel):
    """Hugr representation of signed integers in the arithmetic extension."""
    c: Literal["ConstIntS"] = "ConstIntS"
    log_width: int
    value: int


class ConstF64(BaseModel):
    """Hugr representation of signed integers in the arithmetic extension."""
    c: Literal["ConstF64"] = "ConstF64"
    value: float


def int_value(i: int) -> val.Value:
    return val.Prim(val=val.ExtensionVal(c=(ConstIntS(log_width=INT_WIDTH, value=i),)))


def float_value(f: float) -> val.Value:
    return val.Prim(val=val.ExtensionVal(c=(ConstF64(value=f),)))


class IdCompiler(CallCompiler):
    """Call compiler for the builtin `id` function"""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        check_num_args(1, len(args), self.node)
        [arg] = args
        return [arg]


class CallableCompiler(CallCompiler):
    """Call compiler for the builtin `callable` function"""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        check_num_args(1, len(args), self.node)
        [arg] = args
        is_callable = isinstance(arg.ty, FunctionType) or self.globals.get_instance_func(arg.ty, "__call__") is not None
        const = self.graph.add_constant(bool_value(is_callable), BoolType()).out_port(0)
        return [self.graph.add_load_constant(const).out_port(0)]


class BuiltinCompiler(CallCompiler):
    name: str
    dunder_name: str

    def __init__(self, name: str, dunder_name: str):
        self.name = name
        self.dunder_name = dunder_name

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        check_num_args(1, len(args), self.node)
        [arg] = args
        func = self.globals.get_instance_func(arg.ty, self.dunder_name)
        if func is None:
            raise GuppyTypeError(
                f"Builtin function `{self.name}` is not defined for argument of type "
                "`{arg.ty}`",
                self.node.args[0] if isinstance(self.node, ast.Call) else self.node,
            )
        return func.compile_call(args, self.parent, self.graph, self.globals, self.node)


# TODO: dict, list, max, min, pow, sum, tuple

extension.new_func("abs", BuiltinCompiler("abs", "__abs__"), higher_order=False)
extension.new_func("bool", BuiltinCompiler("bool", "__bool__"), higher_order=False)
extension.new_func("callable", CallableCompiler(), higher_order=False)
extension.new_func("divmod", BuiltinCompiler("divmod", "__divmod__"), higher_order=False)
extension.new_func("float", BuiltinCompiler("float", "__float__"), higher_order=False)
extension.new_func("id", IdCompiler(), higher_order=False)
extension.new_func("int", BuiltinCompiler("int", "__int__"), higher_order=False)
extension.new_func("len", BuiltinCompiler("len", "__len__"), higher_order=False)
extension.new_func("round", BuiltinCompiler("round", "__round__"), higher_order=False)




