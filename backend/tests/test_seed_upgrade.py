"""scripts/seed_content.py updates a page body only while it is still a
text the repo shipped before, never one edited in the admin panel."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from app import content_service
from app.db import session_scope
from app.models import ContentPage

SEED = Path(__file__).resolve().parent.parent / "scripts" / "seed_content.py"


def _load_seed():
    spec = importlib.util.spec_from_file_location("seed_content", SEED)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _page(body_en, body_ar):
    base = {"nav_label": "Solutions", "section_title": "Solutions", "section_body": "x"}
    return {"en": {**base, "body_markdown": body_en}, "ar": {**base, "body_markdown": body_ar}}


def test_unedited_body_is_upgraded_and_edited_body_is_kept(monkeypatch):
    seed = _load_seed()
    monkeypatch.setattr(seed, "PREVIOUS_BODIES", {"services": {
        "en": {seed._body_hash("old shipped text")}, "ar": {seed._body_hash("old shipped text")},
    }})
    with session_scope() as db:
        content_service.upsert_page(db, "services", translations=_page("old shipped text\r\n", "edited by an admin"),
                                    order=0, actor_id=None, actor_username="test")

    seed.main()

    with session_scope() as db:
        t = db.get(ContentPage, "services").translations
        assert t["en"]["body_markdown"] == seed._read_md("en", "services")   # unedited: upgraded
        assert "/software-development" in t["en"]["body_markdown"]
        assert t["ar"]["body_markdown"] == "edited by an admin"               # edited: kept


def test_homepage_headline_upgrades_as_a_pair_and_keeps_edits():
    from app.settings_registry import get_def
    from app.settings_service import get_setting, set_many

    seed = _load_seed()
    old = {lang: {f: next(iter(v)) for f, v in fields.items()} for lang, fields in seed.PREVIOUS_COPY["copy.home"].items()}
    saved = {lang: dict(get_def("copy.home").default[lang]) for lang in ("en", "ar")}
    for lang in ("en", "ar"):
        saved[lang].update(old[lang])
    saved["en"]["tagline_line1"] = "Our own headline"          # an admin edit
    with session_scope() as db:
        set_many(db, {"copy.home": saved}, actor_id=None, actor_username="test")

    seed.main()

    new = get_def("copy.home").default
    with session_scope() as db:
        home = get_setting(db, "copy.home")
    assert home["en"]["tagline_line1"] == "Our own headline"            # edit kept…
    assert home["en"]["tagline_line2"] == old["en"]["tagline_line2"]    # …with its own second line
    assert home["en"]["supporting_text"] == new["en"]["supporting_text"]
    assert home["ar"]["tagline_line1"] == new["ar"]["tagline_line1"]    # untouched: upgraded
    assert home["ar"]["tagline_line2"] == new["ar"]["tagline_line2"]
