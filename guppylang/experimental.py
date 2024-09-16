from ast import expr
from types import TracebackType

from guppylang.ast_util import AstNode
from guppylang.error import GuppyError

EXPERIMENTAL_FEATURES_ENABLED = False


class enable_experimental_features:
    """Enables experimental Guppy features.

    Can be used as a context manager to enable experimental features in a `with` block.
    """

    def __init__(self) -> None:
        global EXPERIMENTAL_FEATURES_ENABLED
        self.original = EXPERIMENTAL_FEATURES_ENABLED
        EXPERIMENTAL_FEATURES_ENABLED = True

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        global EXPERIMENTAL_FEATURES_ENABLED
        EXPERIMENTAL_FEATURES_ENABLED = self.original


class disable_experimental_features:
    """Disables experimental Guppy features.

    Can be used as a context manager to enable experimental features in a `with` block.
    """

    def __init__(self) -> None:
        global EXPERIMENTAL_FEATURES_ENABLED
        self.original = EXPERIMENTAL_FEATURES_ENABLED
        EXPERIMENTAL_FEATURES_ENABLED = False

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        global EXPERIMENTAL_FEATURES_ENABLED
        EXPERIMENTAL_FEATURES_ENABLED = self.original


def check_function_tensors_enabled(node: expr | None = None) -> None:
    if not EXPERIMENTAL_FEATURES_ENABLED:
        raise GuppyError(
            "Function tensors are an experimental feature. Use "
            "`guppylang.enable_experimental_features()` to enable them.",
            node,
        )


def check_lists_enabled(loc: AstNode | None = None) -> None:
    if not EXPERIMENTAL_FEATURES_ENABLED:
        raise GuppyError(
            "Lists are an experimental feature and not fully supported yet. Use "
            "`guppylang.enable_experimental_features()` to enable them.",
            loc,
        )
