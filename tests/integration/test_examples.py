"""Tests validating the files in the `examples` directory."""


def test_demo_notebook(nb_regression):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check("tests/integration/notebooks/demo.ipynb")


def test_random_walk_qpe(validate):
    from examples.random_walk_qpe import hugr

    validate(hugr)


def test_t_factory(validate):
    from examples.t_factory import hugr

    validate(hugr)
