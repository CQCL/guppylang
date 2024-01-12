# Guppy

## About

TODO

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python >=3.10

### Installing


First make sure poetry [is
installed](https://python-poetry.org/docs/#installation).

Then run the following to setup your virtual environment and install dependencies:

```sh
poetry install
```

You can then activate the virtual environment and work within it with:

```sh
poetry shell
```

Consider using [direnv](https://github.com/direnv/direnv/wiki/Python#poetry) to
automate this when entering and leaving a directory.

To run a single command in the shell, just prefix it with `poetry run`.


### Git blame

You can configure Git to ignore formatting commits when using `git blame` by running

```sh
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

## Usage

TODO

## Testing

First, build the PyO3 Hugr validation library from the `validator` directory using

```sh
maturin develop
```

Run tests using

```sh
poetry run pytest -v
```

Integration test cases can be exported to a directory using

```sh
poetry run pytest --export-test-cases=guppy-exports

```

which will create a directory `./guppy-exports` populated with hugr modules serialised in msgpack.

## Packaging

```sh
poetry build
```

## License

This project is licensed under Apache License, Version 2.0 ([LICENSE][] or http://www.apache.org/licenses/LICENSE-2.0).

  [LICENSE]: ./LICENSE
