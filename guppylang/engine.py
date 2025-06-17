from collections import defaultdict
from types import FrameType
from typing import TYPE_CHECKING

import hugr.build.function as hf
from hugr.package import ModulePointer, Package

import guppylang
from guppylang.definition.common import (
    CheckableDef,
    CheckedDef,
    CompiledDef,
    DefId,
    ParsableDef,
    ParsedDef,
    RawDef,
)
from guppylang.definition.ty import TypeDef
from guppylang.error import pretty_errors
from guppylang.span import SourceMap
from guppylang.tys.builtin import (
    array_type_def,
    bool_type_def,
    callable_type_def,
    float_type_def,
    frozenarray_type_def,
    int_type_def,
    list_type_def,
    nat_type_def,
    none_type_def,
    option_type_def,
    sized_iter_type_def,
    string_type_def,
    tuple_type_def,
)

if TYPE_CHECKING:
    from guppylang.compiler.core import MonoDefId

BUILTIN_DEFS_LIST: list[RawDef] = [
    callable_type_def,
    tuple_type_def,
    none_type_def,
    bool_type_def,
    nat_type_def,
    int_type_def,
    float_type_def,
    string_type_def,
    list_type_def,
    array_type_def,
    frozenarray_type_def,
    sized_iter_type_def,
    option_type_def,
]

BUILTIN_DEFS = {defn.name: defn for defn in BUILTIN_DEFS_LIST}


class DefinitionStore:
    """Storage class holding references to all Guppy definitions created in the current
    interpreter session.

    See `DEF_STORE` for the singleton instance of this class.
    """

    raw_defs: dict[DefId, RawDef]
    impls: defaultdict[DefId, dict[str, DefId]]
    frames: dict[DefId, FrameType]
    sources: SourceMap

    def __init__(self) -> None:
        self.raw_defs = {defn.id: defn for defn in BUILTIN_DEFS_LIST}
        self.impls = defaultdict(dict)
        self.frames = {}
        self.sources = SourceMap()

    def register_def(self, defn: RawDef, frame: FrameType | None) -> None:
        self.raw_defs[defn.id] = defn
        if frame:
            self.frames[defn.id] = frame

    def register_impl(self, ty_id: DefId, name: str, impl_id: DefId) -> None:
        self.impls[ty_id][name] = impl_id
        # Update the frame of the definition to the frame of the defining class
        if impl_id in self.frames:
            frame = self.frames[impl_id].f_back
            if frame:
                self.frames[impl_id] = frame


DEF_STORE: DefinitionStore = DefinitionStore()


class CompilationEngine:
    """Main compiler driver handling checking and compiling of definitions.

    The engine maintains a worklist of definitions that still need to be checked and
    makes sure that all dependencies are compiled.

    See `ENGINE` for the singleton instance of this class.
    """

    parsed: dict[DefId, ParsedDef]
    checked: dict[DefId, CheckedDef]
    compiled: dict["MonoDefId", CompiledDef]

    types_to_check_worklist: dict[DefId, ParsedDef]
    to_check_worklist: dict[DefId, ParsedDef]

    def reset(self) -> None:
        """Resets the compilation cache."""
        self.parsed = {}
        self.checked = {}
        self.to_check_worklist = {}
        self.types_to_check_worklist = {}

    def get_parsed(self, id: DefId) -> ParsedDef:
        """Look up the parsed version of a definition by its id.

        Parses the definition if it hasn't been parsed yet. Also makes sure that the
        definition will be checked and compiled later on.
        """
        from guppylang.checker.core import Globals

        if id in self.parsed:
            return self.parsed[id]
        defn = DEF_STORE.raw_defs[id]
        if isinstance(defn, ParsableDef):
            defn = defn.parse(Globals(DEF_STORE.frames[defn.id]), DEF_STORE.sources)
        self.parsed[id] = defn
        if isinstance(defn, TypeDef):
            self.types_to_check_worklist[id] = defn
        else:
            self.to_check_worklist[id] = defn
        return defn

    def get_checked(self, id: DefId) -> CheckedDef:
        """Look up the checked version of a definition by its id.

        Parses and checks the definition if it hasn't been parsed/checked yet. Also
        makes sure that the definition will be compiled to Hugr later on.
        """
        from guppylang.checker.core import Globals

        if id in self.checked:
            return self.checked[id]
        defn = self.get_parsed(id)
        if isinstance(defn, CheckableDef):
            defn = defn.check(Globals(DEF_STORE.frames[defn.id]))
        self.checked[id] = defn

        from guppylang.definition.struct import CheckedStructDef

        if isinstance(defn, CheckedStructDef):
            for method_def in defn.generated_methods():
                DEF_STORE.register_def(method_def, None)
                DEF_STORE.register_impl(defn.id, method_def.name, method_def.id)

        return defn

    @pretty_errors
    def check(self, id: DefId) -> None:
        """Top-level function to kick of checking of a definition.

        This is the main driver behind `guppy.check()`.
        """
        from guppylang.checker.core import Globals

        # Clear previous compilation cache.
        # TODO: In order to maintain results from the previous `check` call we would
        #  need to store and check if any dependencies have changed.
        self.reset()

        defn = DEF_STORE.raw_defs[id]
        self.to_check_worklist = {
            defn.id: (
                defn.parse(Globals(DEF_STORE.frames[defn.id]), DEF_STORE.sources)
                if isinstance(defn, ParsableDef)
                else defn
            )
        }
        while self.types_to_check_worklist or self.to_check_worklist:
            # Types need to be checked first. This is because parsing e.g. a function
            # definition requires instantiating the types in its signature which can
            # only be done if the types have already been checked.
            if self.types_to_check_worklist:
                id, _ = self.types_to_check_worklist.popitem()
            else:
                id, _ = self.to_check_worklist.popitem()
            self.checked[id] = self.get_checked(id)

    @pretty_errors
    def compile(self, id: DefId) -> ModulePointer:
        """Top-level function to kick of Hugr compilation of a definition.

        This is the main driver behind `guppy.compile()`.
        """
        self.check(id)

        # Prepare Hugr for this module
        graph = hf.Module()
        graph.metadata["name"] = "__main__"

        # Lower definitions to Hugr
        from guppylang.compiler.core import CompilerContext

        ctx = CompilerContext(graph)
        ctx.compile(self.checked[id])
        self.compiled = ctx.compiled

        # TODO: Currently we just include a hardcoded list of extensions. We should
        #  compute this dynamically from the imported dependencies instead.
        #
        # The hugr prelude and std_extensions are implicit.
        from guppylang.std._internal.compiler.tket2_exts import TKET2_EXTENSIONS

        extensions = [*TKET2_EXTENSIONS, guppylang.compiler.hugr_extension.EXTENSION]
        return ModulePointer(Package(modules=[graph.hugr], extensions=extensions), 0)


ENGINE: CompilationEngine = CompilationEngine()
