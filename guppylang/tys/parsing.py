import ast
from collections.abc import Sequence

from guppylang.ast_util import AstNode
from guppylang.checker.core import Globals
from guppylang.error import GuppyError
from guppylang.tys.arg import Argument, TypeArg
from guppylang.tys.param import Parameter, TypeParam
from guppylang.tys.ty import NoneType, TupleType, Type


def arg_from_ast(
    node: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter] | None = None,
) -> Argument:
    """Turns an AST expression into an argument."""
    # A single identifier
    if isinstance(node, ast.Name):
        x = node.id
        # Either a defined type (e.g. `int`, `bool`, ...)
        if x in globals.type_defs:
            ty = globals.type_defs[x].check_instantiate([], node)
            return TypeArg(ty)
        # Or a parameter (e.g. `T`, `n`, ...)
        if x in globals.param_vars:
            if param_var_mapping is None:
                raise GuppyError(
                    "Free type variable. Only function types can be generic", node
                )
            var = globals.param_vars[x]
            if var.name not in param_var_mapping:
                param_var_mapping[var.name] = var.with_idx(len(param_var_mapping))
            return param_var_mapping[var.name].to_bound()
        raise GuppyError("Unknown identifier", node)

    # A parametrised type, e.g. `list[??]`
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        x = node.value.id
        if x in globals.type_defs:
            arg_nodes = (
                node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            )
            # Hack: Flatten argument lists to support the `Callable` type. For example,
            # we turn `Callable[[int, int], bool]` into `Callable[int, int, bool]`.
            # TODO: We can get rid of this once we added support for variadic params
            arg_nodes = [
                n
                for arg in arg_nodes
                for n in (arg.elts if isinstance(arg, ast.List) else (arg,))
            ]
            args = [
                arg_from_ast(arg_node, globals, param_var_mapping)
                for arg_node in arg_nodes
            ]
            ty = globals.type_defs[x].check_instantiate(args, node)
            return TypeArg(ty)
        # We don't allow parametrised variables like `T[int]`
        if x in globals.param_vars:
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

    # Finally, we also support delayed annotations in strings
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            [stmt] = ast.parse(node.value).body
            if not isinstance(stmt, ast.Expr):
                raise GuppyError("Invalid Guppy type", node)
            return arg_from_ast(stmt.value, globals, param_var_mapping)
        except (SyntaxError, ValueError):
            raise GuppyError("Invalid Guppy type", node) from None

    raise GuppyError("Not a valid type argument", node)


_type_param = TypeParam(0, "T", True)


def type_from_ast(
    node: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter] | None = None,
) -> Type:
    """Turns an AST expression into a Guppy type."""
    # Parse an argument and check that it's valid for a `TypeParam`
    arg = arg_from_ast(node, globals, param_var_mapping)
    return _type_param.check_arg(arg, node).ty


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
