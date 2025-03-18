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
    uv sync --extra pytket --group execution --inexact

# Run the pre-commit checks.
check:
    uv run pre-commit run --all-files

# Compile integration test binaries.
_prepare-test:
    # Build the validator binary if rust is installed. Otherwise, skip it.
    cargo build --release -p validator || true
    # Build the execution binary if rust is installed. Otherwise, skip it.
    uv run maturin develop -m execute_llvm/Cargo.toml --release || true

# Run the tests.
test *PYTEST_FLAGS: _prepare-test
    uv run pytest {{PYTEST_FLAGS}}

# Export the integration test cases to a directory.
export-integration-tests directory="guppy-exports": _prepare-test
    uv run pytest --export-test-cases="{{ directory }}"

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
build-docs:
    cd docs && ./build.sh

# Package the code and store the wheels in the dist/ directory.
build-wheels:
    uvx --from build pyproject-build --installer uv

# Run benchmarks using pytest-benchmark.
bench *PYTEST_FLAGS:
    uv run pytest --benchmark-only {{PYTEST_FLAGS}}

# Run benchmarks and save JSON data to path/name.json.
bench_save path name:
    uv run pytest --benchmark-only --benchmark-storage={{path}} --benchmark-save={{name}}
