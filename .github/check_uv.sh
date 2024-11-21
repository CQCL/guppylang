#!/bin/bash
# Ensure that the `uv` command is available and meets the minimum version requirement.

# Desired minimum version
MIN_VERSION="0.4.27"

# Get the version of `uv`
UV_VERSION=$(uv --version | awk '{print $2}')

# Function to compare versions
version_ge() {
  # Returns 0 (true) if $1 >= $2
  [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n 1)" == "$2" ]
}

# Compare versions
if version_ge "$UV_VERSION" "$MIN_VERSION"; then
  echo "uv version $UV_VERSION meets the minimum requirement ($MIN_VERSION)."
else
  echo "uv version $UV_VERSION does not meet the minimum requirement ($MIN_VERSION)."
  echo "Please upgrade uv by running `uv self update`, or by following the instructions in your package manager."
  exit 1
fi