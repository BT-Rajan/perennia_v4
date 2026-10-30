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


INDEX = """<!doctype html><html lang="en"><head>
<!-- seo:head --><title>fallback</title><!-- /seo:head -->
<link rel="stylesheet" href="./assets/app.css"></head>
<body><div id="root"></div>
<script type="module" src="./assets/app.js"></script></body></html>"""

_SERVICE = {
    "en": {"nav_label": "Software Development", "section_title": "Custom Software Development in Kuwait",
           "section_body": "Custom software for Kuwait.", "seo_title": "Custom Software Development Company in Kuwait",
           "seo_description": "We build custom software in Kuwait.",
           "body_markdown": "# Custom Software\n\nIntro <b>bold</b> text.\n\n## Frequently asked questions\n\n"
                            "### How long does it take?\n\nAbout 30 days.\n\n[[cta]]"},
    "ar": {"nav_label": "تطوير البرمجيات", "section_title": "تطوير البرمجيات المخصصة في الكويت",
           "section_body": "برمجيات مخصصة.", "body_markdown": "# تطوير البرمجيات\n\nنص."},
}


def _app_with_index(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    monkeypatch.setattr(main, "PUBLIC_DIST", tmp_path)
    return TestClient(main.create_app())


def test_each_page_gets_its_own_head_and_content(tmp_path, monkeypatch):
    with session_scope() as db:
        content_service.upsert_page(db, "software-development", translations=_SERVICE, order=1,
                                    show_in_nav=False, actor_id=None, actor_username="test")
    with _app_with_index(tmp_path, monkeypatch) as c:
        r = c.get("/software-development")
        assert r.status_code == 200
        assert "<title>Custom Software Development Company in Kuwait</title>" in r.text
        assert 'content="We build custom software in Kuwait."' in r.text
        assert '<link rel="canonical" href="http://testserver/software-development" />' in r.text
        assert 'hreflang="ar" href="http://testserver/ar/software-development"' in r.text
        assert "<h1>Custom Software</h1>" in r.text            # page body rendered for crawlers
        assert "&lt;b&gt;bold&lt;/b&gt;" in r.text             # page HTML is escaped
        assert '"@type": "Service"' in r.text and '"@type": "FAQPage"' in r.text
        assert '"name": "How long does it take?"' in r.text
        assert 'href="/assets/app.css"' in r.text and 'src="/assets/app.js"' in r.text

        r = c.get("/ar/software-development")
        assert r.status_code == 200
        assert '<html lang="ar" dir="rtl"' in r.text
        # no seo_title in Arabic: falls back to the section title
        assert "<title>تطوير البرمجيات المخصصة في الكويت | " in r.text
        assert '<link rel="canonical" href="http://testserver/ar/software-development" />' in r.text


def test_unknown_page_is_404_noindex_and_request_text_is_escaped(tmp_path, monkeypatch):
    with _app_with_index(tmp_path, monkeypatch) as c:
        r = c.get('/a"><script>alert(1)</script>')
        assert r.status_code == 404
        assert '<meta name="robots" content="noindex" />' in r.text
        assert "<script>alert(1)" not in r.text


def test_sitemap_lists_both_languages_with_alternates(client):
    with session_scope() as db:
        content_service.upsert_page(db, "seo-alt-page", translations=_T, order=92,
                                    actor_id=None, actor_username="test")
    r = client.get("/sitemap.xml")
    assert "<loc>http://testserver/ar/seo-alt-page</loc>" in r.text
    assert 'hreflang="ar" href="http://testserver/ar/seo-alt-page"' in r.text
    assert 'hreflang="x-default" href="http://testserver/seo-alt-page"' in r.text


def test_markdown_renderer_and_faq_extraction():
    from app.seo_render import extract_faq, markdown_to_html

    html = markdown_to_html("## Hi\n\n- **a**\n- [b](/x)\n\n[c](javascript:alert(1))\n\n[[workflow: A → B]]",
                            cta_label="Book", cta_href="/contact")
    assert "<h2>Hi</h2>" in html and "<strong>a</strong>" in html and '<a href="/x">b</a>' in html
    assert "javascript:" not in html                        # unsafe link schemes dropped
    assert "<ol><li>A</li><li>B</li></ol>" in html
    assert extract_faq("## الأسئلة الشائعة\n\n### س؟\n\nج.") == [("س؟", "ج.")]
