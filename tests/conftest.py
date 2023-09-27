import pytest
from pathlib import Path
import argparse

def pytest_addoption(parser):
    def dir_path(s):
        path = Path(s)
        if not path.exists() or path.is_dir():
            return path
        raise argparse.ArgumentTypeError(f"export-test-cases dir:{path} exists and is not a directory")

    parser.addoption("--export-test-cases", action="store", type=dir_path, help="A directory to which to export test cases")
