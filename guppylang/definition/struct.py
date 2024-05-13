import ast
import inspect
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from guppylang.ast_util import AstNode, annotate_location
from guppylang.checker.core import Globals
from guppylang.definition.common import (
    CheckableDef,
    CompiledDef,
    DefId,
    Definition,
    ParsableDef,
)
from guppylang.definition.parameter import ParamDef
from guppylang.definition.ty import TypeDef
from guppylang.error import GuppyError
from guppylang.tys.arg import Argument
from guppylang.tys.param import Parameter
from guppylang.tys.ty import Type


@dataclass(frozen=True)
class UncheckedStructField:
    """A single field on a struct whose type has not been checked yet."""

    name: str
    type_ast: ast.expr


@dataclass(frozen=True)
class StructField:
    """A single field on a struct."""

    name: str
    ty: Type


@dataclass(frozen=True)
class RawStructDef(TypeDef, ParsableDef):
    """A raw struct type definition that has not been parsed yet."""

    python_class: type

    def __getitem__(self, item: Any) -> "RawStructDef":
        """Dummy implementation to enable subscripting in the Python runtime.

        For example, if users write `MyStruct[int]` in a function signature, the
        interpreter will try to execute the expression which would fail if this function
        weren't implemented.
        """
        return self

    def parse(self, globals: Globals) -> "ParsedStructDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        cls_def = parse_py_class(self.python_class)
        if cls_def.keywords:
            raise GuppyError("Unexpected keyword", cls_def.keywords[0])

        # The only base we allow is `Generic[...]` to specify generic parameters
        # TODO: This will become obsolete once we have Python 3.12 style generic classes
        params: list[Parameter]
        match cls_def.bases:
            case []:
                params = []
            case [base] if elems := try_parse_generic_base(base):
                params = params_from_ast(elems, globals)
            case bases:
                raise GuppyError("Struct inheritance is not supported", bases[0])

        fields: list[UncheckedStructField] = []
        used_field_names: set[str] = set()
        for node in cls_def.body:
            match node:
                # We allow `pass` statements to define empty structs
                case ast.Pass():
                    pass
                # Docstrings are also fine
                case ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                # Ensure that all function definitions are Guppy functions
                case ast.FunctionDef(name=name):
                    v = getattr(self.python_class, name)
                    if not isinstance(v, Definition):
                        raise GuppyError(
                            "Add a `@guppy` decorator to this function to add it to "
                            f"the struct `{self.name}`",
                            node,
                        )
                # Struct fields are declared via annotated assignments without value
                case ast.AnnAssign(target=ast.Name(id=field_name)) as node:
                    if node.value:
                        raise GuppyError(
                            "Default struct values are not supported", node.value
                        )
                    if field_name in used_field_names:
                        raise GuppyError(
                            f"Struct `{self.name}` already contains a field named "
                            f"`{field_name}`",
                            node.target,
                        )
                    fields.append(UncheckedStructField(field_name, node.annotation))
                    used_field_names.add(field_name)
                case node:
                    raise GuppyError("Unexpected statement in struct", node)

        return ParsedStructDef(self.id, self.name, cls_def, params, fields)

    def check_instantiate(
        self, args: Sequence[Argument], globals: "Globals", loc: AstNode | None = None
    ) -> Type:
        raise NotImplementedError


@dataclass(frozen=True)
class ParsedStructDef(TypeDef, CheckableDef):
    """A struct definition whose fields have not been checked yet."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    fields: Sequence[UncheckedStructField]

    def check(self, globals: Globals) -> "CheckedStructDef":
        """Checks that all struct fields have valid types."""
        raise NotImplementedError

    def check_instantiate(
        self, args: Sequence[Argument], globals: "Globals", loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        raise NotImplementedError


@dataclass(frozen=True)
class CheckedStructDef(TypeDef, CompiledDef):
    """A struct definition that has been fully checked."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    fields: Sequence[StructField]

    def check_instantiate(
        self, args: Sequence[Argument], globals: "Globals", loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        raise NotImplementedError


def parse_py_class(cls: type) -> ast.ClassDef:
    """Parses a Python class object into an AST."""
    source_lines, line_offset = inspect.getsourcelines(cls)
    source = "".join(source_lines)  # Lines already have trailing \n's
    source = textwrap.dedent(source)
    cls_ast = ast.parse(source).body[0]
    file = inspect.getsourcefile(cls)
    if file is None:
        raise GuppyError("Couldn't determine source file for class")
    annotate_location(cls_ast, source, file, line_offset)
    if not isinstance(cls_ast, ast.ClassDef):
        raise GuppyError("Expected a class definition", cls_ast)
    return cls_ast


def try_parse_generic_base(node: ast.expr) -> list[ast.expr] | None:
    """Checks if an AST node corresponds to a `Generic[T1, ..., Tn]` base class.

    Returns the generic parameters or `None` if the AST has a different shape
    """
    match node:
        case ast.Subscript(value=ast.Name(id="Generic"), slice=elem):
            return elem.elts if isinstance(elem, ast.Tuple) else [elem]
        case _:
            return None


def params_from_ast(nodes: Sequence[ast.expr], globals: Globals) -> list[Parameter]:
    """Parses a list of AST nodes into unique type parameters.

    Raises user errors if the AST nodes don't correspond to parameters or parameters
    occur multiple times.
    """
    params: list[Parameter] = []
    params_set: set[DefId] = set()
    for node in nodes:
        if isinstance(node, ast.Name) and node.id in globals:
            defn = globals[node.id]
            if isinstance(defn, ParamDef):
                if defn.id in params_set:
                    raise GuppyError(
                        f"Parameter `{node.id}` cannot be used multiple times", node
                    )
                params.append(defn.to_param(len(params)))
                params_set.add(defn.id)
                continue
        raise GuppyError("Not a parameter", node)
    return params
