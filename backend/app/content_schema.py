"""
Schemas for *structured, repeatable* content — content pages and FAQ
items — as opposed to the scalar key/value settings in
settings_registry.py. Both still follow the same principle: declare the
shape once here, and storage/validation/admin API/public API all derive
from it instead of being hand-written per field.

Why not force pages and FAQ into the settings registry too? Because
they're *lists of records* (an admin adds/removes/reorders FAQ items;
pages have per-record versioning) rather than single named values —
different enough shape that forcing them through the scalar registry
would mean synthetic list-of-JSON settings with no real validation.
`content_service.py` reuses the same "translations dict validated
against a schema" pattern for both, so the two content tables share one
validation function despite having different field lists.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str
    required: bool
    multiline: bool = False  # hint for the (future) admin UI, markdown for body fields


# One row per content page. `nav_label` also feeds the header nav menu
# and the home page's quick-link cards — unifying what used to be three
# separate hardcoded structures (NAV, SECTIONS, PAGE_META in
# src/data/content.js and src/data/pages.js) into one per-page record.
PAGE_FIELDS: list[FieldDef] = [
    FieldDef("nav_label", "Nav menu label", required=True),
    FieldDef("section_title", "Home teaser title", required=True),
    FieldDef("section_body", "Home teaser text", required=True, multiline=True),
    FieldDef("tagline_line1", "Page header — line 1", required=False),
    FieldDef("tagline_line2", "Page header — line 2 (accent)", required=False),
    FieldDef("tagline_sub", "Page header — subtitle", required=False),
    FieldDef("body_markdown", "Full page body (Markdown)", required=True, multiline=True),
]

FAQ_FIELDS: list[FieldDef] = [
    FieldDef("q", "Question", required=True),
    FieldDef("a", "Answer", required=True, multiline=True),
]

PAGE_FIELD_KEYS = {f.key for f in PAGE_FIELDS}
FAQ_FIELD_KEYS = {f.key for f in FAQ_FIELDS}


def validate_translations(fields: list[FieldDef], translations: dict, *, supported_languages: list[str]) -> None:
    """`translations` must be {lang_code: {field_key: str, ...}}. At
    least one supported language must be present with every required
    field filled in (a record can be partially translated — the reader
    falls back — but it can't exist with zero real content)."""
    if not isinstance(translations, dict):
        raise ValueError("translations must be an object keyed by language code")

    unknown_langs = set(translations) - set(supported_languages)
    if unknown_langs:
        raise ValueError(f"Unsupported language code(s): {sorted(unknown_langs)}")

    field_keys = {f.key for f in fields}
    has_one_complete = False
    for lang, values in translations.items():
        if not isinstance(values, dict):
            raise ValueError(f"translations[{lang!r}] must be an object")
        unknown_fields = set(values) - field_keys
        if unknown_fields:
            raise ValueError(f"Unknown field(s) for {lang!r}: {sorted(unknown_fields)}")
        for v in values.values():
            if not isinstance(v, str):
                raise ValueError(f"translations[{lang!r}] values must be strings")
        if all((not f.required) or values.get(f.key, "").strip() for f in fields):
            has_one_complete = True

    if not has_one_complete:
        required = [f.key for f in fields if f.required]
        raise ValueError(f"At least one language must have all required fields filled in: {required}")
