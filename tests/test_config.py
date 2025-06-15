import sys
from pathlib import Path

# Allow importing modules from the fastapi_app directory
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "fastapi_app"))

from config import BASE_DIR, make_path_relative, resolve_file_path


def test_make_path_relative_absolute_under_base():
    abs_path = BASE_DIR / "data" / "example.txt"
    result = make_path_relative(str(abs_path))
    assert Path(result) == Path("data/example.txt")


def test_make_path_relative_absolute_outside_base(tmp_path):
    outside = tmp_path / "outside.txt"
    result = make_path_relative(str(outside))
    assert result == str(outside)


def test_make_path_relative_relative_path():
    rel_path = "data/sample.txt"
    assert make_path_relative(rel_path) == rel_path


def test_resolve_file_path_absolute(tmp_path):
    abs_path = tmp_path / "absolute.txt"
    resolved = resolve_file_path(str(abs_path))
    assert resolved == abs_path


def test_resolve_file_path_relative():
    rel_path = "data/sample.txt"
    resolved = resolve_file_path(rel_path)
    assert resolved == BASE_DIR / rel_path
