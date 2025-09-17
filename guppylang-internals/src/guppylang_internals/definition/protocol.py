import ast
from dataclasses import dataclass, field
from typing import ClassVar, Mapping, Sequence
import sys

from guppylang_internals.ast_util import AstNode
from guppylang_internals.definition.common import CheckableDef, CompiledDef, DefId, Definition, ParsableDef
from guppylang_internals.definition.struct import NonGuppyMethodError, RedundantParamsError, params_from_ast, parse_py_class, try_parse_generic_base
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import type_from_ast
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.ty import FunctionType
from guppylang_internals.checker.core import Globals
from guppylang_internals.span import SourceMap, Span, to_span
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.checker.errors.generic import (
    ExpectedError,
    UnexpectedError,
    UnsupportedError,
)
from guppylang_internals.diagnostic import Error, Help, Note


if sys.version_info >= (3, 12):
    from guppylang_internals.tys.parsing import parse_parameter

@dataclass(frozen=True)
class ProtocolDef(Definition):
    """Abstract base class for protocol definitions."""

    description: str = field(default="protocol", init=False)


@dataclass(frozen=True)
class RawProtocolDef(ProtocolDef, ParsableDef):
    """A raw protocol definition that has not been parsed yet."""
    
    python_class: type

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedProtocolDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        # Mostly copied from RawStructDef.parse, but only allowing function declarations
        # in the body and allowing `Protocol` as a base class.
        frame = DEF_STORE.frames[self.id]
        cls_def = parse_py_class(self.python_class, frame, sources)
        if cls_def.keywords:
            raise GuppyError(UnexpectedError(cls_def.keywords[0], "keyword"))

        # Look for generic parameters from Python 3.12 style syntax.
        params = []
        params_span: Span | None = None
        if sys.version_info >= (3, 12):
            if cls_def.type_params:
                first, last = cls_def.type_params[0], cls_def.type_params[-1]
                params_span = Span(to_span(first).start, to_span(last).end)
                params = [
                    parse_parameter(node, idx, globals)
                    for idx, node in enumerate(cls_def.type_params)
                ]

        match cls_def.bases:
            case []:
                pass
            # We allow `Generic[...]` to specify  parameters with the legacy syntax.
            case [base] if elems := try_parse_generic_base(base):
                # Complain if we already have Python 3.12 generic params
                if params_span is not None:
                    err: Error = RedundantParamsError(base, self.name)
                    err.add_sub_diagnostic(RedundantParamsError.PrevSpec(params_span))
                    raise GuppyError(err)
                params = params_from_ast(elems, globals)
            # Specifying `Protocol` is redundant but we allow it optionally.
            case [base] if base.id == "Protocol": 
                pass
            case bases:
                err = UnsupportedError(bases[0], "Protocol inheritance", singular=True)
                raise GuppyError(err)

        func_defs: dict[str, ast.FunctionDef] = {}
        for i, node in enumerate(cls_def.body):
            match i, node:
                # Docstrings are fine if they occur at the start.
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                # Ensure that all function definitions are Guppy declarations.
                case _, ast.FunctionDef(name=name) as node:
                    from guppylang.defs import GuppyDefinition

                    v = getattr(self.python_class, name)
                    if not isinstance(v, GuppyDefinition):
                        raise GuppyError(NonGuppyMethodError(node, self.name, name))
                    func_defs[name] = node
                # Fields are not allowed in protocols.
                case _, ast.AnnAssign(target=ast.Name(_)) as node:
                    err = UnsupportedError(node.value, "field", unsupported_in="protocol definition")
                    raise GuppyError(err)
                case _, node:
                    err = UnexpectedError(
                        node, "statement", unexpected_in="protocol definition"
                    )
                    raise GuppyError(err)


        return ParsedProtocolDef(self.id, self.name, cls_def, params, func_defs)


@dataclass(frozen=True)
class ParsedProtocolDef(ProtocolDef, CheckableDef):
    """A protocol definition that is missing member function types."""
    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    members: Mapping[str, ast.FunctionDef]

    # Retrieve the function type for each member.
    def check(self, globals: Globals) -> "CheckedProtocolDef":
        # TODO: Check that this works / likely there is a better way to do this?
        param_var_mapping = {p.name: p for p in self.params}
        members: dict[str, FunctionType] = {}
        for name, node in members.items():
            func_type = type_from_ast(node, globals, param_var_mapping)
            print(func_type)
            members[name] = func_type

        return CheckedProtocolDef(self.id, self.name, self.defined_at, self.params, members)
    
    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> ProtocolInst:
        """Checks if the protocol can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        return ProtocolInst(self.id, args)


@dataclass(frozen=True)
class CheckedProtocolDef(ProtocolDef, CompiledDef):
    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    members: Mapping[str, FunctionType]

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> ProtocolInst:
        """Checks if the protocol can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        return ProtocolInst(self.id, args)

