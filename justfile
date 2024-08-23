# List the available commands
help:
    @just --list --justfile {{justfile()}}

# Prepare the environment for development, installing all the dependencies and
# setting up the pre-commit hooks.
setup:
    uv sync
    [[ -n "${JUST_INHIBIT_GIT_HOOKS:-}" ]] || uv run pre-commit install -t pre-commit

# Prepare the environment for development, including the extra dependency groups.
setup-extras:
    uv sync --extra pytket --extra validation --extra execution --inexact

# Run the pre-commit checks.
check:
    uv run pre-commit run --all-files

# Run all the tests.
test:
    uv run pytest

# Auto-fix all clippy warnings.
fix:
    uv run ruff check --fix guppylang

# Format the code.
format:
    uv run ruff format guppylang

# Generate a test coverage report.
coverage:
    uv run pytest --cov=./ --cov-report=html

# Generate the documentation.
build-py-docs:
    cd hugr-py/docs && ./build.sh

# Package the code and store the wheels in the dist/ directory.
build-wheels:
    uvx --from build pyproject-build --installer uv
