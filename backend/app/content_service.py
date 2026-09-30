"""
Read/write access to structured content (pages, FAQ). Mirrors
settings_service.py's role for the settings registry: routers never
touch the ORM directly, everything goes through here so validation and
audit logging happen exactly once.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content_schema import FAQ_FIELDS, PAGE_FIELDS, validate_translations
from app.models import AuditLog, ContentPage, ContentPageVersion, FaqItem
from app.settings_service import get_setting


def _supported_languages(db: Session) -> list[str]:
    return get_setting(db, "locale.supported_languages")


# ── Content pages ────────────────────────────────────────────────────

def list_pages(db: Session, *, visible_only: bool) -> list[ContentPage]:
    stmt = select(ContentPage).order_by(ContentPage.order, ContentPage.slug)
    if visible_only:
        stmt = stmt.where(ContentPage.is_visible.is_(True))
    return list(db.scalars(stmt))


def get_page(db: Session, slug: str) -> ContentPage | None:
    return db.get(ContentPage, slug)


def upsert_page(
    db: Session, slug: str, *, translations: dict, order: int | None = None,
    is_visible: bool | None = None, show_in_nav: bool | None = None,
    actor_id: str | None, actor_username: str | None,
) -> ContentPage:
    validate_translations(PAGE_FIELDS, translations, supported_languages=_supported_languages(db))

    page = db.get(ContentPage, slug)
    if page is None:
        page = ContentPage(slug=slug, translations=translations, order=order or 0,
                            is_visible=is_visible if is_visible is not None else True,
                            show_in_nav=show_in_nav if show_in_nav is not None else True)
        db.add(page)
    else:
        # Snapshot the pre-edit state so this change is reversible.
        db.add(ContentPageVersion(slug=slug, translations=page.translations,
                                   saved_by=actor_id, saved_by_username=actor_username))
        page.translations = translations
        if order is not None:
            page.order = order
        if is_visible is not None:
            page.is_visible = is_visible
        if show_in_nav is not None:
            page.show_in_nav = show_in_nav
    page.updated_by = actor_id

    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="content_page.upsert", target=slug))
    return page


def delete_page(db: Session, slug: str, *, actor_id: str | None, actor_username: str | None) -> bool:
    page = db.get(ContentPage, slug)
    if page is None:
        return False
    db.delete(page)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="content_page.delete", target=slug))
    return True


def list_versions(db: Session, slug: str) -> list[ContentPageVersion]:
    stmt = select(ContentPageVersion).where(ContentPageVersion.slug == slug).order_by(ContentPageVersion.saved_at.desc())
    return list(db.scalars(stmt))


def rollback_page(db: Session, slug: str, version_id: str, *, actor_id: str | None, actor_username: str | None) -> ContentPage:
    version = db.get(ContentPageVersion, version_id)
    if version is None or version.slug != slug:
        raise KeyError(f"No version {version_id!r} for page {slug!r}")
    return upsert_page(db, slug, translations=version.translations, actor_id=actor_id, actor_username=actor_username)


def reorder_pages(db: Session, ordered_slugs: list[str], *, actor_id: str | None, actor_username: str | None) -> None:
    """Same pattern as reorder_faq: bulk-assign `order` from list position
    so the admin UI can drag-reorder pages without one PUT per row."""
    pages = {p.slug: p for p in db.scalars(select(ContentPage).where(ContentPage.slug.in_(ordered_slugs)))}
    missing = set(ordered_slugs) - set(pages)
    if missing:
        raise KeyError(f"Unknown page slug(s): {sorted(missing)}")
    for idx, slug in enumerate(ordered_slugs):
        pages[slug].order = idx
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="content_page.reorder"))


# ── FAQ items ────────────────────────────────────────────────────────

def list_faq(db: Session, *, active_only: bool) -> list[FaqItem]:
    stmt = select(FaqItem).order_by(FaqItem.order)
    if active_only:
        stmt = stmt.where(FaqItem.is_active.is_(True))
    return list(db.scalars(stmt))


def create_faq(db: Session, *, translations: dict, order: int = 0, is_active: bool = True,
               actor_id: str | None, actor_username: str | None) -> FaqItem:
    validate_translations(FAQ_FIELDS, translations, supported_languages=_supported_languages(db))
    item = FaqItem(translations=translations, order=order, is_active=is_active, updated_by=actor_id)
    db.add(item)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="faq.create"))
    db.flush()  # populate item.id for the response
    return item


def update_faq(db: Session, item_id: str, *, translations: dict | None = None, order: int | None = None,
                is_active: bool | None = None, actor_id: str | None, actor_username: str | None) -> FaqItem:
    item = db.get(FaqItem, item_id)
    if item is None:
        raise KeyError(f"No FAQ item {item_id!r}")
    if translations is not None:
        validate_translations(FAQ_FIELDS, translations, supported_languages=_supported_languages(db))
        item.translations = translations
    if order is not None:
        item.order = order
    if is_active is not None:
        item.is_active = is_active
    item.updated_by = actor_id
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="faq.update", target=item_id))
    return item


def delete_faq(db: Session, item_id: str, *, actor_id: str | None, actor_username: str | None) -> bool:
    item = db.get(FaqItem, item_id)
    if item is None:
        return False
    db.delete(item)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="faq.delete", target=item_id))
    return True


def reorder_faq(db: Session, ordered_ids: list[str], *, actor_id: str | None, actor_username: str | None) -> None:
    items = {i.id: i for i in db.scalars(select(FaqItem).where(FaqItem.id.in_(ordered_ids)))}
    missing = set(ordered_ids) - set(items)
    if missing:
        raise KeyError(f"Unknown FAQ id(s): {sorted(missing)}")
    for idx, item_id in enumerate(ordered_ids):
        items[item_id].order = idx
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="faq.reorder"))


# -- Chat integration ---------------------------------------------------
# Mirrors knowledge_service.build_prompt_block's shape: turn the
# admin-managed records into one block appended to the chat system
# prompt (see chat_service._build_system_prompt), so the assistant can
# actually draw on this content instead of it only existing for admins
# to browse. Empty/blank means "nothing to add", not an error.

def build_faq_prompt_block(db: Session, lang: str) -> str:
    items = list_faq(db, active_only=True)
    if not items:
        return ""

    lines = []
    for item in items:
        t = item.translations.get(lang) or item.translations.get("en") or next(iter(item.translations.values()), {})
        q, a = (t.get("q") or "").strip(), (t.get("a") or "").strip()
        if q and a:
            lines.append(f"Q: {q}\nA: {a}")
    if not lines:
        return ""

    faqs = "\n\n".join(lines)
    if lang == "ar":
        return (
            "\n\nالأسئلة الشائعة (أجب بهذه المعلومات بالضبط عندما يسأل الزائر شيئاً مطابقاً لأحد "
            "هذه الأسئلة — أعد صياغتها بأسلوبك المحادثي بدلاً من نسخها حرفياً):\n" + faqs
        )
    return (
        "\n\nFREQUENTLY ASKED QUESTIONS (answer with this exact information when a visitor asks "
        "something matching one of these questions — rephrase it conversationally rather than "
        "copying it verbatim):\n" + faqs
    )
