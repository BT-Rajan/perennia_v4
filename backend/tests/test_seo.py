"""robots.txt and sitemap.xml (app/routers/public_seo.py)."""
from __future__ import annotations

from app import content_service
from app.db import session_scope

_T = {"en": {"nav_label": "X", "section_title": "X", "section_body": "X", "body_markdown": "x"}}


def test_robots_points_to_sitemap_and_hides_admin(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "Disallow: /admin" in r.text
    assert "Disallow: /api/" in r.text
    assert "Sitemap: http://testserver/sitemap.xml" in r.text


def test_sitemap_lists_home_and_visible_pages_only(client):
    with session_scope() as db:
        content_service.upsert_page(db, "seo-visible-page", translations=_T, order=90,
                                    actor_id=None, actor_username="test")
        content_service.upsert_page(db, "seo-hidden-page", translations=_T, order=91, is_visible=False,
                                    actor_id=None, actor_username="test")

    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<loc>http://testserver/</loc>" in r.text
    assert "<loc>http://testserver/seo-visible-page</loc>" in r.text
    assert "seo-hidden-page" not in r.text
    assert "<lastmod>" in r.text


def test_index_html_placeholders_filled_and_escaped(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    (tmp_path / "index.html").write_text(
        '<link rel="canonical" href="__PAGE_URL__"><meta property="og:image" content="__SITE_URL__/x.png">'
    )
    monkeypatch.setattr(main, "PUBLIC_DIST", tmp_path)
    with TestClient(main.create_app()) as c:
        r = c.get("/about")
        assert '<link rel="canonical" href="http://testserver/about">' in r.text
        assert 'content="http://testserver/x.png"' in r.text
        r = c.get('/a"><script>')
        assert "<script>" not in r.text
