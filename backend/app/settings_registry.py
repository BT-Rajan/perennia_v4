"""
The settings registry: THE single source of truth for "everything
configurable" on the site.

Why a registry instead of a settings table with real columns, or a
hand-written admin endpoint per field (the reference app's approach)?
Because both of those force you to touch N places — a migration, a
Pydantic model, a route handler, an admin form — every single time you
add one configurable field. That's exactly the repetition this project
was asked to avoid, and it's how a 57KB main.py happens.

Here, adding a new configurable field is ONE line: a `SettingDef` entry
below. Everything downstream — DB storage, validation, the generic
admin CRUD API (routers/admin_settings.py), the public config API
(routers/public_config.py), and (Pass 8) the generic admin settings
form — reads this registry and needs no per-field code.

Categories map directly to admin panel sections. Each pass adds entries
to existing or new categories; no pass should need to add a new *code
path*, only new *entries*.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# Default on-screen text (copy.home/chat/booking/common), shared with the
# frontend's bundled fallback (src/data/content.js) so the two can't
# drift. Edit the JSON file, not a copy of it here.
SITE_COPY_PATH = Path(__file__).resolve().parents[2] / "src" / "content" / "site-copy.json"
_SITE_COPY: dict[str, Any] = json.loads(SITE_COPY_PATH.read_text(encoding="utf-8"))


class SettingType(str, Enum):
    STRING = "string"        # short single-line text
    TEXT = "text"             # multi-line text / markdown
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    COLOR = "color"           # hex color, admin renders a color picker
    URL = "url"
    EMAIL = "email"
    IMAGE = "image"           # URL to an uploaded image (Pass 3 adds upload)
    ENUM = "enum"              # one of `choices`
    LIST = "list"              # JSON list of strings
    JSON = "json"              # arbitrary JSON blob (structured content, Pass 2+)


@dataclass(frozen=True)
class SettingDef:
    key: str                      # dotted path, e.g. "branding.site_name"
    category: str                 # admin panel section, e.g. "branding"
    label: str                    # human label shown in admin UI
    type: SettingType
    default: Any
    help_text: str = ""
    secret: bool = False          # encrypted at rest, never in public config API
    choices: tuple[str, ...] | None = None   # required for ENUM
    i18n: bool = False            # if true, value is {lang_code: value} JSON
    validator: Callable[[Any], None] | None = field(default=None, repr=False)

    def validate(self, value: Any) -> None:
        if self.i18n:
            if not isinstance(value, dict):
                raise ValueError(f"{self.key}: expected an object keyed by language code")
            for lang, v in value.items():
                self._validate_single(v)
            return
        self._validate_single(value)

    def _validate_single(self, value: Any) -> None:
        t = self.type
        if t == SettingType.BOOL and not isinstance(value, bool):
            raise ValueError(f"{self.key}: expected bool")
        if t == SettingType.INT and not isinstance(value, int):
            raise ValueError(f"{self.key}: expected int")
        if t == SettingType.FLOAT and not isinstance(value, (int, float)):
            raise ValueError(f"{self.key}: expected number")
        if t == SettingType.COLOR:
            if not (isinstance(value, str) and _is_hex_color(value)):
                raise ValueError(f"{self.key}: expected hex color like #RRGGBB")
        if t == SettingType.ENUM:
            if value not in (self.choices or ()):
                raise ValueError(f"{self.key}: must be one of {self.choices}")
        if t == SettingType.LIST and not isinstance(value, list):
            raise ValueError(f"{self.key}: expected a list")
        if t == SettingType.JSON and not isinstance(value, (dict, list)):
            raise ValueError(f"{self.key}: expected an object or array")
        if t in (SettingType.STRING, SettingType.TEXT, SettingType.URL, SettingType.EMAIL, SettingType.IMAGE):
            if not isinstance(value, str):
                raise ValueError(f"{self.key}: expected string")
        if self.validator:
            self.validator(value)


def _is_hex_color(v: str) -> bool:
    import re
    return bool(re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", v))


def _url_or_empty(v: str) -> None:
    if v and not (v.startswith("http://") or v.startswith("https://") or v.startswith("/")):
        raise ValueError("must be an absolute URL or a root-relative path")


def _px_range(lo: int, hi: int):
    def _check(v: int) -> None:
        if not (lo <= v <= hi):
            raise ValueError(f"must be between {lo} and {hi}")
    return _check


def _int_range(lo: int, hi: int):
    def _check(v: int) -> None:
        if not (lo <= v <= hi):
            raise ValueError(f"must be between {lo} and {hi}")
    return _check


def _float_range(lo: float, hi: float):
    def _check(v: float) -> None:
        if not (lo <= v <= hi):
            raise ValueError(f"must be between {lo} and {hi}")
    return _check


def _valid_timezone(v: str) -> None:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        ZoneInfo(v)
    except ZoneInfoNotFoundError:
        raise ValueError(f"{v!r} is not a valid IANA timezone (e.g. 'Asia/Kuwait', 'America/New_York')")


def _hero_buttons(v: list) -> None:
    if not isinstance(v, list):
        raise ValueError("expected a list of {label, url} objects")
    if len(v) > 8:
        raise ValueError("at most 8 buttons")
    for i, btn in enumerate(v):
        if not isinstance(btn, dict):
            raise ValueError(f"button {i}: expected an object")
        label = btn.get("label")
        if not isinstance(label, dict) or not any(str(t).strip() for t in label.values()):
            raise ValueError(f"button {i}: label must be a non-empty {{lang: text}} object")
        url = btn.get("url", "")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"button {i}: url is required")
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("/")):
            raise ValueError(f"button {i}: url must be absolute http(s) or a root-relative path")


def _valid_workdays(v: list) -> None:
    if not all(isinstance(d, int) and 0 <= d <= 6 for d in v):
        raise ValueError("each workday must be an integer 0 (Monday) through 6 (Sunday)")
    if len(v) != len(set(v)):
        raise ValueError("workdays must not contain duplicates")


# Default search/share description — also the bundled fallback in
# src/data/siteContent.js and index.html; keep all three in sync.
META_EN = "Perennia — a technology partner for GCC businesses. Practical AI. Affordable Innovation."
META_AR = "بيرينيا — شريك تقني للشركات في دول الخليج. ذكاء اصطناعي عملي. ابتكار في المتناول."


# ── Registry ──────────────────────────────────────────────────────────
# Grouped by category purely for readability; the flat dict below is
# what code actually consumes.

_DEFS: list[SettingDef] = [
    # branding ------------------------------------------------------
    SettingDef("branding.site_name", "branding", "Site name", SettingType.STRING,
               {"en": "Perennia", "ar": "بيرينيا"}, i18n=True,
               help_text="Shown in the header, browser tab, and emails. Per-language, since a wordmark "
                          "often isn't a literal translation."),
    SettingDef("branding.tagline", "branding", "Tagline", SettingType.STRING, {"en": "", "ar": ""}, i18n=True),
    SettingDef("branding.logo_url", "branding", "Logo", SettingType.IMAGE, "/static/perennia-logo.png"),
    SettingDef("branding.logo_scale", "branding", "Logo zoom", SettingType.FLOAT, 1.0,
               help_text="Display size of the logo image relative to its default — logos with a lot "
                          "of built-in padding often look small next to the header text at 1.0x.",
               validator=_float_range(0.5, 3.0)),
    SettingDef("branding.favicon_url", "branding", "Favicon", SettingType.IMAGE, "/favicon.svg"),
    SettingDef("branding.meta_description", "branding", "Search/share description", SettingType.TEXT,
               {"en": META_EN, "ar": META_AR}, i18n=True,
               help_text="Shown in search results and link previews (og:description)."),

    # locale ----------------------------------------------------------
    SettingDef("locale.default_language", "locale", "Default language", SettingType.ENUM, "en",
               choices=("en", "ar")),
    SettingDef("locale.supported_languages", "locale", "Supported languages", SettingType.LIST, ["en", "ar"]),

    # contact -----------------------------------------------------------
    SettingDef("contact.email", "contact", "Contact email", SettingType.EMAIL, ""),
    SettingDef("contact.phone", "contact", "Contact phone", SettingType.STRING, "+965 9933 1344"),
    SettingDef("contact.whatsapp_number", "contact", "WhatsApp number", SettingType.STRING, "",
               help_text="Include country code, digits only, e.g. 96599999999."),
    SettingDef("contact.address", "contact", "Address", SettingType.TEXT, {"en": "", "ar": ""}, i18n=True),

    # theme — brand identity. Deliberately a SMALL set of base tokens
    # (colors, fonts, a few layout metrics) rather than every CSS custom
    # property in tokens.css: the frontend derives the full palette
    # (navy scale, glass surfaces, gold gradient shades, etc.) from
    # these few values using CSS color-mix(), so a full re-theme only
    # ever requires changing what's here — see src/styles/tokens.css
    # and PASS3_NOTES.md for the derivation.
    SettingDef("theme.primary_color", "theme", "Primary color", SettingType.COLOR, "#c9a84c",
               help_text="Main accent — buttons, links, highlights."),
    SettingDef("theme.accent_color", "theme", "Accent color", SettingType.COLOR, "#e8c96a",
               help_text="Secondary accent, used alongside the primary color in gradients."),
    SettingDef("theme.background_color", "theme", "Background color", SettingType.COLOR, "#07060a",
               help_text="Base dark surface color the whole app is built on."),
    SettingDef("theme.text_color", "theme", "Text color", SettingType.COLOR, "#f5f0e8",
               help_text="Primary light text color against the background."),
    SettingDef("theme.font_display", "theme", "Display font (headings)", SettingType.STRING,
               '"Cormorant Garamond", Georgia, serif'),
    SettingDef("theme.font_body", "theme", "Body font", SettingType.STRING,
               '"Syne", system-ui, -apple-system, sans-serif'),
    SettingDef("theme.font_ar", "theme", "Arabic font", SettingType.STRING,
               '"Noto Kufi Arabic", "Arial Unicode MS", sans-serif'),
    SettingDef("theme.google_fonts_url", "theme", "Google Fonts stylesheet URL", SettingType.URL,
               "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700"
               "&family=Syne:wght@500;600;700;800&family=Noto+Kufi+Arabic:wght@300;400;500;600;700"
               "&display=swap",
               help_text="Must include every font family referenced above, or those fonts won't load."),
    SettingDef("theme.header_height_px", "theme", "Header height (px)", SettingType.INT, 64,
               validator=_px_range(40, 160)),
    SettingDef("theme.content_max_width_px", "theme", "Content max width (px)", SettingType.INT, 1180,
               validator=_px_range(600, 2400)),
    SettingDef("theme.corner_radius_px", "theme", "Corner radius (px)", SettingType.INT, 10,
               help_text="Base radius — smaller and larger UI elements scale proportionally from this.",
               validator=_px_range(0, 48)),
    SettingDef("theme.hero_auto_advance_seconds", "theme", "Home auto-advance (seconds)", SettingType.INT, 7,
               help_text="How long the home screen waits before auto-continuing into chat.",
               validator=_int_range(2, 60)),
    # Which homepage layout arrangement to render — purely a client-side
    # choice of *structure* (how the same headline/tagline/CTA/nav
    # pieces are composed on the page), never colors/fonts (those stay
    # theme.primary_color etc. above) and never which features exist.
    # "classic" is both the default and the site's original/only layout
    # before this setting existed, so an unset or unrecognized value here
    # can never regress an existing deployment — the frontend falls back
    # to it (see src/components/hero/Hero.jsx).
    SettingDef("theme.layout_template", "theme", "Homepage layout", SettingType.ENUM, "classic",
               choices=("classic", "split", "centered-card", "editorial"),
               help_text="How the homepage headline, CTAs, and page-navigation cards are arranged. "
                          "Colors and fonts are unaffected — set those above."),
    # Purely the headline's text *treatment* (fill/animation) — never
    # its content (that's copy.home.welcome) and never layout (that's
    # theme.layout_template above). "ripple-gradient" is both the
    # default and the site's original/only headline style before this
    # setting existed, so it's the safe fallback for any unset or
    # unrecognized value (see src/components/hero/HeroShared.jsx).
    SettingDef("theme.headline_style", "theme", "Headline style", SettingType.ENUM, "ripple-gradient",
               choices=("ripple-gradient", "solid-gold", "solid-white", "two-tone", "outline"),
               help_text="Visual treatment of the homepage headline text. Uses the theme colors above — "
                          "changing the theme preset changes how each of these looks too."),
    # Homepage headline pacing — how fast copy.home.hero_statement types
    # out, and how slowly it dissolves into the permanent tagline once
    # done. Split into two settings (rather than one "speed" enum)
    # because they're genuinely independent: an admin might want a slow,
    # dramatic type-out with a snappy handoff, or vice versa. 5 cps is a
    # deliberately unhurried default (the site's original hardcoded rate
    # was ~45 cps); admins with a short statement may want it faster.
    SettingDef("theme.headline_typing_speed_cps", "theme", "Headline typing speed (characters/second)",
               SettingType.INT, 5,
               help_text="How fast the homepage headline types itself out. Lower = slower, more dramatic. "
                          "Only affects copy.home.hero_statement — the permanent tagline beneath it is never "
                          "animated.",
               validator=_int_range(1, 40)),
    SettingDef("theme.headline_dissolve_ms", "theme", "Headline dissolve transition (ms)",
               SettingType.INT, 2500,
               help_text="How long the crossfade from the typed statement to the permanent tagline "
                          "(taglineLine1/taglineLine2) takes, in milliseconds.",
               validator=_int_range(200, 8000)),
    # ── Pass 1 of the whole-page style system (surfaces + buttons).
    # Both are unified, cross-component toggles — one setting changes
    # every covered element at once, not per-component overrides. See
    # src/styles/themeVariants.css for exactly what each value does.
    #
    # "glass" / "default" reproduce today's actual appearance byte-for-
    # byte (glass is a real style choice that happens to already be
    # what's live; "default" for buttons means "each button keeps its
    # own current look" since today's buttons are NOT visually
    # uniform — the CTA pills are outlined/glass, the sticky buttons
    # are solid-filled). Either is always the safe fallback for an
    # unset or unrecognized value, so no existing deployment regresses.
    SettingDef("theme.surface_style", "theme", "Card & panel surface", SettingType.ENUM, "glass",
               choices=("glass", "solid", "outline", "elevated"),
               help_text="Fill treatment for cards and panels site-wide: the chat widget, booking panel, "
                          "and homepage nav/content cards. 'glass' is today's blurred, translucent look."),
    SettingDef("theme.button_style", "theme", "Buttons & pills", SettingType.ENUM, "default",
               choices=("default", "solid", "outline", "ghost", "gradient"),
               help_text="Fill treatment for call-to-action buttons and pills site-wide: homepage quick-"
                          "link buttons, the centered-card pills, and the sticky Appointments/AI Assistant "
                          "buttons. 'default' keeps each button's current individual look; every other "
                          "choice makes them all match one unified style."),
    # ── Pass 2 of the whole-page style system (typography). "standard"
    # / "as-is" reproduce today's actual font sizes and heading
    # casing exactly, so they're the safe fallback for any unset or
    # unrecognized value. See src/styles/themeVariants.css.
    SettingDef("theme.type_scale", "theme", "Text size scale", SettingType.ENUM, "standard",
               choices=("standard", "compact", "comfortable", "large"),
               help_text="Global size for body text, small text, and section-card headings site-wide. "
                          "Doesn't affect the homepage headline, which sizes itself to fit the page."),
    SettingDef("theme.heading_case", "theme", "Section heading style", SettingType.ENUM, "as-is",
               choices=("as-is", "uppercase-tracked", "sentence-case"),
               help_text="Casing and letter-spacing for section/card titles (e.g. the homepage nav "
                          "cards). 'as-is' keeps today's normal-case headings."),
    # ── Pass 3 of the whole-page style system (background & texture).
    # "grid" / "subtle" reproduce today's actual background exactly —
    # a solid fill plus a faint grid-mesh overlay — so they're the
    # safe fallback for any unset or unrecognized value.
    SettingDef("theme.background_style", "theme", "Background pattern", SettingType.ENUM, "grid",
               choices=("grid", "dot-grid", "radial-glow", "solid"),
               help_text="Texture behind all page content. 'grid' is today's faint line-mesh overlay; "
                          "'solid' removes the overlay entirely."),
    SettingDef("theme.background_intensity", "theme", "Background intensity", SettingType.ENUM, "subtle",
               choices=("subtle", "soft", "bold", "off"),
               help_text="How strong the background pattern above is. 'off' hides it regardless of "
                          "which pattern is selected."),
    # ── Pass 4 of the whole-page style system (spacing & density).
    # "comfortable" / "standard" reproduce today's actual spacing and
    # section rhythm exactly, so they're the safe fallback for any
    # unset or unrecognized value.
    SettingDef("theme.density", "theme", "Spacing density", SettingType.ENUM, "comfortable",
               choices=("compact", "comfortable", "spacious"),
               help_text="Padding, gaps, and prose line-height site-wide — every card, button, and "
                          "text block scales together. 'comfortable' is today's spacing."),
    SettingDef("theme.section_rhythm", "theme", "Section rhythm", SettingType.ENUM, "standard",
               choices=("tight", "standard", "loose"),
               help_text="Breathing room specifically between major page sections (e.g. the gap before "
                          "the homepage's nav-card grid) — independent of the density setting above, "
                          "so you can pair tight card spacing with generous section gaps, or vice versa."),

    # features (toggles for capabilities landing in later passes,
    # declared now so the admin can already see what's coming and
    # nothing needs a hardcoded `if` for "is this feature on") --------
    SettingDef("features.booking_enabled", "features", "Enable appointment booking", SettingType.BOOL, True),
    SettingDef("features.chat_enabled", "features", "Enable AI chat widget", SettingType.BOOL, True),
    SettingDef("features.whatsapp_widget_enabled", "features", "Enable WhatsApp widget", SettingType.BOOL, False),
    SettingDef("features.calendar_sync_enabled", "features", "Enable Google Calendar sync", SettingType.BOOL, False,
               help_text="Pass 12: once connected (see Calendar Sync), busy time on the linked Google "
                         "Calendar blocks booking slots. Off by default even after connecting — a "
                         "deliberate two-step opt-in."),

    # booking — business rules for the appointment scheduler. Slot
    # generation, availability, and notice-window enforcement all read
    # these at request time (app/booking_service.py) rather than having
    # any of it hardcoded, so an admin can retune the whole booking
    # flow (different hours, days, timezone, lead time) without a
    # deploy. day_start_hour/day_end_hour aren't cross-validated against
    # each other here (registry validation is per-key); if end <= start,
    # booking_service treats that day as having zero slots rather than
    # erroring, so a temporarily-inconsistent pair never 500s a request.
    SettingDef("booking.timezone", "booking", "Timezone", SettingType.STRING, "Asia/Kuwait",
               help_text="IANA timezone name — determines what 'today' and business hours mean.",
               validator=_valid_timezone),
    SettingDef("booking.slot_minutes", "booking", "Slot length (minutes)", SettingType.INT, 30,
               validator=_int_range(5, 240)),
    SettingDef("booking.day_start_hour", "booking", "Day starts at (hour, 24h)", SettingType.INT, 9,
               validator=_int_range(0, 23)),
    SettingDef("booking.day_end_hour", "booking", "Day ends at (hour, 24h)", SettingType.INT, 17,
               validator=_int_range(0, 23)),
    SettingDef("booking.workdays", "booking", "Working days", SettingType.LIST, [0, 1, 2, 3, 4],
               help_text="0=Monday .. 6=Sunday.", validator=_valid_workdays),
    SettingDef("booking.max_days_ahead", "booking", "Max days ahead (appointments)", SettingType.INT, 30,
               validator=_int_range(1, 365)),
    SettingDef("booking.min_notice_hours", "booking", "Minimum notice (hours)", SettingType.INT, 6,
               help_text="Required lead time to book, cancel, or reschedule.", validator=_int_range(0, 168)),
    # A pending appointment holds its slot exactly like a confirmed one
    # (booking_service.py::_booked_intervals) - deliberately, per
    # PASS10_NOTES.md - but that was previously unbounded: an admin who
    # never accepts/declines a request leaves it blocking that slot
    # forever. These two settings bound that: past
    # pending_expiry_hours old, a pending appointment stops counting as
    # blocking (checked live in _booked_intervals) and is auto-declined
    # by a background sweep (booking_service.expire_stale_pending_appointments,
    # run every pending_expiry_poll_minutes by app/scheduler.py) so it
    # doesn't just quietly stop blocking while still sitting there
    # showing "pending" forever.
    SettingDef("booking.pending_expiry_hours", "booking", "Auto-decline pending requests after (hours)",
               SettingType.INT, 48, validator=_int_range(0, 720),
               help_text="A pending appointment awaiting approval stops holding its slot, and is "
                         "auto-declined, after this many hours with no admin action. 0 disables this — "
                         "a pending appointment then holds its slot indefinitely, as it always did before "
                         "this setting existed."),
    SettingDef("booking.pending_expiry_poll_minutes", "booking", "Check for expired pending requests every (minutes)",
               SettingType.INT, 30, validator=_int_range(5, 1440),
               help_text="How often the background sweep runs. Irrelevant if pending_expiry_hours is 0."),
    SettingDef("booking.calendar_sync_fail_open", "booking", "If Google Calendar is unreachable, show slots anyway",
               SettingType.BOOL, False,
               help_text="Pass 12: when the connected Google Calendar can't be reached (timeout, revoked "
                         "access, quota), the safe default is to show NO slots rather than risk double-"
                         "booking against busy time we can't currently see. Turn this on only if you'd "
                         "rather keep taking bookings — ignoring the external calendar — when it's down."),

    # chat — LLM-powered assistant configuration. The API key is the
    # only secret setting in the app so far (Fernet-encrypted at rest
    # by settings_service.py, never returned by any read endpoint).
    # Everything else here — provider, model, prompt, sampling
    # parameters, and the fallback message shown when no key is
    # configured — is ordinary admin-editable config, so the whole
    # assistant's behavior and persona can be retuned without a deploy.
    SettingDef("chat.llm_provider", "chat", "LLM provider", SettingType.ENUM, "none",
               choices=("none", "anthropic", "openai", "deepseek"),
               help_text="'none' disables real LLM calls; the assistant uses the fallback message below."),
    SettingDef("chat.llm_model", "chat", "Model", SettingType.STRING, "claude-sonnet-4-6"),
    SettingDef("chat.llm_api_key", "chat", "API key", SettingType.STRING, "", secret=True),
    SettingDef("chat.max_tokens", "chat", "Max response tokens", SettingType.INT, 512,
               validator=_int_range(16, 4096)),
    SettingDef("chat.temperature", "chat", "Temperature", SettingType.FLOAT, 0.7,
               validator=_float_range(0.0, 1.0)),
    # Shown next to the assistant in the sticky widget (ChatWidget).
    # Blank falls back to a plain initial-letter
    # avatar (see src/components/chat/ChatWidget.jsx).
    SettingDef("chat.avatar_url", "chat", "Assistant avatar", SettingType.IMAGE, "",
               help_text="Shown next to the assistant in the AI Assistant widget. "
                          "Leave blank to use a plain initial-letter avatar instead."),
    SettingDef("chat.system_prompt", "chat", "System prompt", SettingType.TEXT, {
        "en": "You are Perennia's AI assistant. Be warm, concise, and professional. Early in the "
              "conversation, ask the visitor's name so you can personalize the chat and so the team can "
              "follow up. Help visitors understand how Perennia helps businesses with technology, AI and advisory, and encourage "
              "booking a 30-minute discovery meeting (\"Book a 30-Minute Discovery Meeting\") when they show "
              "real interest.",
        "ar": "أنت المساعد الذكي لشركة بيرينيا. كن ودودًا ومختصرًا ومحترفًا. في وقت مبكر من المحادثة، اسأل "
              "الزائر عن اسمه حتى تتمكن من تخصيص المحادثة ومتابعة الطلب. ساعد الزوار على فهم كيف تساعد بيرينيا الشركات في التقنية والذكاء الاصطناعي "
              "والاستشارات، وشجعهم على حجز اجتماع استكشافي مدته 30 دقيقة عبر \"احجز اجتماعًا استكشافيًا لمدة 30 دقيقة\" عند "
              "إبداء اهتمام حقيقي.",
    }, i18n=True),
    SettingDef("chat.unavailable_message", "chat", "Fallback message (LLM unavailable)", SettingType.TEXT, {
        "en": "Thanks for sharing that! Someone from our team will follow up shortly. "
              "Would you like to book a time to talk?",
        "ar": "شكرًا لك! سيقوم أحد أعضاء فريقنا بمتابعة رسالتك قريبًا. هل ترغب في حجز موعد؟",
    }, i18n=True, help_text="Shown when no LLM provider is configured, or if a request to it fails."),
    SettingDef("chat.max_turns", "chat", "Max exchanges per session", SettingType.INT, 15,
               help_text="Once a visitor's user-turn count in one session passes this, the turn-limit "
                          "message below is shown instead of calling the LLM again.",
               validator=_int_range(3, 100)),
    SettingDef("chat.turn_limit_message", "chat", "Turn-limit message", SettingType.TEXT, {
        "en": "You've reached the message limit for this session. We'd love to keep the conversation "
              "going directly — please book a 30-minute discovery meeting with our team.",
        "ar": "لقد وصلت إلى الحد الأقصى لعدد الرسائل في هذه الجلسة. يسعدنا مواصلة الحديث مباشرة — "
              "احجز اجتماعًا استكشافيًا لمدة 30 دقيقة مع فريقنا.",
    }, i18n=True, help_text="Shown once a visitor exceeds the max exchanges above, in place of a real reply."),

    # calendar_sync — Pass 12 (docs/CALENDAR_MODULE_PLAN.md): Google
    # OAuth app credentials for the Calendar Sync connect flow. These
    # identify *this deployment* to Google (same client id/secret for
    # every admin who ever connects, since there's one business
    # per install) — separate from the per-connection tokens stored in
    # CalendarCredential (app/models.py), which identify *which Google
    # account* got connected and are Fernet-encrypted the same way
    # google_client_secret is.
    SettingDef("calendar_sync.google_client_id", "calendar_sync", "Google OAuth client ID", SettingType.STRING, "",
               help_text="From Google Cloud Console — an OAuth 2.0 Client ID for a 'Web application'."),
    SettingDef("calendar_sync.google_client_secret", "calendar_sync", "Google OAuth client secret",
               SettingType.STRING, "", secret=True),
    SettingDef("calendar_sync.google_redirect_uri", "calendar_sync", "OAuth redirect URI", SettingType.URL, "",
               help_text="Must exactly match an 'Authorized redirect URI' configured on the Google OAuth "
                         "client. Point this at the admin Settings page itself — "
                         "https://yourdomain.com/admin/settings/calendar_sync — the page picks up "
                         "Google's ?code=&state= and completes the connection without a full page reload.",
               validator=_url_or_empty),
    SettingDef("calendar_sync.drift_poll_minutes", "calendar_sync", "Auto-check for external changes every (minutes)",
               SettingType.INT, 15, validator=_int_range(0, 1440),
               help_text="How often to check the connected Google Calendar for events that were edited or "
                         "deleted directly in Google (not through this app) and flag the mismatched "
                         "appointment for review. 0 disables the automatic check — use 'Sync now' in the "
                         "Calendar settings instead."),

    # notifications — outbound email/WhatsApp for booking confirmations
    # and internal staff alerts. Every send is best-effort: a
    # notification failure (bad SMTP creds, provider down) never fails
    # the booking/chat request that triggered it — see
    # notification_service.py. Both channels default fully OFF so an
    # admin opts in deliberately rather than the app silently trying
    # (and failing) to send mail with no configuration.
    SettingDef("notifications.email_enabled", "notifications", "Enable email notifications", SettingType.BOOL, False),
    SettingDef("notifications.smtp_host", "notifications", "SMTP host", SettingType.STRING, ""),
    SettingDef("notifications.smtp_port", "notifications", "SMTP port", SettingType.INT, 587,
               validator=_int_range(1, 65535),
               help_text="587 = STARTTLS (Gmail, Office 365, most providers). 465 = SSL/TLS from the "
                         "start (the STARTTLS switch is ignored). Use 'Send test email' below after saving."),
    SettingDef("notifications.smtp_username", "notifications", "SMTP username", SettingType.STRING, ""),
    SettingDef("notifications.smtp_password", "notifications", "SMTP password", SettingType.STRING, "", secret=True,
               help_text="For Gmail / Google Workspace use an App Password, not the account password."),
    SettingDef("notifications.smtp_use_tls", "notifications", "Use STARTTLS", SettingType.BOOL, True),
    SettingDef("notifications.from_email", "notifications", "From address", SettingType.EMAIL, ""),
    SettingDef("notifications.from_name", "notifications", "From name", SettingType.STRING, "",
               help_text="Falls back to the site name if left blank."),
    SettingDef("notifications.attach_calendar_invite", "notifications", "Attach calendar invite (.ics)",
               SettingType.BOOL, True,
               help_text="Booking confirmation, reschedule and cancellation emails carry a calendar invite, "
                         "so the visitor and the internal alert email get the meeting added, moved or removed "
                         "in their own calendar (Gmail, Outlook, Apple)."),
    SettingDef("notifications.admin_alert_email", "notifications", "Internal alert email", SettingType.EMAIL, "",
               help_text="Where new-booking and new-lead alerts are sent. Leave blank to disable."),
    SettingDef("notifications.admin_alert_whatsapp_number", "notifications", "Internal alert WhatsApp number",
               SettingType.STRING, "",
               help_text="Pass 13: where the 'a booking needs your confirmation' alert is sent by "
                         "WhatsApp (in addition to, or instead of, the email above — whichever of "
                         "the two is configured is used). Requires WhatsApp notifications enabled "
                         "below. Leave blank to skip WhatsApp for this alert."),
    SettingDef("notifications.whatsapp_enabled", "notifications", "Enable WhatsApp notifications", SettingType.BOOL, False),
    SettingDef("notifications.whatsapp_provider", "notifications", "WhatsApp provider", SettingType.ENUM, "none",
               choices=("none", "twilio", "meta_cloud")),
    SettingDef("notifications.whatsapp_account_id", "notifications", "Account ID", SettingType.STRING, "",
               help_text="Twilio Account SID, or Meta phone number ID."),
    SettingDef("notifications.whatsapp_api_key", "notifications", "API key / auth token", SettingType.STRING, "",
               secret=True),
    SettingDef("notifications.whatsapp_from_number", "notifications", "Sender number", SettingType.STRING, "",
               help_text="Required for Twilio; unused for Meta Cloud API (the account ID identifies the sender)."),

    # templates — editable, bilingual notification content. Every
    # send in notification_service.py renders one of these rather than
    # having any wording hardcoded in Python, so the exact phrasing of
    # a confirmation email or WhatsApp message is an admin edit like
    # everything else. {name}/{date}/{time}/{id}/{service} placeholders
    # are filled in at send time — see notification_service.render().
    SettingDef("templates.booking_confirmed_email", "templates", "Appointment confirmed — email", SettingType.JSON, {
        "en": {"subject": "Your appointment is confirmed — {id}",
               "body": "Hi {name},\n\nYour appointment is confirmed for {date} at {time}.\n"
                       "Confirmation code: {id}\n\nWe look forward to speaking with you."},
        "ar": {"subject": "تم تأكيد موعدك — {id}",
               "body": "مرحباً {name}،\n\nتم تأكيد موعدك في {date} الساعة {time}.\nرمز التأكيد: {id}\n\nنتطلع للحديث معك."},
    }, i18n=True),
    SettingDef("templates.booking_cancelled_email", "templates", "Appointment cancelled — email", SettingType.JSON, {
        "en": {"subject": "Your appointment has been cancelled — {id}",
               "body": "Hi {name},\n\nYour appointment on {date} at {time} (code {id}) has been cancelled.\n"
                       "Feel free to book a new time whenever suits you."},
        "ar": {"subject": "تم إلغاء موعدك — {id}",
               "body": "مرحباً {name}،\n\nتم إلغاء موعدك في {date} الساعة {time} (الرمز {id}).\n"
                       "يمكنك حجز موعد جديد في أي وقت يناسبك."},
    }, i18n=True),
    SettingDef("templates.booking_rescheduled_email", "templates", "Appointment rescheduled — email", SettingType.JSON, {
        "en": {"subject": "Your appointment was rescheduled — {id}",
               "body": "Hi {name},\n\nYour appointment (code {id}) is now confirmed for {date} at {time}."},
        "ar": {"subject": "تم تغيير موعد الحجز — {id}",
               "body": "مرحباً {name}،\n\nموعدك (الرمز {id}) أصبح الآن في {date} الساعة {time}."},
    }, i18n=True),
    SettingDef("templates.booking_confirmed_whatsapp", "templates", "Appointment confirmed — WhatsApp", SettingType.TEXT, {
        "en": "Hi {name}! Your appointment is confirmed for {date} at {time}. Code: {id}",
        "ar": "مرحباً {name}! تم تأكيد موعدك في {date} الساعة {time}. الرمز: {id}",
    }, i18n=True),
    SettingDef("templates.booking_cancelled_whatsapp", "templates", "Appointment cancelled — WhatsApp", SettingType.TEXT, {
        "en": "Hi {name}, your appointment on {date} at {time} (code {id}) has been cancelled.",
        "ar": "مرحباً {name}، تم إلغاء موعدك في {date} الساعة {time} (الرمز {id}).",
    }, i18n=True),
    SettingDef("templates.booking_rescheduled_whatsapp", "templates", "Appointment rescheduled — WhatsApp", SettingType.TEXT, {
        "en": "Hi {name}, your appointment (code {id}) is now confirmed for {date} at {time}.",
        "ar": "مرحباً {name}، موعدك (الرمز {id}) أصبح الآن في {date} الساعة {time}.",
    }, i18n=True),
    SettingDef("templates.new_booking_admin_alert", "templates", "New appointment — internal alert", SettingType.JSON, {
        "en": {"subject": "New booking: {name} — {date} {time}",
               "body": "{name} ({email}) booked {date} at {time}.\nService: {service}\nCode: {id}"},
    }, help_text="Internal alert, English only by default — this is for staff, not visitors."),
    SettingDef("templates.booking_cancelled_admin_alert", "templates", "Appointment cancelled — internal alert",
               SettingType.JSON, {
        "en": {"subject": "Cancelled: {name} — {date} {time}",
               "body": "{name} ({email}) — appointment on {date} at {time} was cancelled.\nService: {service}\nCode: {id}"},
    }, help_text="Internal alert, English only by default — this is for staff, not visitors."),
    SettingDef("templates.booking_rescheduled_admin_alert", "templates", "Appointment rescheduled — internal alert",
               SettingType.JSON, {
        "en": {"subject": "Rescheduled: {name} — now {date} {time}",
               "body": "{name} ({email}) — appointment moved to {date} at {time}.\nService: {service}\nCode: {id}"},
    }, help_text="Internal alert, English only by default — this is for staff, not visitors."),
    SettingDef("templates.new_lead_admin_alert", "templates", "New lead — internal alert", SettingType.JSON, {
        "en": {"subject": "New lead from chat: {email}",
               "body": "A new lead came in via chat.\nEmail: {email}\nMessage: {message}"},
    }, help_text="Internal alert, English only by default — this is for staff, not visitors."),

    # Pass 10 (docs/CALENDAR_MODULE_PLAN.md): confirmation workflow for
    # services with requires_confirmation=True. A new booking against
    # one of those lands as "pending" — the organizer gets an internal
    # alert (booking_requested_admin_alert, staff-facing like
    # new_booking_admin_alert) instead of the attendee getting an
    # immediate confirmation; the attendee only hears back once an
    # admin accepts or declines the request.
    SettingDef("templates.booking_requested_admin_alert", "templates", "Appointment requested — internal alert",
               SettingType.JSON, {
        "en": {"subject": "Booking request: {name} — {date} {time}",
               "body": "{name} ({email}) requested {date} at {time}.\nService: {service}\nCode: {id}\n\n"
                       "This service requires confirmation — accept or decline it from the admin dashboard."},
    }, help_text="Internal alert, English only by default — this is for staff, not visitors."),
    SettingDef("templates.booking_requested_admin_whatsapp", "templates", "Appointment requested — internal WhatsApp",
               SettingType.TEXT, "New booking request from {name} for {date} at {time} ({service}, code {id}) "
                                  "needs your confirmation — check the admin dashboard.",
               help_text="Pass 13: sent to notifications.admin_alert_whatsapp_number when set, alongside "
                         "(or instead of) the email alert above."),
    SettingDef("templates.booking_accepted_email", "templates", "Appointment request accepted — email", SettingType.JSON, {
        "en": {"subject": "Your appointment is confirmed — {id}",
               "body": "Hi {name},\n\nGood news — your request for {date} at {time} has been accepted "
                       "and is now confirmed.\nConfirmation code: {id}\n\nWe look forward to speaking with you."},
        "ar": {"subject": "تم تأكيد موعدك — {id}",
               "body": "مرحباً {name}،\n\nخبر سار — تم قبول طلبك في {date} الساعة {time} وأصبح مؤكداً الآن.\n"
                       "رمز التأكيد: {id}\n\nنتطلع للحديث معك."},
    }, i18n=True),
    SettingDef("templates.booking_declined_email", "templates", "Appointment request declined — email", SettingType.JSON, {
        "en": {"subject": "About your appointment request — {id}",
               "body": "Hi {name},\n\nWe're sorry, but we're unable to confirm your request for {date} "
                       "at {time}.{reason}\n\nPlease feel free to reach out or book another time.\n\nCode: {id}"},
        "ar": {"subject": "بخصوص طلب موعدك — {id}",
               "body": "مرحباً {name}،\n\nنأسف، لا يمكننا تأكيد طلبك في {date} الساعة {time}.{reason}\n\n"
                       "لا تتردد في التواصل معنا أو حجز موعد آخر.\n\nالرمز: {id}"},
    }, i18n=True, help_text="{reason} is filled with the admin's decline note when one is given, "
                              "or left blank otherwise — leave it in the template even if you rarely use it."),
    SettingDef("templates.booking_accepted_whatsapp", "templates", "Appointment request accepted — WhatsApp",
               SettingType.TEXT, {
        "en": "Hi {name}! Your request for {date} at {time} has been accepted and is now confirmed. Code: {id}",
        "ar": "مرحباً {name}! تم قبول طلبك في {date} الساعة {time} وأصبح مؤكداً. الرمز: {id}",
    }, i18n=True),
    SettingDef("templates.booking_declined_whatsapp", "templates", "Appointment request declined — WhatsApp",
               SettingType.TEXT, {
        "en": "Hi {name}, we're unable to confirm your request for {date} at {time}.{reason} "
              "Feel free to reach out or book another time.",
        "ar": "مرحباً {name}، لا يمكننا تأكيد طلبك في {date} الساعة {time}.{reason} "
              "لا تتردد في التواصل معنا أو حجز موعد آخر.",
    }, i18n=True, help_text="{reason} is filled with the admin's decline note when one is given, "
                              "or left blank otherwise."),

    # copy — free-form UI microcopy blobs, grouped by the screen that
    # uses them (home / chat / booking). Kept as JSON blobs rather than
    # exploded into one registry entry per string: these ~10-15 strings
    # per screen are always edited together, so one admin form per
    # screen (Pass 8) makes more sense than fifteen tiny form fields.
    # Structured content that's genuinely record-shaped (pages, FAQ)
    # lives in content_schema.py / content_service.py instead — see
    # PASS2_NOTES.md for why the split.
    SettingDef("copy.home", "copy", "Home screen text", SettingType.JSON, _SITE_COPY["home"], i18n=True,
               help_text="welcome, tagline, hint, lang_switch, hero_statement, tagline_line1, tagline_line2, "
                          "eyebrow, supporting_text, cta_primary, cta_secondary, "
                          "situations_kicker, situations_heading, situations_intro, sectors_heading, sectors_note "
                          "(the who-we-work-with section under the hero), "
                          "capabilities_heading, capabilities_intro, capabilities_roles, "
                          "capabilities_scope_note (the Technology/AI/Advisory section), "
                          "local_kicker, local_heading, local_intro (the Kuwait/GCC panel), "
                          "process_heading, process_intro (the how-we-work section), work_kicker, work_heading, work_intro, "
                          "work_other_label, work_need_label, work_built_label, work_all_label and work_all_url (the Our work section; the last two are its \"View all case studies\" link — leave either empty to hide it), case_kicker, case_heading, case_body, "
                          "case_link, case_image_alt, case_page_slug, case_image_url (the featured case-study teaser), "
                          "trust_kicker, trust_heading, trust_intro, "
                          "trust_contrast_label_a/_a/_label_b/_b (the reliable-induction section), discovery_heading, "
                          "discovery_body, discovery_note (the discovery-meeting panel after it). "
                          "Homepage lists (edit or reorder the items in place; each is a list of objects): "
                          "situations, sectors, capabilities, local_points, process_steps, case_stages, "
                          "other_work, trust_points. case_page_slug picks which content page is the featured "
                          "case study (the teaser hides if that page doesn't exist). "
                          "eyebrow is the static line above the headline. cta_primary opens "
                          "the booking panel (or the Contact page if booking is off); cta_secondary opens the "
                          "products page. hero_statement (empty by default) types itself out on the homepage "
                          "before handing off to tagline_line1/2 (see theme.headline_typing_speed_cps and "
                          "theme.headline_dissolve_ms above) — include a literal newline in the string to "
                          "have it type across two lines instead of one."),
    SettingDef("copy.chat", "copy", "Chat screen text", SettingType.JSON, _SITE_COPY["chat"], i18n=True,
               help_text="Chat widget labels and messages: header, online_status, welcome_msg, input_placeholder, "
                          "faq_title, book_btn, the mic_* and *_tts voice controls, and powered_by. Any key left "
                          "out falls back to the bundled default text."),
    SettingDef("copy.booking", "copy", "Appointment flow text", SettingType.JSON, _SITE_COPY["booking"], i18n=True,
               help_text="Field labels and status messages for the booking panel, including validation and "
                          "error messages so a visitor never sees a raw error code. Status messages support "
                          "{id}/{date}/{time} placeholders."),
    SettingDef("copy.common", "copy", "Shared accessibility labels", SettingType.JSON, _SITE_COPY["common"], i18n=True,
               help_text="Screen-reader labels used across multiple screens (close/back/send buttons, nav "
                          "landmarks) — not visible text, but still shown to assistive-technology users in "
                          "whichever language they're browsing in."),
    SettingDef("copy.home_hero_buttons", "copy", "Home hero buttons", SettingType.JSON, [],
               help_text="Slim buttons shown on the home screen in place of the tagline. List of "
                          "objects: {\"label\": {\"en\": \"...\", \"ar\": \"...\"}, \"url\": \"...\"}. "
                          "Empty list falls back to the tagline text. URL must be absolute http(s) "
                          "or a root-relative path.",
               validator=_hero_buttons),

    # knowledge — the chat assistant's grounding documents (uploaded
    # files and fetched web pages). No embeddings/vector search: every
    # active source's (capped) text is concatenated straight into the
    # system prompt on each reply — see chat_service.py and
    # knowledge_service.py. These settings bound how much that can
    # grow, since prompt size directly affects LLM cost and latency.
    SettingDef("knowledge.enabled", "knowledge", "Use knowledge base in chat replies", SettingType.BOOL, True),
    SettingDef("knowledge.max_total_sources", "knowledge", "Max sources", SettingType.INT, 20,
               help_text="Uploads/URLs beyond this must be removed before adding another.",
               validator=_int_range(1, 200)),
    SettingDef("knowledge.max_chars_per_source", "knowledge", "Max characters per source", SettingType.INT, 8000,
               help_text="Longer documents are truncated at upload/fetch time.",
               validator=_int_range(500, 50000)),
    SettingDef("knowledge.max_lines_in_prompt", "knowledge", "Max lines per source sent to the LLM",
               SettingType.INT, 50,
               help_text="Defense-in-depth against prompt injection via an uploaded document: caps how much "
                          "of any one source can reach the model, so a huge or adversarial upload can't crowd "
                          "out the assistant's actual instructions.",
               validator=_int_range(5, 500)),
]

for _d in _DEFS:
    if _d.type == SettingType.URL or _d.type == SettingType.IMAGE:
        object.__setattr__(_d, "validator", _url_or_empty)

REGISTRY: dict[str, SettingDef] = {d.key: d for d in _DEFS}

CATEGORIES: list[str] = sorted({d.category for d in _DEFS})


def defs_for_category(category: str) -> list[SettingDef]:
    return [d for d in _DEFS if d.category == category]


def get_def(key: str) -> SettingDef:
    d = REGISTRY.get(key)
    if d is None:
        raise KeyError(f"Unknown setting key: {key!r} (not in settings_registry.REGISTRY)")
    return d
