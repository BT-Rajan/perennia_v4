"""Status codes and headers of the single-port SPA serving (app/main.py).

Needs a built public site (dist/); skipped otherwise, since the SPA
routes are only registered when it exists.
"""
from __future__ import annotations

import pytest

from app.main import PUBLIC_DIST

pytestmark = pytest.mark.skipif(not (PUBLIC_DIST / "index.html").is_file(), reason="public site not built")


def test_known_pages_are_200_and_indexable(client):
    for path in ("/", "/privacy", "/terms"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert 'content="index, follow"' in r.text
        assert r.headers["cache-control"] == "no-cache"


def test_unknown_page_is_404_noindex_but_still_renders(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404
    assert 'id="root"' in r.text
    assert '<meta name="robots" content="noindex" />' in r.text


def test_unknown_api_path_is_json_404(client):
    for path in ("/api/no-such-endpoint", "/admin/api/no-such-endpoint"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.headers["content-type"].startswith("application/json")


def test_head_is_allowed(client):
    assert client.head("/").status_code == 200


def test_hashed_assets_are_immutable(client):
    asset = next((PUBLIC_DIST / "assets").glob("*.js"))
    r = client.get(f"/assets/{asset.name}")
    assert r.status_code == 200
    assert "immutable" in r.headers["cache-control"]


def test_security_headers(client):
    h = client.get("/").headers
    assert h["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert "microphone=(self)" in h["permissions-policy"]
