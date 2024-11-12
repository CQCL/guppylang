from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from guppylang.diagnostic import Error, Help, Note

if TYPE_CHECKING:
    from guppylang.definition.struct import StructField
    from guppylang.tys.const import Const
    from guppylang.tys.param import Parameter
    from guppylang.tys.ty import FunctionType, Type


@dataclass(frozen=True)
class TypeMismatchError(Error):
    title: ClassVar[str] = "Type mismatch"
    span_label: ClassVar[str] = "Expected {kind} of type `{expected}`, got `{actual}`"

    expected: Type
    actual: Type
    kind: str = "expression"

    @dataclass(frozen=True)
    class CantInferParam(Note):
        message: ClassVar[str] = (
            "Couldn't infer an instantiation for type variable `?{type_var}` "
            "(higher-rank polymorphic types are not supported)"
        )
        type_var: str

    @dataclass(frozen=True)
    class CantInstantiateFreeVars(Note):
        message: ClassVar[str] = (
            "Can't instantiate parameter `{param}` with type `{illegal_inst}` "
            "containing free variables"
        )
        param: str
        illegal_inst: Type | Const


@dataclass(frozen=True)
class AssignFieldTypeMismatchError(Error):
    title: ClassVar[str] = "Type mismatch"
    span_label: ClassVar[str] = (
        "Cannot assign expression of type `{actual}` to field `{field.name}` of type "
        "`{field.ty}`"
    )
    actual: Type
    field: StructField


@dataclass(frozen=True)
class NonLinearInstantiateError(Error):
    title: ClassVar[str] = "Not defined for linear argument"
    span_label: ClassVar[str] = (
        "Cannot instantiate non-linear type parameter `{param.name}` in type "
        "`{func_ty}` with linear type `{ty}`"
    )
    param: Parameter
    func_ty: FunctionType
    ty: Type


@dataclass(frozen=True)
class TypeInferenceError(Error):
    title: ClassVar[str] = "Cannot infer type"
    span_label: ClassVar[str] = (
        "Cannot infer type variables in expression of type `{unsolved_ty}`"
    )
    unsolved_ty: Type


@dataclass(frozen=True)
class IllegalConstant(Error):
    title: ClassVar[str] = "Unsupported constant"
    span_label: ClassVar[str] = "Type `{ty}` is not supported"
    python_ty: type


@dataclass(frozen=True)
class ModuleMemberNotFoundError(Error):
    title: ClassVar[str] = "Not found in module"
    span_label: ClassVar[str] = "Module `{module_name}` has no member `{member}`"
    module_name: str
    member: str


@dataclass(frozen=True)
class AttributeNotFoundError(Error):
    title: ClassVar[str] = "Attribute not found"
    span_label: ClassVar[str] = "`{ty}` has no attribute `{attribute}`"
    ty: Type
    attribute: str


@dataclass(frozen=True)
class UnaryOperatorNotDefinedError(Error):
    title: ClassVar[str] = "Operator not defined"
    span_label: ClassVar[str] = "Unary operator `{op}` not defined for `{ty}`"
    ty: Type
    op: str


@dataclass(frozen=True)
class BinaryOperatorNotDefinedError(Error):
    title: ClassVar[str] = "Operator not defined"
    span_label: ClassVar[str] = (
        "Binary operator `{op}` not defined for `{left_ty}` and `{right_ty}`"
    )
    left_ty: Type
    right_ty: Type
    op: str


@dataclass(frozen=True)
class BadProtocolError(Error):
    title: ClassVar[str] = "Not {is_not}"
    span_label: ClassVar[str] = "Expression of type `{ty}` is not {is_not}"
    ty: Type
    is_not: str

    @dataclass(frozen=True)
    class MethodMissing(Help):
        message: ClassVar[str] = "Implement missing method: `{method}: {signature}`"
        method: str
        signature: FunctionType

    @dataclass(frozen=True)
    class BadSignature(Help):
        message: ClassVar[str] = (
            "Fix signature of method `{ty}.{method}`:  Expected `{exp_signature}`, got "
            "`{act_signature}`"
        )
        ty: Type
        method: str
        exp_signature: FunctionType
        act_signature: FunctionType


@dataclass(frozen=True)
class MissingReturnValueError(Error):
    title: ClassVar[str] = "Missing return value"
    span_label: ClassVar[str] = "Expected return value of type `{ty}`"
    ty: Type


@dataclass(frozen=True)
class NotCallableError(Error):
    title: ClassVar[str] = "Not callable"
    span_label: ClassVar[str] = "Expected a function, got expression of type `{actual}`"
    actual: Type


@dataclass(frozen=True)
class WrongNumberOfArgsError(Error):
    title: ClassVar[str] = ""  # Custom implementation in `rendered_title`
    span_label: ClassVar[str] = "Expected {expected} function arguments, got `{actual}`"
    expected: int
    actual: int
    detailed: bool = True

    @property
    def rendered_title(self) -> str:
        return (
            "Not enough arguments"
            if self.expected > self.actual
            else "Too many arguments"
        )

    @property
    def rendered_span_label(self) -> str:
        if not self.detailed:
            return f"Expected {self.expected}, got {self.actual}"
        diff = self.expected - self.actual
        if diff < 0:
            msg = "Unexpected arguments" if diff < -1 else "Unexpected argument"
        else:
            msg = "Missing arguments" if diff > 1 else "Missing argument"
        return f"{msg} (expected {self.expected}, got {self.actual})"

    @dataclass(frozen=True)
    class SignatureHint(Note):
        message: ClassVar[str] = "Function signature is `{sig}`"
        sig: FunctionType


@dataclass(frozen=True)
class WrongNumberOfUnpacksError(Error):
    title: ClassVar[str] = "{prefix} values to unpack"
    expected: int
    actual: int

    @property
    def prefix(self) -> str:
        return "Not enough" if self.expected > self.actual else "Too many"

    @property
    def rendered_span_label(self) -> str:
        diff = self.expected - self.actual
        if diff < 0:
            msg = "Unexpected assignment " + ("targets" if diff < -1 else "target")
        else:
            msg = "Not enough assignment targets"
        return f"{msg} (expected {self.expected}, got {self.actual})"


@dataclass(frozen=True)
class AssignNonPlaceHelp(Help):
    message: ClassVar[str] = (
        "Consider assigning this value to a local variable first before assigning the "
        "field `{field.name}`"
    )
    field: StructField
