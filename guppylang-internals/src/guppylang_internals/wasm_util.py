from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from wasm_tob import (
    LANG_TYPE_F64,
    LANG_TYPE_I64,
    SEC_EXPORT,
    SEC_FUNCTION,
    SEC_TYPE,
    decode_module,
)

from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    Type,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from wasm_tob.decode import ModuleFragment


# The thing to be imported elsewhere
@dataclass
class ConcreteWasmModule:
    filename: str
    # Function names in order for looking up by index
    functions: dict[int, str]
    function_sigs: dict[str, FunctionType | str]


@dataclass(frozen=True)
class WasmFileNotFound(Error):
    title: ClassVar[str] = "Wasm file `{file}` not found"
    file: str


@dataclass(frozen=True)
class WasmFunctionNotInFile(Error):
    title: ClassVar[str] = (
        "Declared wasm function `{function}` isn't exported by wasm file {file}"
    )
    function: str
    file: str


@dataclass(frozen=True)
class WasmSigMismatchError(Error):
    title: ClassVar[str] = "Wasm signature mismatch"
    span_label: ClassVar[str] = (
        "Signature of wasm function didn't match that in provided file"
    )

    @dataclass(frozen=True)
    class Declaration(Note):
        message: ClassVar[str] = "Declared signature: {declared}"
        declared: str

    @dataclass(frozen=True)
    class Actual(Note):
        message: ClassVar[str] = "Signature in wasm:  {actual}"
        actual: str


def decode_type(tag: int) -> Type | None:
    if tag == LANG_TYPE_I64:
        return NumericType(NumericType.Kind.Int)
    elif tag == LANG_TYPE_F64:
        return NumericType(NumericType.Kind.Float)
    else:
        return None


def decode_sig(params: list[int], output: int | None) -> FunctionType | str:
    # Function args in wasm are called "params"
    my_params: list[FuncInput] = []
    for p in params:
        if ty := decode_type(p):
            my_params.append(FuncInput(ty, flags=InputFlags.NoFlags))
        else:
            return f"Invalid param: {p}"
    if output:
        if ty := decode_type(output):
            return FunctionType(my_params, ty)
        else:
            return f"Invalid output: {output}"
    else:
        return FunctionType(my_params, NoneType())


def decode_wasm_functions(filename: str, wasm_bytes: bytes) -> ConcreteWasmModule:
    """Top level function which reads in wasm bytes and returns a map of
    function names to either a guppy signatures or an error message.
    It is allowable for a file to have signatures unrepresentable in guppy as
    long as they're don't have interface stubs written in guppy, so we only fail
    when such a type is written with a @wasm decorator.
    """
    wasm_module: Iterator[ModuleFragment] = iter(decode_module(wasm_bytes))
    next(wasm_module)  # Skip module header (always first)
    funcs: dict[str, FunctionType | str] = {}
    fun_tys: list[FunctionType | str] = []
    fun_ptrs: list[int] = []
    ordered_func_names: dict[int, str] = {}
    for _, frag_data in wasm_module:
        # If we find a type section, add each type to our ordered list of types
        # in `fun_tys`
        if frag_data.id == SEC_TYPE:
            for ty in frag_data.payload.entries:
                # TODO: Do we need to worry about the form?
                if ty.return_count > 1:
                    fun_tys.append(
                        "!!!! Illegal function with more than one return type !!!!"
                    )
                else:
                    fun_tys.append(
                        decode_sig(
                            ty.param_types,
                            ty.return_type if ty.return_count == 1 else None,
                        )
                    )
        # Function section gives us a list of functions, which each are just indices
        # into the types list
        elif frag_data.id == SEC_FUNCTION:
            fun_ptrs = list(frag_data.payload.types)
        # The export section says which symbols are available to us! With types
        # which index into the function types list
        elif frag_data.id == SEC_EXPORT:
            for export in frag_data.payload.entries:
                name = bytearray(export.field_str[: export.field_len]).decode("utf8")
                # It's a function!
                if export.kind == 0:
                    funcs[name] = fun_tys[fun_ptrs[export.index]]
                    ordered_func_names[export.index] = name
        else:
            # Ignore other sections, like function bodies
            pass
    return ConcreteWasmModule(filename, ordered_func_names, funcs)
