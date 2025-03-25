from dataclasses import dataclass
from typing import ClassVar

from guppylang.diagnostic import Error, Help, Note
from guppylang.tys.ty import FunctionType


@dataclass(frozen=True)
class IllegalComptimeExpressionError(Error):
    title: ClassVar[str] = "Unsupported Python expression"
    span_label: ClassVar[str] = "Expression of type `{python_ty}` is not supported"
    python_ty: type


@dataclass(frozen=True)
class ComptimeExprNotCPythonError(Error):
    title: ClassVar[str] = "Not running CPython"
    span_label: ClassVar[str] = "Comptime expressions are only supported in CPython"


@dataclass(frozen=True)
class ComptimeExprNotStaticError(Error):
    title: ClassVar[str] = "Not compile-time evaluatable"
    span_label: ClassVar[str] = (
        "Guppy variable `{guppy_var}` cannot be accessed in a comptime expression"
    )
    guppy_var: str


@dataclass(frozen=True)
class ComptimeExprEvalError(Error):
    title: ClassVar[str] = "Python error"
    span_label: ClassVar[str] = (
        "Error occurred while evaluating this comptime expression"
    )
    message: ClassVar[str] = "Traceback printed below:\n\n{err}"
    err: str


@dataclass(frozen=True)
class ComptimeExprIncoherentListError(Error):
    title: ClassVar[str] = "Unsupported list"
    span_label: ClassVar[str] = "List contains elements with different types"


@dataclass(frozen=True)
class Tket2NotInstalled(Error):
    title: ClassVar[str] = "Tket2 not installed"
    span_label: ClassVar[str] = (
        "Experimental pytket compatibility requires `tket2` to be installed"
    )

    @dataclass(frozen=True)
    class InstallInstruction(Help):
        message: ClassVar[str] = "Install tket2: `pip install tket2`"


@dataclass(frozen=True)
class PytketSignatureMismatch(Error):
    title: ClassVar[str] = "Signature mismatch"
    span_label: ClassVar[str] = "Signature `{name}` doesn't match provided circuit"
    name: str

    @dataclass(frozen=True)
    class TypeHint(Note):
        message: ClassVar[str] = "Expected circuit signature is `{circ_sig}`"
        circ_sig: FunctionType
