import ast
from collections.abc import Sequence

from guppylang.ast_util import (
    AstNode,
    set_location_from,
    shift_loc,
)
from guppylang.checker.core import Globals
from guppylang.definition.parameter import ParamDef
from guppylang.definition.ty import TypeDef
from guppylang.error import GuppyError
from guppylang.tys.arg import Argument, ConstArg, TypeArg
from guppylang.tys.builtin import CallableTypeDef
from guppylang.tys.const import ConstValue
from guppylang.tys.param import Parameter, TypeParam
from guppylang.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    TupleType,
    Type,
)


def arg_from_ast(
    node: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter] | None = None,
) -> Argument:
    """Turns an AST expression into an argument."""
    # A single identifier
    if isinstance(node, ast.Name):
        x = node.id
        if x not in globals:
            raise GuppyError("Unknown identifier", node)
        match globals[x]:
            # Special case for the `Callable` type
            case CallableTypeDef():
                return TypeArg(
                    _parse_callable_type([], node, globals, param_var_mapping)
                )
            # Either a defined type (e.g. `int`, `bool`, ...)
            case TypeDef() as defn:
                return TypeArg(defn.check_instantiate([], globals, node))
            # Or a parameter (e.g. `T`, `n`, ...)
            case ParamDef() as defn:
                if param_var_mapping is None:
                    raise GuppyError(
                        "Free type variable. Only function types can be generic", node
                    )
                if x not in param_var_mapping:
                    param_var_mapping[x] = defn.to_param(len(param_var_mapping))
                return param_var_mapping[x].to_bound()
            case defn:
                raise GuppyError(
                    f"Expected a type, got {defn.description} `{defn.name}`", node
                )

    # A parametrised type, e.g. `list[??]`
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        x = node.value.id
        if x in globals:
            defn = globals[x]
            arg_nodes = (
                node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            )
            if isinstance(defn, CallableTypeDef):
                # Special case for the `Callable[[S1, S2, ...], T]` type to support the
                # input list syntax and @inout annotations.
                return TypeArg(
                    _parse_callable_type(arg_nodes, node, globals, param_var_mapping)
                )
            if isinstance(defn, TypeDef):
                args = [
                    arg_from_ast(arg_node, globals, param_var_mapping)
                    for arg_node in arg_nodes
                ]
                ty = defn.check_instantiate(args, globals, node)
                return TypeArg(ty)
            # We don't allow parametrised variables like `T[int]`
            if isinstance(defn, ParamDef):
                raise GuppyError(
                    f"Variable `{x}` is not parameterized. Higher-kinded types are not "
                    f"supported",
                    node,
                )

    # We allow tuple types to be written as `(int, bool)`
    if isinstance(node, ast.Tuple):
        ty = TupleType(
            [type_from_ast(el, globals, param_var_mapping) for el in node.elts]
        )
        return TypeArg(ty)

    # `None` is represented as a `ast.Constant` node with value `None`
    if isinstance(node, ast.Constant) and node.value is None:
        return TypeArg(NoneType())

    # Integer literals are turned into nat args since these are the only ones we support
    # right now.
    # TODO: Once we also have int args etc, we need proper inference logic here
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        # Fun fact: int ast.Constant values are never negative since e.g. `-5` is a
        # `ast.UnaryOp` negation of a `ast.Constant(5)`
        assert node.value >= 0
        nat_ty = NumericType(NumericType.Kind.Nat)
        return ConstArg(ConstValue(nat_ty, node.value))

    # Finally, we also support delayed annotations in strings
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        node = _parse_delayed_annotation(node.value, node)
        return arg_from_ast(node, globals, param_var_mapping)

    raise GuppyError("Not a valid type argument", node)


def _parse_delayed_annotation(ast_str: str, node: ast.Constant) -> ast.expr:
    """Parses a delayed type annotation in a string."""
    try:
        [stmt] = ast.parse(ast_str).body
        if not isinstance(stmt, ast.Expr):
            raise GuppyError("Invalid Guppy type", node)
        set_location_from(stmt, loc=node)
        shift_loc(
            stmt,
            delta_lineno=node.lineno - 1,  # -1 since lines start at 1
            delta_col_offset=node.col_offset + 1,  # +1 to remove the `"`
        )
    except (SyntaxError, ValueError):
        raise GuppyError("Invalid Guppy type", node) from None
    else:
        return stmt.value


def _parse_callable_type(
    args: list[ast.expr],
    loc: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter] | None,
) -> FunctionType:
    """Helper function to parse a `Callable[[<arguments>], <return types>]` type."""
    err = (
        "Function types should be specified via "
        "`Callable[[<arguments>], <return types>]`"
    )
    if len(args) != 2:
        raise GuppyError(err, loc)
    [inputs, output] = args
    if not isinstance(inputs, ast.List):
        raise GuppyError(err, loc)
    inouts, output = parse_function_io_types(
        inputs.elts, output, loc, globals, param_var_mapping
    )
    return FunctionType(inouts, output)


def parse_function_io_types(
    input_nodes: list[ast.expr],
    output_node: ast.expr,
    loc: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter] | None,
) -> tuple[list[FuncInput], Type]:
    """Parses the inputs and output types of a function type.

    This function takes care of parsing `@inout` annotations and any related checks.

    Returns the parsed input and output types.
    """
    inputs = []
    for inp in input_nodes:
        ty, flags = type_with_flags_from_ast(inp, globals, param_var_mapping)
        if InputFlags.Inout in flags and not ty.linear:
            raise GuppyError(
                f"Non-linear type `{ty}` cannot be annotated as `@inout`", loc
            )
        inputs.append(FuncInput(ty, flags))
    output = type_from_ast(output_node, globals, param_var_mapping)
    return inputs, output


_type_param = TypeParam(0, "T", True)


def type_with_flags_from_ast(
    node: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter] | None = None,
) -> tuple[Type, InputFlags]:
    """Turns an AST expression into a Guppy type with some optional @flags."""
    # Check for `type @flag` annotations
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.MatMult):
        ty, flags = type_with_flags_from_ast(node.left, globals, param_var_mapping)
        match node.right:
            case ast.Name(id="inout"):
                if not ty.linear:
                    raise GuppyError(
                        f"Non-linear type `{ty}` cannot be annotated as `@inout`",
                        node.right,
                    )
                flags |= InputFlags.Inout
            case _:
                raise GuppyError("Invalid annotation", node.right)
        return ty, flags
    # We also need to handle the case that this could be a delayed string annotation
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        node = _parse_delayed_annotation(node.value, node)
        return type_with_flags_from_ast(node, globals, param_var_mapping)
    else:
        # Parse an argument and check that it's valid for a `TypeParam`
        arg = arg_from_ast(node, globals, param_var_mapping)
        return _type_param.check_arg(arg, node).ty, InputFlags.NoFlags


def type_from_ast(
    node: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter] | None = None,
) -> Type:
    """Turns an AST expression into a Guppy type."""
    ty, flags = type_with_flags_from_ast(node, globals, param_var_mapping)
    if flags != InputFlags.NoFlags:
        raise GuppyError("`@` type annotations are not allowed in this position", node)
    return ty


def type_row_from_ast(node: ast.expr, globals: "Globals") -> Sequence[Type]:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return []
    ty = type_from_ast(node, globals)
    if isinstance(ty, TupleType):
        return ty.element_types
    else:
        return [ty]
