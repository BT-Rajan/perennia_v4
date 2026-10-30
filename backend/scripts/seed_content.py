#!/usr/bin/env python3
"""
One-time content seed: reads the content shared with the frontend's
bundled fallback (../src/content: the page .md files, pages.json,
faq.json, and site-copy.json via the copy.* registry defaults) and
writes it into the DB as the initial admin-editable content. After this runs, the DB rows
are authoritative — this script is what performs the migration, not
something the running app depends on.

Safe to re-run: skips any page/FAQ item/setting that already has a DB
override, so it never clobbers an admin's edits.

    python scripts/seed_content.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base, engine, session_scope
from app.models import ContentPage, FaqItem, SiteSetting
from app import content_service
from app.settings_registry import get_def
from app.settings_service import set_many

FRONTEND_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "content"

# Page records (nav label, section summary, tagline; order and nav
# visibility) and the FAQ are shared with the frontend's bundled
# fallback (src/data/content.js), so a fresh install starts with exactly
# what the site shows without a backend. Page bodies are the .md files.
PAGES = json.loads((FRONTEND_CONTENT_DIR / "pages.json").read_text(encoding="utf-8"))
FAQ_SEED = json.loads((FRONTEND_CONTENT_DIR / "faq.json").read_text(encoding="utf-8"))

# Fields added after a page may already exist in the DB: filled in on
# existing pages when empty there, never overwritten.
FILL_IF_EMPTY = ("seo_title", "seo_description")

# Copy blobs: their registry defaults, which are read from
# src/content/site-copy.json (see app/settings_registry.py).
COPY_KEYS = ("copy.home", "copy.chat", "copy.booking")


def _read_md(lang: str, slug: str) -> str:
    path = FRONTEND_CONTENT_DIR / lang / f"{slug}.md"
    if not path.exists():
        print(f"  WARNING: {path} not found, leaving body_markdown empty for {slug}/{lang}")
        return ""
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with session_scope() as db:
        # --- pages ---
        for order, record in enumerate(PAGES):
            slug, show_in_nav = record["slug"], record["show_in_nav"]
            per_lang = {k: v for k, v in record.items() if k not in ("slug", "show_in_nav")}
            existing = db.get(ContentPage, slug)
            if existing is not None:
                # Fill only empty SEO fields on existing pages; never
                # overwrite anything an admin has written.
                merged = {lang: dict(fields) for lang, fields in (existing.translations or {}).items()}
                filled = []
                for lang, fields in per_lang.items():
                    target = merged.setdefault(lang, {})
                    for key in FILL_IF_EMPTY:
                        if fields.get(key) and not (target.get(key) or "").strip():
                            target[key] = fields[key]
                            filled.append(f"{lang}.{key}")
                if filled:
                    content_service.upsert_page(db, slug, translations=merged, actor_id=None,
                                                 actor_username="seed_script")
                    print(f"Page '{slug}' exists — filled {', '.join(filled)}.")
                else:
                    print(f"Page '{slug}' already exists — skipping.")
                continue
            translations = {
                lang: {**fields, "body_markdown": _read_md(lang, slug)}
                for lang, fields in per_lang.items()
            }
            content_service.upsert_page(db, slug, translations=translations, order=order,
                                         show_in_nav=show_in_nav,
                                         actor_id=None, actor_username="seed_script")
            print(f"Seeded page '{slug}'.")

        # --- FAQ ---
        if db.query(FaqItem).count() == 0:
            for order, translations in enumerate(FAQ_SEED):
                content_service.create_faq(db, translations=translations, order=order,
                                            actor_id=None, actor_username="seed_script")
            print(f"Seeded {len(FAQ_SEED)} FAQ items.")
        else:
            print("FAQ items already exist — skipping.")

        # --- copy blobs ---
        to_set = {}
        for key in COPY_KEYS:
            if db.get(SiteSetting, key) is None:
                to_set[key] = get_def(key).default
            else:
                print(f"Setting '{key}' already overridden — skipping.")
        if to_set:
            set_many(db, to_set, actor_id=None, actor_username="seed_script")
            print(f"Seeded copy blobs: {list(to_set)}.")

        # --- contact phone: fill in if still empty ---
        phone = db.get(SiteSetting, "contact.phone")
        if phone is not None and not phone.value.strip('" '):
            set_many(db, {"contact.phone": get_def("contact.phone").default},
                     actor_id=None, actor_username="seed_script")
            print("Set contact.phone (was empty).")

        # --- logo: move off the old placeholder default ---
        # Only when the stored value is exactly the old placeholder; a logo
        # an admin chose in Settings is left alone.
        logo = db.get(SiteSetting, "branding.logo_url")
        if logo is not None and logo.value.strip('"') == "/static/logo.svg":
            set_many(db, {"branding.logo_url": get_def("branding.logo_url").default},
                     actor_id=None, actor_username="seed_script")
            print("Updated branding.logo_url from the old placeholder to the Perennia logo.")


if __name__ == "__main__":
    main()
