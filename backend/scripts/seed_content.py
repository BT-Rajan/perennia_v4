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

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base, engine, session_scope
from app.models import ContentPage, FaqItem, SiteSetting
from app import content_service
from app.settings_registry import get_def
from app.settings_service import get_setting, set_many

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

# Bodies earlier versions of this repo shipped, as sha256 of the stripped
# text (see _body_hash). A page whose body is still one of these was
# never edited, so it is safely updated to the current .md file. Add the
# old hash here whenever a bundled page body changes and live sites
# should get the new text.
PREVIOUS_BODIES = {
    # Solutions, before the links to the service pages were added.
    "services": {
        "en": {
            "7e4042cda804981f3f7dc1715877fd9aa1c4da17a84e5a12f41d1faf92c79b64",
            "8f375a96c30f8f47ff94dd7767535a9acfdd9ca211c9120c2ab17e211917c28f",
            "389c5aa73495d8b97fa0fda535b714fbe90084e0441e8cf26c426d01291ae252",
        },
        "ar": {
            "f235ac48e7669724c6559407e3774d1b95198ffe8cf66c9147b9b1701e15da06",
            "48b1929955744a287e3ef0eca08ba008978db79d9c88e21f70c4783363ad5584",
            "04f4f0295ef652ecd57e052899243a9064797ed2119075b7c8e9b99b350c5128",
        },
    },
}


def _body_hash(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").strip().encode("utf-8")).hexdigest()


# Copy fields earlier versions of this repo shipped. A saved value that is
# still exactly one of these was never edited, so on deploy it is updated
# to the current default; edited values are kept.
PREVIOUS_COPY = {
    # Homepage headline and supporting line, before the search keywords.
    "copy.home": {
        "en": {
            "tagline_line1": {"Technology that moves"},
            "tagline_line2": {"your business forward."},
            "supporting_text": {"Perennia helps GCC businesses adopt, build and scale technology — from their first digital initiative to practical AI and larger-scale transformation."},
        },
        "ar": {
            "tagline_line1": {"تقنية تدفع"},
            "tagline_line2": {"أعمالك إلى الأمام."},
            "supporting_text": {"تساعد بيرينيا الشركات في دول الخليج على تبنّي التقنية وبنائها وتوسيعها — من أول مبادرة رقمية إلى الذكاء الاصطناعي العملي والتحول على نطاق أوسع."},
        },
    },
}


# Fields that read as one sentence: updated together or not at all, so an
# edited first line never ends up next to a new second line.
COPY_FIELD_GROUPS = (("tagline_line1", "tagline_line2"),)


def _upgrade_copy(key: str, saved: dict) -> list[str]:
    """Update, in place, fields of a saved copy blob still holding a
    previously shipped value. Returns what changed / was kept."""
    default = get_def(key).default
    report = []
    for lang, fields in PREVIOUS_COPY.get(key, {}).items():
        blob = saved.setdefault(lang, {})
        new = default.get(lang, {})
        groups = [g for g in COPY_FIELD_GROUPS if set(g) <= set(fields)]
        groups += [(f,) for f in fields if not any(f in g for g in groups)]
        for group in groups:
            if all(blob.get(f) == new.get(f) for f in group):
                continue  # already current
            if all(blob.get(f) in fields[f] and new.get(f) for f in group):
                for f in group:
                    blob[f] = new[f]
                report.append(f"updated {lang}.{'+'.join(group)}")
            else:
                report.append(f"kept edited {lang}.{'+'.join(group)}")
    return report


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
                # Fill only empty SEO fields, and update a body only if it
                # is still exactly a text this repo shipped before (nobody
                # has edited it); never overwrite anything an admin wrote.
                merged = {lang: dict(fields) for lang, fields in (existing.translations or {}).items()}
                filled = []
                for lang, fields in per_lang.items():
                    target = merged.setdefault(lang, {})
                    for key in FILL_IF_EMPTY:
                        if fields.get(key) and not (target.get(key) or "").strip():
                            target[key] = fields[key]
                            filled.append(f"{lang}.{key}")
                    body = _read_md(lang, slug)
                    current = target.get("body_markdown") or ""
                    if body and current != body and _body_hash(current) in PREVIOUS_BODIES.get(slug, {}).get(lang, ()):
                        target["body_markdown"] = body
                        filled.append(f"{lang}.body_markdown (updated to the current text)")
                    elif slug in PREVIOUS_BODIES and current and current.strip() != body:
                        print(f"  Page '{slug}' ({lang}) was edited in the admin panel — body left as is.")
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
                continue
            saved = copy.deepcopy(get_setting(db, key) or {})
            report = _upgrade_copy(key, saved)
            if any(r.startswith("updated") for r in report):
                to_set[key] = saved
            print(f"Setting '{key}' already overridden — {', '.join(report) if report else 'skipping'}.")
        if to_set:
            set_many(db, to_set, actor_id=None, actor_username="seed_script")
            print(f"Saved copy blobs: {list(to_set)}.")

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
