import sys
import subprocess

from pathlib import Path
import selene_core
from selene_core.build_utils import (
    Step,
    ArtifactKind,
    Artifact,
    BuildCtx,
    DEFAULT_BUILD_PLANNER,
)
from selene_core.build_utils.builtins.hugr import HUGREnvelopeBytesKind
from typing import Any


class GuppyPythonFileKind(ArtifactKind[Path]):
    @classmethod
    def matches(cls, resource: Any) -> bool:
        if isinstance(resource, Path):
            path = resource
        elif isinstance(resource, str):
            path = Path(resource)

        return path.suffixes[-2:] == [".gpy", ".py"]


class GuppyPythonFileToHugrPackageStep(Step):
    input_kind = GuppyPythonFileKind
    output_kind = HUGREnvelopeBytesKind

    @classmethod
    def apply(cls, build_ctx: BuildCtx, input_artifact: Artifact) -> Artifact:
        args = [sys.executable, input_artifact.resource]
        if build_ctx.verbose:
            print(f"Executing guppy python file: {args}")

        result = subprocess.run(args, check=True, capture_output=True)
        # TODO handle stderr
        return cls._make_artifact(result.stdout)


def register_guppylang_with_selene(
    planner: selene_core.build_utils.BuildPlanner = DEFAULT_BUILD_PLANNER,
):
    planner.add_kind(GuppyPythonFileKind)
    planner.add_step(GuppyPythonFileToHugrPackageStep)
