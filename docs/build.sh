#!/bin/sh

mkdir build

touch build/.nojekyll  # Disable jekyll to keep files starting with underscores

uv run --extra docs sphinx-build -b html ./api-docs ./build/api-docs
