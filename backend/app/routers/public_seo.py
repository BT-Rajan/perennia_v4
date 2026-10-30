"""
robots.txt and sitemap.xml for search engines.

Both are generated per request (cheap: one small query) so they always
match the site: pages an admin adds, hides or re-orders in the Pages
screen show up here with no redeploy. URLs are absolute and built from
the request's own scheme + host — behind the HTTPS reverse proxy that
means https://<public domain>, because uvicorn runs with
--proxy-headers (see install.sh) — so nothing here hardcodes a domain.

Page URLs are /<slug> in English and /ar/<slug> in Arabic (the public
site reads the path on load — see src/seo/pageMeta.js).
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ContentPage
from app.seo_render import SERVICE_PAGES, page_path
from app.settings_service import get_setting

router = APIRouter(tags=["public-seo"])


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("/robots.txt", include_in_schema=False)
def robots_txt(request: Request) -> PlainTextResponse:
    base = _base_url(request)
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /api/",
        "",
        f"Sitemap: {base}/sitemap.xml",
        "",
    ])
    return PlainTextResponse(body, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml(request: Request, db: Session = Depends(get_db)) -> Response:
    """Every visible page in every language (English at /<slug>, Arabic
    at /ar/<slug>), each with its hreflang alternates so search engines
    pair the translations."""
    base = _base_url(request)
    languages = get_setting(db, "locale.supported_languages") or ["en", "ar"]
    pages = db.scalars(
        select(ContentPage).where(ContentPage.is_visible.is_(True)).order_by(ContentPage.order)
    ).all()

    newest = max((p.updated_at for p in pages if p.updated_at), default=None)
    entries = [("", newest, "1.0")]
    entries += [(p.slug, p.updated_at, "0.9" if p.slug in SERVICE_PAGES else "0.8") for p in pages]

    def loc(lang: str, slug: str) -> str:
        return escape(base + page_path(lang, slug, languages[0]))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for slug, updated, priority in entries:
        for lang in languages:
            lines.append("  <url>")
            lines.append(f"    <loc>{loc(lang, slug)}</loc>")
            for alt in languages:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{alt}" href="{loc(alt, slug)}"/>')
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{loc(languages[0], slug)}"/>')
            if updated:
                lines.append(f"    <lastmod>{updated.date().isoformat()}</lastmod>")
            lines.append(f"    <priority>{priority}</priority>")
            lines.append("  </url>")
    lines.append("</urlset>")
    return Response("\n".join(lines) + "\n", media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})
