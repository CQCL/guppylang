from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_docstring(validate):
    @guppy
    def f() -> None:
        "Example docstring"

    @guppy
    def g() -> None:
        """Multi
        line
        doc
        string.
        """
        f()

    @guppy
    def nested() -> None:
        """Test docstrings in nested functions"""

        def f_nested() -> None:
            "Example docstring"
            f_nested()
            g()

        def g_nested() -> None:
            """Multi
            line
            doc
            string.
            """

    default_module = guppy.get_module()
    validate(default_module.compile())


def test_docstring_module(validate):
    module = GuppyModule("")

    @guppy(module)
    def f() -> None:
        "Example docstring"
        f()

    @guppy(module)
    def g() -> None:
        """Multi
        line
        doc
        string.
        """

    @guppy(module)
    def nested() -> None:
        """Test docstrings in nested functions"""

        def f_nested() -> None:
            "Example docstring"
            f()
            g()

        def g_nested() -> None:
            """Multi
            line
            doc
            string.
            """
            f()
            f_nested()

    validate(module.compile())
