"""The SPA catch-all routes must never serve a file outside dist/.

An encoded "../" ("..%2f") reaches the route already decoded, so
/static/..%2f..%2fbackend/.env used to return the backend's secrets.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.main import ADMIN_DIST, PUBLIC_DIST, _built_file

SECRET_NAME = ".env.traversal_canary"


@pytest.fixture
def canary():
    path = Path(__file__).resolve().parent.parent / SECRET_NAME
    path.write_text("SECRET_KEY=canary\n", encoding="utf-8")
    yield path
    path.unlink()


@pytest.mark.parametrize("root", [PUBLIC_DIST, ADMIN_DIST])
@pytest.mark.parametrize("rel", [
    f"../backend/{SECRET_NAME}",
    f"../../backend/{SECRET_NAME}",
    f"static/../../backend/{SECRET_NAME}",
    f"assets/../../../backend/{SECRET_NAME}",
])
def test_built_file_rejects_paths_outside_root(canary, root, rel):
    assert _built_file(root, rel) is None


def test_built_file_serves_files_inside_root(tmp_path):
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "logo.svg").write_text("<svg/>", encoding="utf-8")
    assert _built_file(tmp_path, "static/logo.svg") == (tmp_path / "static" / "logo.svg").resolve()
    assert _built_file(tmp_path, "") is None
    assert _built_file(tmp_path, "static") is None  # a directory, not a file
