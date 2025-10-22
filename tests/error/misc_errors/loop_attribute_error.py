from guppylang import guppy

@guppy
def foo() -> None:
    for i in range(
        a
    ): # Really really really really long comment to cause linter to split line
        pass


foo.compile()
