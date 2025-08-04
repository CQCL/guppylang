from collections import defaultdict
from enum import Enum
from types import FrameType
from typing import TYPE_CHECKING

import hugr.build.function as hf
import hugr.std.collections.array
import hugr.std.float
import hugr.std.int
import hugr.std.logic
import hugr.std.prelude
from hugr import ops
from hugr.ext import Extension
from hugr.package import ModulePointer, Package

import guppylang_internals
from guppylang_internals.definition.common import (
    CheckableDef,
    CheckedDef,
    CompiledDef,
    DefId,
    ParsableDef,
    ParsedDef,
    RawDef,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import (
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.error import pretty_errors
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.builtin import (
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
    from guppylang_internals.compiler.core import MonoDefId

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


class CoreMetadataKeys(Enum):
    """Core HUGR metadata keys used by Guppy."""

    USED_EXTENSIONS = "core.used_extensions"
    GENERATOR = "core.generator"


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
                # For Python 3.12 generic functions and classes, there is an additional
                # inserted frame for the annotation scope. We can detect this frame by
                # looking for the special ".generic_base" variable in the frame locals
                # that is implicitly inserted by CPython. See
                # - https://docs.python.org/3/reference/executionmodel.html#annotation-scopes
                # - https://docs.python.org/3/reference/compound_stmts.html#generic-functions
                # - https://jellezijlstra.github.io/pep695.html
                if ".generic_base" in frame.f_locals:
                    frame = frame.f_back
                    assert frame is not None
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
    additional_extensions: list[Extension]

    types_to_check_worklist: dict[DefId, ParsedDef]
    to_check_worklist: dict[DefId, ParsedDef]

    def reset(self) -> None:
        """Resets the compilation cache."""
        self.parsed = {}
        self.checked = {}
        self.compiled = {}
        self.additional_extensions = []
        self.to_check_worklist = {}
        self.types_to_check_worklist = {}

    @pretty_errors
    def register_extension(self, extension: Extension) -> None:
        self.additional_extensions.append(extension)

    @pretty_errors
    def get_parsed(self, id: DefId) -> ParsedDef:
        """Look up the parsed version of a definition by its id.

        Parses the definition if it hasn't been parsed yet. Also makes sure that the
        definition will be checked and compiled later on.
        """
        from guppylang_internals.checker.core import Globals

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

    @pretty_errors
    def get_checked(self, id: DefId) -> CheckedDef:
        """Look up the checked version of a definition by its id.

        Parses and checks the definition if it hasn't been parsed/checked yet. Also
        makes sure that the definition will be compiled to Hugr later on.
        """
        from guppylang_internals.checker.core import Globals

        if id in self.checked:
            return self.checked[id]
        defn = self.get_parsed(id)
        if isinstance(defn, CheckableDef):
            defn = defn.check(Globals(DEF_STORE.frames[defn.id]))
        self.checked[id] = defn

        from guppylang_internals.definition.struct import CheckedStructDef

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
        from guppylang_internals.checker.core import Globals

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

        This is the function that is invoked by `guppy.compile`.
        """
        self.check(id)

        # Prepare Hugr for this module
        graph = hf.Module()
        graph.metadata["name"] = "__main__"  # entrypoint metadata

        # Lower definitions to Hugr
        from guppylang_internals.compiler.core import CompilerContext

        ctx = CompilerContext(graph)
        compiled_def = ctx.compile(self.checked[id])
        self.compiled = ctx.compiled

        if (
            isinstance(compiled_def, CompiledHugrNodeDef)
            and isinstance(compiled_def, CompiledCallableDef)
            and not isinstance(graph.hugr[compiled_def.hugr_node].op, ops.FuncDecl)
        ):
            # if compiling a region set it as the HUGR entrypoint
            # can be loosened after https://github.com/CQCL/hugr/issues/2501 is fixed
            graph.hugr.entrypoint = compiled_def.hugr_node

        # TODO: Currently the list of extensions is manually managed by the user.
        #  We should compute this dynamically from the imported dependencies instead.
        #
        # The hugr prelude and std_extensions are implicit.
        from guppylang_internals.std._internal.compiler.tket_exts import TKET_EXTENSIONS

        extensions = [
            *TKET_EXTENSIONS,
            guppylang_internals.compiler.hugr_extension.EXTENSION,
            *self.additional_extensions,
        ]
        # TODO replace with computed extensions after https://github.com/CQCL/guppylang/issues/550
        all_used_extensions = [
            *extensions,
            hugr.std.prelude.PRELUDE_EXTENSION,
            hugr.std.collections.array.EXTENSION,
            hugr.std.float.FLOAT_OPS_EXTENSION,
            hugr.std.float.FLOAT_TYPES_EXTENSION,
            hugr.std.int.INT_OPS_EXTENSION,
            hugr.std.int.INT_TYPES_EXTENSION,
            hugr.std.logic.EXTENSION,
        ]
        graph.hugr.module_root.metadata[CoreMetadataKeys.USED_EXTENSIONS.value] = [
            {
                "name": ext.name,
                "version": str(ext.version),
            }
            for ext in all_used_extensions
        ]
        graph.hugr.module_root.metadata[CoreMetadataKeys.GENERATOR.value] = {
            "name": "guppylang",
            "version": guppylang_internals.__version__,
        }
        return ModulePointer(Package(modules=[graph.hugr], extensions=extensions), 0)


ENGINE: CompilationEngine = CompilationEngine()
