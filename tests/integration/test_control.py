from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


def test_dagger(validate):
    @guppy
    def main() -> None:
        with (dagger, dagger, dagger, control(q)):
            pass

    #   print("  main = ", main)

    validate(main.compile())
    assert (0 == 1)


def test_control(validate):
    @guppy
    def main(q: qubit) -> qubit:
        with control(q):
            return

    validate(main.compile())

def test_as_not_defined(validate):
    @guppy
    def main(q: qubit) -> qubit:
        with dagger as c:
            return c
    validate(main.compile())

def test_return_in_with(validate):
    @guppy
    def main() -> None:
        with dagger:
            return
    validate(main.compile())
