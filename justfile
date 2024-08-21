# List the available commands
help:
    @just --list --justfile {{justfile()}}

# Prepare the environment for development, installing all the dependencies and
# setting up the pre-commit hooks.
setup:
    poetry install
    [[ -n "${JUST_INHIBIT_GIT_HOOKS:-}" ]] || poetry run pre-commit install -t pre-commit

# Run the pre-commit checks.
check:
    poetry run pre-commit run --all-files

# Run all the tests.
test:
    poetry run pytest

# Auto-fix all clippy warnings.
fix:
    poetry run ruff check --fix guppylang

# Format the code.
format:
    poetry run ruff format guppylang

# Generate a test coverage report.
coverage:
    poetry run pytest --cov=./ --cov-report=html

# Load a shell with all the dependencies installed
shell:
    poetry shell


build-py-docs:
    cd hugr-py/docs && ./build.sh
