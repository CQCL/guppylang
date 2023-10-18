# Guppy

## About

TODO

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python >=3.10

### Installing

Setup your virtual environment and install dependencies:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install a local development version using:

```sh
pip install -e '.[dev]'
```

### Git blame

You can configure Git to ignore formatting commits when using `git blame` by running 
```sh
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

## Usage

TODO

## Testing

First, build the PyO3 Hugr validation library using
```sh
maturin develop
```

from the `validator` directory.

Run tests using
```sh
pytest -v
```

Integration test cases can be exported to a directory using

```sh
pytest --export-test-cases=guppy-exports

```
which will create a directory `./guppy-exports` populated with hugr modules serialised in msgpack.

## Packaging

```sh
python -m build -n
```
