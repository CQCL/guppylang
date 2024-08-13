"""Tests validating the files in the `examples` directory."""


def test_random_walk_qpe(validate):
    from examples.random_walk_qpe import hugr

    validate(hugr)


def test_t_factory(validate):
    from examples.t_factory import hugr

    validate(hugr)
