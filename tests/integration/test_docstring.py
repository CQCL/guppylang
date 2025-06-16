from guppylang.decorator import guppy


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

    validate(guppy.compile(f))
    validate(guppy.compile(g))
    validate(guppy.compile(nested))
