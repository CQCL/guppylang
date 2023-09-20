"""Guppy standard extension for bool operations."""

# mypy: disable-error-code=empty-body

from guppy.prelude import builtin
from guppy.prelude.builtin import BoolType
from guppy.extension import (
    GuppyExtension,
    OpCompiler,
    IdOpCompiler,
    NotImplementedCompiler,
)
from guppy.hugr import ops
from guppy.prelude.integer import IntOpCompiler


class BoolOpCompiler(OpCompiler):
    def __init__(self, op_name: str):
        super().__init__(ops.CustomOp(extension="logic", op_name=op_name, args=[]))


ext = GuppyExtension("boolean", [builtin])


@ext.func(BoolOpCompiler("And"), instance=BoolType)
def __and__(self: bool, other: bool) -> bool:
    ...


@ext.func(IdOpCompiler(), instance=BoolType)
def __bool__(self: bool) -> bool:
    ...


@ext.func(IntOpCompiler("ifrombool"), instance=BoolType)
def __int__(self: bool) -> int:
    ...


@ext.func(BoolOpCompiler("Or"), instance=BoolType)
def __or__(self: bool, other: bool) -> bool:
    ...


@ext.func(NotImplementedCompiler(), instance=BoolType)  # TODO
def __str__(self: int) -> str:
    ...
