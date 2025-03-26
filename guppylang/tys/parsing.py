import ast
from collections.abc import Sequence

from guppylang.ast_util import (
    AstNode,
    set_location_from,
    shift_loc,
)
from guppylang.cfg.builder import is_comptime_expression
from guppylang.checker.core import Context, Globals, Locals
from guppylang.checker.errors.generic import ExpectedError
from guppylang.definition.common import Definition
from guppylang.definition.module import ModuleDef
from guppylang.definition.parameter import ParamDef
from guppylang.definition.ty import TypeDef
from guppylang.error import GuppyError
from guppylang.tys.arg import Argument, ConstArg, TypeArg
from guppylang.tys.builtin import CallableTypeDef
from guppylang.tys.const import ConstValue
from guppylang.tys.errors import (
    FlagNotAllowedError,
    FreeTypeVarError,
    HigherKindedTypeVarError,
    IllegalComptimeTypeArgError,
    InvalidCallableTypeError,
    InvalidFlagError,
    InvalidTypeArgError,
    InvalidTypeError,
    ModuleMemberNotFoundError,
    NonLinearOwnedError,
)
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
    param_var_mapping: dict[str, Parameter],
    allow_free_vars: bool = False,
) -> Argument:
    """Turns an AST expression into an argument."""
    # A single (possibly qualified) identifier
    if defn := _try_parse_defn(node, globals):
        return _arg_from_instantiated_defn(
            defn, [], globals, node, param_var_mapping, allow_free_vars
        )

    # A parametrised type, e.g. `list[??]`
    if isinstance(node, ast.Subscript) and (
        defn := _try_parse_defn(node.value, globals)
    ):
        arg_nodes = (
            node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
        )
        return _arg_from_instantiated_defn(
            defn, arg_nodes, globals, node, param_var_mapping, allow_free_vars
        )

    # We allow tuple types to be written as `(int, bool)`
    if isinstance(node, ast.Tuple):
        ty = TupleType(
            [
                type_from_ast(el, globals, param_var_mapping, allow_free_vars)
                for el in node.elts
            ]
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

    # Py-expressions can also be used to specify static numbers
    if comptime_expr := is_comptime_expression(node):
        from guppylang.checker.expr_checker import eval_comptime_expr

        v = eval_comptime_expr(comptime_expr, Context(globals, Locals({}), {}))
        if isinstance(v, int):
            nat_ty = NumericType(NumericType.Kind.Nat)
            return ConstArg(ConstValue(nat_ty, v))
        else:
            raise GuppyError(IllegalComptimeTypeArgError(node, v))

    # Finally, we also support delayed annotations in strings
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        node = _parse_delayed_annotation(node.value, node)
        return arg_from_ast(node, globals, param_var_mapping, allow_free_vars)

    raise GuppyError(InvalidTypeArgError(node))


def _try_parse_defn(node: AstNode, globals: Globals) -> Definition | None:
    """Tries to parse a (possibly qualified) name into a global definition."""
    from guppylang.checker.cfg_checker import VarNotDefinedError

    match node:
        case ast.Name(id=x):
            if x not in globals:
                raise GuppyError(VarNotDefinedError(node, x))
            return globals[x]
        case ast.Attribute(value=ast.Name(id=module_name) as value, attr=x):
            if module_name not in globals:
                raise GuppyError(VarNotDefinedError(value, module_name))
            module_def = globals[module_name]
            if not isinstance(module_def, ModuleDef):
                err = ExpectedError(
                    value,
                    "a module",
                    got=f"{module_def.description} `{module_def.name}`",
                )
                raise GuppyError(err)
            if x not in module_def.globals:
                raise GuppyError(ModuleMemberNotFoundError(node, module_def.name, x))
            return module_def.globals[x]
        case _:
            return None


def _arg_from_instantiated_defn(
    defn: Definition,
    arg_nodes: list[ast.expr],
    globals: Globals,
    node: AstNode,
    param_var_mapping: dict[str, Parameter],
    allow_free_vars: bool = False,
) -> Argument:
    """Parses a globals definition with type args into an argument."""
    match defn:
        # Special case for the `Callable` type
        case CallableTypeDef():
            return TypeArg(
                _parse_callable_type(
                    arg_nodes, node, globals, param_var_mapping, allow_free_vars
                )
            )
        # Either a defined type (e.g. `int`, `bool`, ...)
        case TypeDef() as defn:
            args = [
                arg_from_ast(arg_node, globals, param_var_mapping, allow_free_vars)
                for arg_node in arg_nodes
            ]
            ty = defn.check_instantiate(args, globals, node)
            return TypeArg(ty)
        # Or a parameter (e.g. `T`, `n`, ...)
        case ParamDef() as defn:
            # We don't allow parametrised variables like `T[int]`
            if arg_nodes:
                raise GuppyError(HigherKindedTypeVarError(node, defn))
            if defn.name not in param_var_mapping:
                if allow_free_vars:
                    param_var_mapping[defn.name] = defn.to_param(len(param_var_mapping))
                else:
                    raise GuppyError(FreeTypeVarError(node, defn))
            return param_var_mapping[defn.name].to_bound()
        case defn:
            err = ExpectedError(node, "a type", got=f"{defn.description} `{defn.name}`")
            raise GuppyError(err)


def _parse_delayed_annotation(ast_str: str, node: ast.Constant) -> ast.expr:
    """Parses a delayed type annotation in a string."""
    try:
        [stmt] = ast.parse(ast_str).body
        if not isinstance(stmt, ast.Expr):
            raise GuppyError(InvalidTypeError(node))
        set_location_from(stmt, loc=node)
        shift_loc(
            stmt,
            delta_lineno=node.lineno - 1,  # -1 since lines start at 1
            delta_col_offset=node.col_offset + 1,  # +1 to remove the `"`
        )
    except (SyntaxError, ValueError):
        raise GuppyError(InvalidTypeError(node)) from None
    else:
        return stmt.value


def _parse_callable_type(
    args: list[ast.expr],
    loc: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter],
    allow_free_vars: bool = False,
) -> FunctionType:
    """Helper function to parse a `Callable[[<arguments>], <return type>]` type."""
    err = InvalidCallableTypeError(loc)
    if len(args) != 2:
        raise GuppyError(err)
    [inputs, output] = args
    if not isinstance(inputs, ast.List):
        raise GuppyError(err)
    inouts, output = parse_function_io_types(
        inputs.elts, output, loc, globals, param_var_mapping, allow_free_vars
    )
    return FunctionType(inouts, output)


def parse_function_io_types(
    input_nodes: list[ast.expr],
    output_node: ast.expr,
    loc: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter],
    allow_free_vars: bool = False,
) -> tuple[list[FuncInput], Type]:
    """Parses the inputs and output types of a function type.

    This function takes care of parsing annotations and any related checks.

    Returns the parsed input and output types.
    """
    inputs = []
    for inp in input_nodes:
        ty, flags = type_with_flags_from_ast(
            inp, globals, param_var_mapping, allow_free_vars
        )
        if InputFlags.Owned in flags and ty.copyable:
            raise GuppyError(NonLinearOwnedError(loc, ty))
        if not ty.copyable and InputFlags.Owned not in flags:
            flags |= InputFlags.Inout

        inputs.append(FuncInput(ty, flags))
    output = type_from_ast(output_node, globals, param_var_mapping, allow_free_vars)
    return inputs, output


_type_param = TypeParam(0, "T", False, False)


def type_with_flags_from_ast(
    node: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter],
    allow_free_vars: bool = False,
) -> tuple[Type, InputFlags]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.MatMult):
        ty, flags = type_with_flags_from_ast(
            node.left, globals, param_var_mapping, allow_free_vars
        )
        match node.right:
            case ast.Name(id="owned"):
                if ty.copyable:
                    raise GuppyError(NonLinearOwnedError(node.right, ty))
                flags |= InputFlags.Owned
            case _:
                raise GuppyError(InvalidFlagError(node.right))
        return ty, flags
    # We also need to handle the case that this could be a delayed string annotation
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        node = _parse_delayed_annotation(node.value, node)
        return type_with_flags_from_ast(
            node, globals, param_var_mapping, allow_free_vars
        )
    else:
        # Parse an argument and check that it's valid for a `TypeParam`
        arg = arg_from_ast(node, globals, param_var_mapping, allow_free_vars)
        tyarg = _type_param.check_arg(arg, node)
        return tyarg.ty, InputFlags.NoFlags


def type_from_ast(
    node: AstNode,
    globals: Globals,
    param_var_mapping: dict[str, Parameter],
    allow_free_vars: bool = False,
) -> Type:
    """Turns an AST expression into a Guppy type."""
    ty, flags = type_with_flags_from_ast(
        node, globals, param_var_mapping, allow_free_vars
    )
    if flags != InputFlags.NoFlags:
        assert InputFlags.Inout not in flags  # Users shouldn't be able to set this
        raise GuppyError(FlagNotAllowedError(node))
    return ty


def type_row_from_ast(
    node: ast.expr, globals: "Globals", allow_free_vars: bool = False
) -> Sequence[Type]:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return []
    ty = type_from_ast(node, globals, {}, allow_free_vars)
    if isinstance(ty, TupleType):
        return ty.element_types
    else:
        return [ty]
