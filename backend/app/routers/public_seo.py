"""
robots.txt and sitemap.xml for search engines.

Both are generated per request (cheap: one small query) so they always
match the site: pages an admin adds, hides or re-orders in the Pages
screen show up here with no redeploy. URLs are absolute and built from
the request's own scheme + host — behind the HTTPS reverse proxy that
means https://<public domain>, because uvicorn runs with
--proxy-headers (see install.sh) — so nothing here hardcodes a domain.

Page URLs are /<slug> (the public site reads the path on load — see
src/App.jsx), except the "contact" page, which is also /contact.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ContentPage

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
    base = _base_url(request)
    pages = db.scalars(
        select(ContentPage).where(ContentPage.is_visible.is_(True)).order_by(ContentPage.order)
    ).all()

    newest = max((p.updated_at for p in pages if p.updated_at), default=None)
    entries = [(f"{base}/", newest, "1.0")]
    entries += [(f"{base}/{p.slug}", p.updated_at, "0.8") for p in pages]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, updated, priority in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(loc)}</loc>")
        if updated:
            lines.append(f"    <lastmod>{updated.date().isoformat()}</lastmod>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return Response("\n".join(lines) + "\n", media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})
