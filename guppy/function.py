import ast

from guppy.bb import BB, NestedFunctionDef
from guppy.cfg import CFGBuilder
from guppy.compiler_base import CompilerBase, VarMap, RawVariable, DFContainer, Variable
from guppy.error import GuppyError
from guppy.expression import expr_to_row
from guppy.guppy_types import (
    FunctionType,
    GuppyType,
    IntType,
    FloatType,
    BoolType,
    StringType,
    TupleType,
    TypeRow,
)
from guppy.hugr.hugr import Hugr, OutPortV, DFContainingVNode


class FunctionCompiler(CompilerBase):
    cfg_builder: CFGBuilder

    def __init__(self, graph: Hugr, global_variables: VarMap):
        super().__init__(graph, global_variables)
        self.cfg_builder = CFGBuilder()

    @staticmethod
    def validate_signature(func_def: ast.FunctionDef) -> FunctionType:
        """Checks the signature of a function definition and returns the corresponding
        Guppy type."""
        if len(func_def.args.posonlyargs) != 0:
            raise GuppyError(
                "Positional-only parameters not supported", func_def.args.posonlyargs[0]
            )
        if len(func_def.args.kwonlyargs) != 0:
            raise GuppyError(
                "Keyword-only parameters not supported", func_def.args.kwonlyargs[0]
            )
        if func_def.args.vararg is not None:
            raise GuppyError("*args not supported", func_def.args.vararg)
        if func_def.args.kwarg is not None:
            raise GuppyError("**kwargs not supported", func_def.args.kwarg)
        if func_def.returns is None:
            raise GuppyError(
                "Return type must be annotated", func_def
            )  # TODO: Error location is incorrect

        arg_tys = []
        arg_names = []
        for i, arg in enumerate(func_def.args.args):
            if arg.annotation is None:
                raise GuppyError("Argument type must be annotated", arg)
            ty = type_from_ast(arg.annotation)
            arg_tys.append(ty)
            arg_names.append(arg.arg)

        ret_type_row = type_row_from_ast(func_def.returns)
        return FunctionType(arg_tys, ret_type_row.tys, arg_names)

    def compile_global(
        self,
        func_def: ast.FunctionDef,
        def_node: DFContainingVNode,
        global_variables: VarMap,
    ) -> OutPortV:
        """Compiles a top-level function definition."""
        self.global_variables = global_variables
        func_ty = self.validate_signature(func_def)
        args = func_def.args.args

        cfg = self.cfg_builder.build(func_def.body, len(func_ty.returns))

        def_input = self.graph.add_input(parent=def_node)
        cfg_node = self.graph.add_cfg(
            def_node, inputs=[def_input.add_out_port(ty) for ty in func_ty.args]
        )
        assert func_ty.arg_names is not None
        input_sig = [
            RawVariable(x, t, l)
            for x, t, l in zip(func_ty.arg_names, func_ty.args, args)
        ]
        cfg.compile(
            self.graph, input_sig, list(func_ty.returns), cfg_node, global_variables
        )

        # Add final output node for the def block
        self.graph.add_output(
            inputs=[cfg_node.add_out_port(ty) for ty in func_ty.returns],
            parent=def_node,
        )

        return def_node.out_port(0)

    def compile_local(
        self,
        func_def: NestedFunctionDef,
        dfg: DFContainer,
        bb: BB,
        global_variables: VarMap,
    ) -> OutPortV:
        """Compiles a local (nested) function definition."""
        self.global_variables = global_variables
        func_ty = self.validate_signature(func_def)
        args = func_def.args.args
        assert func_ty.arg_names is not None

        # We've already computed the CFG for this function while computing the CFG of
        # the enclosing function
        cfg = func_def.cfg

        # Find captured variables
        parent_cfg = bb.cfg
        def_ass_before = set(func_ty.arg_names) | dfg.variables.keys()
        maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]
        cfg.analyze(len(func_ty.returns), def_ass_before, maybe_ass_before)
        captured = [
            dfg[x]
            for x in cfg.live_before[cfg.entry_bb]
            if x not in func_ty.arg_names and x in dfg
        ]

        # Captured variables may never be assigned to
        for bb in cfg.bbs:
            for v in captured:
                x = v.name
                if x in bb.vars.assigned:
                    raise GuppyError(
                        f"Variable `{x}` defined in an outer scope (at {{0}}) may not "
                        f"be assigned to",
                        bb.vars.assigned[x],
                        [v.defined_at],
                    )

        # Prepend captured variables to the function arguments
        closure_ty = FunctionType(
            [v.ty for v in captured] + list(func_ty.args),
            func_ty.returns,
            [v.name for v in captured] + list(func_ty.arg_names),
        )

        def_node = self.graph.add_def(closure_ty, dfg.node, func_def.name)
        def_input = self.graph.add_input(parent=def_node)
        input_ports = [def_input.add_out_port(ty) for ty in closure_ty.args]
        input_row = captured + [
            RawVariable(x, t, l)
            for x, t, l in zip(func_ty.arg_names, func_ty.args, args)
        ]

        # If we have captured variables and the body contains a recursive occurrence of
        # the function itself, then we pass a version of the function with applied
        # captured arguments as an extra argument.
        if len(captured) > 0 and func_def.name in cfg.live_before[cfg.entry_bb]:
            loaded = self.graph.add_load_constant(def_node.out_port(0), parent=def_node)
            partial = self.graph.add_partial(
                loaded.out_port(0), args=input_ports[: len(captured)], parent=def_node
            )
            input_ports += [partial.out_port(0)]
            input_row += [RawVariable(func_def.name, func_ty, func_def)]
        # Otherwise, we can treat the function like a normal global variable
        else:
            global_variables = global_variables | {
                func_def.name: Variable(func_def.name, def_node.out_port(0), func_def)
            }

        cfg_node = self.graph.add_cfg(def_node, inputs=input_ports)
        cfg.compile(
            self.graph, input_row, list(func_ty.returns), cfg_node, global_variables
        )

        # Add final output node for the def block
        self.graph.add_output(
            inputs=[cfg_node.add_out_port(ty) for ty in func_ty.returns],
            parent=def_node,
        )

        # Finally, add partial application node to supply the captured arguments
        loaded = self.graph.add_load_constant(def_node.out_port(0), parent=dfg.node)
        if len(captured) > 0:
            # TODO: We can probably get rid of the load here once we have a resource
            #  that supports partial application, instead of using a dummy Op here.
            partial = self.graph.add_partial(
                loaded.out_port(0), args=[v.port for v in captured], parent=dfg.node
            )
            return partial.out_port(0)
        return loaded.out_port(0)


def type_from_ast(node: ast.expr) -> GuppyType:
    """Turns an AST expression into a Guppy type."""
    if isinstance(node, ast.Name):
        if node.id == "int":
            return IntType()
        elif node.id == "float":
            return FloatType()
        elif node.id == "bool":
            return BoolType()
        elif node.id == "str":
            return StringType()
    elif isinstance(node, ast.Tuple):
        return TupleType([type_from_ast(el) for el in node.elts])
    # TODO: Remaining cases
    raise GuppyError(f"Invalid type: `{ast.unparse(node)}`", node)


def type_row_from_ast(node: ast.expr) -> TypeRow:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return TypeRow([])
    return TypeRow([type_from_ast(e) for e in expr_to_row(node)])
