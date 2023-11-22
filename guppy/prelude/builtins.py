"""Guppy module for builtin types and operations."""

from guppy.module import GuppyModule


builtins = GuppyModule("builtins", import_builtins=False)
