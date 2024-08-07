# Guppy

[![pypi][]](https://pypi.org/project/guppylang/)
[![codecov][]](https://codecov.io/gh/CQCL/guppylang)
[![py-version][]](https://pypi.org/project/guppylang/)

  [codecov]: https://img.shields.io/codecov/c/gh/CQCL/guppylang?logo=codecov
  [py-version]: https://img.shields.io/pypi/pyversions/guppylang
  [pypi]: https://img.shields.io/pypi/v/guppylang

Guppy is a quantum programming language that is fully embedded into Python.
It allows you to write high-level hybrid quantum programs with classical control flow and mid-circuit measurements using Pythonic syntax:

```python
from guppylang import guppy, qubit, quantum

guppy.load(quantum)

# Teleports the state in `src` to `tgt`.
@guppy
def teleport(src: qubit, tgt: qubit) -> qubit:
   # Create ancilla and entangle it with src and tgt
   tmp = qubit()
   tmp, tgt = cx(h(tmp), tgt)
   src, tmp = cx(src, tmp)

   # Apply classical corrections
   if measure(h(src)):
      tgt = z(tgt)
   if measure(tmp):
      tgt = x(tgt)
   return tgt
```

More examples and tutorials are available [here][examples].

[examples]: ./examples/


## Install

Guppy can be installed via `pip`. Requires Python >= 3.10.

```sh
pip install guppylang
```


## Usage

See the [Getting Started][getting-started] guide and the other [examples].

[getting-started]: ./examples/1-Getting-Started.md


## Development

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python >= 3.10
- [Poetry](https://python-poetry.org/docs/#installation)
- [Rust](https://www.rust-lang.org/tools/install) >= 1.75.0  (only needed for tests)

### Installing

Run the following to setup your virtual environment and install dependencies:

```sh
poetry install --with execution,validation
```

Note that the `--with execution,validation` flag is optional and only needed to run integration tests.

The `validation` flag allows the tests to validate that the hugrs guppy outputs are well formed, and the `execution` flag allows tests to compile these hugrs to native code using [hugr-llvm](https://github.com/CQCL/hugr-llvm) to check the results are as expected.
This requires `llvm-14` as described in the `hugr-llvm` repo.

You can then activate the virtual environment and work within it with:

```sh
poetry shell
```

Consider using [direnv](https://github.com/direnv/direnv/wiki/Python#poetry) to
automate this when entering and leaving a directory.

To run a single command in the shell, just prefix it with `poetry run`.

### Pre-commit

Install the pre-commit hook by running:

```sh
poetry run pre-commit install
```


### Testing

Run tests using

```sh
poetry run pytest -v
```

You have to install extra dependencies to test automatic circuit conversion from `pytket`:

```sh
poetry install --with pytket
poetry run pytest -v  # Now rerun tests
```


Integration test cases can be exported to a directory using

```sh
poetry run pytest --export-test-cases=guppy-exports
```

which will create a directory `./guppy-exports` populated with hugr modules serialised in JSON.

### Experimental: Execution

See the [guppy-runner](https://github.com/CQCL/guppy-runner) repository for in-progress work for compiling Guppy source programs and executing them.

## License

This project is licensed under Apache License, Version 2.0 ([LICENCE][] or http://www.apache.org/licenses/LICENSE-2.0).

  [LICENCE]: ./LICENCE
