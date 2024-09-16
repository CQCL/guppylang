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

guppy.load_all(quantum)


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

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Rust](https://www.rust-lang.org/tools/install) >= 1.75.0  (only needed for tests)

### Installing

Run the following to setup your virtual environment and install dependencies:

```sh
uv sync --extra execution
cargo build --release  # Builds the validator (optional)
```

Note that the `--extra` flag, and the `cargo build` line, are both optional, but enable some integration tests.

The validator allows the tests to validate that the hugrs guppy outputs are well formed, and the `execution` extra allows tests to compile these hugrs to native code using [hugr-llvm](https://github.com/CQCL/hugr-llvm) to check the results are as expected.
This requires `llvm-14` as described in the `hugr-llvm` repo.

Consider using [direnv](https://direnv.net/docs/installation.html) to
automate this when entering and leaving a directory.

To run a single command in the shell, just prefix it with `uv run`.

### Pre-commit

Install the pre-commit hook by running:

```sh
uv run pre-commit install
```


### Testing

Run tests using

```sh
uv run pytest [-v]  # -v just enables verbose test output
```

(If you have not built the validator, you can do `uv run pytest --no_validation`.)

You have to install extra dependencies to test automatic circuit conversion from `pytket`.

```sh
# Install extra dependencies
# Using `--inexact` to avoid removing the already installed extras.
uv sync --extra pytket --inexact
# Now rerun tests
uv run pytest -v
```


Integration test cases can be exported to a directory using

```sh
uv run pytest --export-test-cases=guppy-exports
```

which will create a directory `./guppy-exports` populated with hugr modules serialised in JSON.

### Experimental: Execution

See the [guppy-runner](https://github.com/CQCL/guppy-runner) repository for in-progress work for compiling Guppy source programs and executing them.

## License

This project is licensed under Apache License, Version 2.0 ([LICENCE][] or http://www.apache.org/licenses/LICENSE-2.0).

  [LICENCE]: ./LICENCE
