"""Tests validating the files in the `examples` directory."""


def test_random_walk_qpe(validate):
    from examples.random_walk_qpe import hugr

    validate(hugr)
