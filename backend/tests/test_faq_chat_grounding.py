"""
Covers content_service.build_faq_prompt_block and its wiring into
chat_service._build_system_prompt — the fix that lets the assistant
actually draw on admin-managed FAQ items instead of them only being
visible in the admin panel.
"""
from __future__ import annotations

import pytest

from app import chat_service, content_service
from app.db import session_scope
from app.models import FaqItem


@pytest.fixture(autouse=True)
def _clear_faq_items():
    """The suite's schema is created once and never reset between
    tests (see conftest.py), so without this, FAQ items created by
    one test in this file would leak into the next and break the
    "no active items" / exact-content assertions below."""
    with session_scope() as db:
        for item in db.query(FaqItem).all():
            db.delete(item)
    yield
    with session_scope() as db:
        for item in db.query(FaqItem).all():
            db.delete(item)


def _make_faq(db, *, q_en, a_en, q_ar=None, a_ar=None, is_active=True):
    translations = {"en": {"q": q_en, "a": a_en}}
    if q_ar and a_ar:
        translations["ar"] = {"q": q_ar, "a": a_ar}
    return content_service.create_faq(
        db, translations=translations, is_active=is_active, actor_id=None, actor_username="test"
    )


def test_build_faq_prompt_block_includes_active_items():
    with session_scope() as db:
        _make_faq(db, q_en="Do you work with startups?", a_en="Yes, we work with startups and enterprises alike.")
        _make_faq(db, q_en="Where are you based?", a_en="India, serving clients across India and the GCC.")
        db.flush()

        block = content_service.build_faq_prompt_block(db, "en")

    assert "FREQUENTLY ASKED QUESTIONS" in block
    assert "Do you work with startups?" in block
    assert "Yes, we work with startups and enterprises alike." in block
    assert "Where are you based?" in block


def test_build_faq_prompt_block_excludes_inactive_items():
    with session_scope() as db:
        _make_faq(db, q_en="Active question?", a_en="Active answer.", is_active=True)
        _make_faq(db, q_en="Retired question?", a_en="Retired answer.", is_active=False)
        db.flush()

        block = content_service.build_faq_prompt_block(db, "en")

    assert "Active question?" in block
    assert "Retired question?" not in block


def test_build_faq_prompt_block_falls_back_to_english_for_untranslated_language():
    with session_scope() as db:
        _make_faq(db, q_en="English only question?", a_en="English only answer.")
        db.flush()

        block = content_service.build_faq_prompt_block(db, "ar")

    # No Arabic translation was given, so the English Q/A should still
    # surface rather than the item silently disappearing for Arabic
    # visitors.
    assert "English only question?" in block
    assert "English only answer." in block


def test_build_faq_prompt_block_empty_when_no_active_items():
    with session_scope() as db:
        block = content_service.build_faq_prompt_block(db, "en")
    assert block == ""


def test_faq_block_is_woven_into_system_prompt():
    with session_scope() as db:
        _make_faq(db, q_en="What is your refund policy?", a_en="We offer a 14-day money-back guarantee.")
        db.flush()

        prompt = chat_service._build_system_prompt(
            db, lang="en", turns_used=1, max_turns=20, lead_captured=True, booking_enabled=False,
        )

    assert "What is your refund policy?" in prompt
    assert "14-day money-back guarantee" in prompt
