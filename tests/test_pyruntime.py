import pytest
from typing import ClassVar
from hugr import ext, Hugr, ops, tys, val
from hugr.build import Cfg
from hugr.build.function import Module
from hugr.std.int import INT_T, DivMod, IntVal, int_t, INT_OPS_EXTENSION

from guppylang.pyruntime import PyRuntime


@pytest.mark.asyncio
async def test_recursive_fibonacci() -> None:
    mod = Module()

    fib = mod.define_function("fibonacci", [INT_T], [INT_T])
    one = fib.load(IntVal(1))
    two = fib.load(IntVal(2))
    pred = fib.add_op(ILtU, fib.input_node[0], two)
    cond = fib.add_conditional(pred)
    with cond.add_case(0) as f:
        r1 = f.call(fib, f.add_op(ISub, fib.input_node[0], one))
        r2 = f.call(fib, f.add_op(ISub, fib.input_node[0], two))
        f.set_outputs(f.add_op(IAdd, r1, r2))
    with cond.add_case(1) as t:
        t.set_outputs(t.load(IntVal(1)))
    fib.set_outputs(*cond.outputs())

    main = mod.define_function("main", [], [INT_T])
    main.set_outputs(main.call(fib, main.load(IntVal(5))))

    outs = await PyRuntime().run_graph(mod.hugr)
    assert outs == [IntVal(8)]


@pytest.mark.asyncio
async def test_iterative_factorial() -> None:
    mod = Module()

    fac = mod.define_function("factorial", [INT_T], [INT_T])
    loop_t = tys.Either([INT_T], [])
    with fac.add_tail_loop(fac.inputs(), [fac.load(IntVal(1))]) as tl:
        one = tl.load(IntVal(1))
        with tl.add_if(tl.add_op(ILtU, tl.input_node[0], one)) as if_:
            if_.set_outputs(if_.add(ops.Break(loop_t)()), tl.input_node[1])
        with if_.add_else() as else_:
            i2 = else_.add_op(ISub, tl.input_node[0], one)
            f2 = else_.add_op(IMul, tl.input_node[0], tl.input_node[1])
            else_.set_outputs(else_.add(ops.Continue(loop_t)(i2)), f2)
        tl.set_loop_outputs(*else_.conditional_node.outputs())
    fac.set_outputs(tl)

    main = mod.define_function("main", [], [INT_T])
    main.set_outputs(main.call(fac, main.load(IntVal(5))))

    outs = await PyRuntime().run_graph(mod.hugr)
    assert outs == [IntVal(120, 5)]


@pytest.mark.asyncio
async def test_xor_and_cfg():
    from pathlib import Path

    with open(Path(__file__).parent / "xor_and_cfg.json") as f:
        h = Hugr.load_json(f.read())
    for a in [False, True]:
        for b in [False, True]:
            outs = await PyRuntime().run_graph(h, a, b)
            assert outs == [
                val.TRUE if a ^ b else val.FALSE,
                val.TRUE if a and b else val.FALSE,
            ]


@pytest.mark.asyncio
async def test_dom_edges():
    c = Cfg(tys.Bool, INT_T)

    entry = c.add_entry()
    cst = entry.load(IntVal(6))
    entry.set_block_outputs(*entry.inputs())  # Use Bool to branch, so INT_T

    middle_1 = c.add_successor(entry[0])
    dm = middle_1.add(DivMod(*middle_1.inputs(), cst))
    middle_1.set_single_succ_outputs(dm[0])

    middle_2 = c.add_successor(entry[1])
    middle_2.set_single_succ_outputs(*middle_2.inputs())

    merge = c.add_successor(middle_1)
    c.branch(middle_2[0], merge)
    merge.set_single_succ_outputs(*merge.inputs(), cst)

    c.branch_exit(merge)

    outs = await PyRuntime().run_graph(c.hugr, val.TRUE, 12)
    assert outs == [IntVal(12), IntVal(6)]

    outs = await PyRuntime().run_graph(c.hugr, val.FALSE, 18)
    assert outs == [IntVal(3), IntVal(6)]


from dataclasses import dataclass


@dataclass(frozen=True)
class _ILtUDef(ops.RegisteredOp):
    """Integer less than (unsigned)."""

    width: int = 5
    const_op_def: ClassVar[ext.OpDef] = INT_OPS_EXTENSION.operations["ilt_u"]

    def type_args(self) -> list[tys.TypeArg]:
        return [tys.BoundedNatArg(n=self.width)]

    def cached_signature(self) -> tys.FunctionType | None:
        row: list[tys.Type] = [int_t(self.width)] * 2
        return tys.FunctionType(row, [tys.Bool], runtime_reqs=[INT_OPS_EXTENSION.name])

    def __call__(self, a: ops.ComWire) -> ops.Command:
        return ops.DataflowOp.__call__(self, a)


#: IntLessThan (unsigned) operation
ILtU = _ILtUDef()


@dataclass(frozen=True)
class _IMulDef(ops.RegisteredOp):
    """Integer multiply."""

    width: int = 5
    const_op_def: ClassVar[ext.OpDef] = INT_OPS_EXTENSION.operations["imul"]

    def type_args(self) -> list[tys.TypeArg]:
        return [tys.BoundedNatArg(n=self.width)]

    def cached_signature(self) -> tys.FunctionType | None:
        row: list[tys.Type] = [int_t(self.width)] * 2
        return tys.FunctionType(
            row, [int_t(self.width)], runtime_reqs=[INT_OPS_EXTENSION.name]
        )

    def __call__(self, a: ops.ComWire) -> ops.Command:
        return ops.DataflowOp.__call__(self, a)


#: IMul operation
IMul = _IMulDef()


@dataclass(frozen=True)
class _ISubDef(ops.RegisteredOp):
    """Integer subtract."""

    width: int = 5
    const_op_def: ClassVar[ext.OpDef] = INT_OPS_EXTENSION.operations["isub"]

    def type_args(self) -> list[tys.TypeArg]:
        return [tys.BoundedNatArg(n=self.width)]

    def cached_signature(self) -> tys.FunctionType | None:
        row: list[tys.Type] = [int_t(self.width)] * 2
        return tys.FunctionType(
            row, [int_t(self.width)], runtime_reqs=[INT_OPS_EXTENSION.name]
        )

    def __call__(self, a: ops.ComWire) -> ops.Command:
        return ops.DataflowOp.__call__(self, a)


#: ISub operation
ISub = _ISubDef()


@dataclass(frozen=True)
class _IAddDef(ops.RegisteredOp):
    """Integer add."""

    width: int = 5
    const_op_def: ClassVar[ext.OpDef] = INT_OPS_EXTENSION.operations["iadd"]

    def type_args(self) -> list[tys.TypeArg]:
        return [tys.BoundedNatArg(n=self.width)]

    def cached_signature(self) -> tys.FunctionType | None:
        row: list[tys.Type] = [int_t(self.width)] * 2
        return tys.FunctionType(
            row, [int_t(self.width)], runtime_reqs=[INT_OPS_EXTENSION.name]
        )

    def __call__(self, a: ops.ComWire) -> ops.Command:
        return ops.DataflowOp.__call__(self, a)


#: IAdd operation
IAdd = _IAddDef()
