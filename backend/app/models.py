"""
ORM models.

Deliberately few tables in Pass 1. The big one conceptually is
`SiteSetting`: rather than one DB column per configurable field (which is
how the reference app's sprawl happened — a new column and a new admin
API endpoint for every setting), every configurable value is a row here,
keyed by a dotted key that's validated against `settings_registry.py`.
Later passes (booking, leads, chat, notifications) add their own
domain tables, but *configuration* always flows through this one table.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # bcrypt hash only — a plaintext password is never stored or logged.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Role scaffolding for Pass 9 (RBAC). "owner" can manage other admins;
    # "editor" can change content/settings but not users/security.
    role: Mapped[str] = mapped_column(String(16), default="owner", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["AdminSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AdminSession(Base):
    """Server-side session record. The cookie only carries the opaque
    session id (signed); nothing about the user is trusted from the
    client without a DB lookup, and a session can be revoked instantly
    by deleting this row (unlike a stateless JWT)."""

    __tablename__ = "admin_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex + uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(64), default=_uuid)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["AdminUser"] = relationship(back_populates="sessions")

    __table_args__ = (Index("ix_admin_session_expires", "expires_at"),)


class SiteSetting(Base):
    """One row per configurable value. `key` is a dotted path (e.g.
    'branding.site_name', 'hours.workdays') that must exist in the
    settings registry — the registry is the schema; this table is just
    storage. `value` is always stored as text (JSON-encoded for
    non-string types); `is_secret` rows are Fernet-encrypted before
    being written here and never returned by the public config API."""

    __tablename__ = "site_setting"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("admin_user.id"), nullable=True)


class AuditLog(Base):
    """Append-only trail of admin actions. Full RBAC/audit UI lands in
    Pass 9, but every write path from Pass 1 onward logs through this so
    there's no gap to backfill later."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ContentPage(Base):
    """One row per standalone content page (about/products/services/
    contact/...). `translations` is {lang_code: {field_key: str}},
    validated against content_schema.PAGE_FIELDS — see that module for
    why this is a JSON blob rather than a column per field: it unifies
    what used to be three separate hardcoded structures (nav label, home
    teaser, page tagline, full body) into one admin-editable record per
    page, and lets an admin add a whole new page without a migration."""

    __tablename__ = "content_page"

    slug: Mapped[str] = mapped_column(String(48), primary_key=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_in_nav: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    translations: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("admin_user.id"), nullable=True)


class ContentPageVersion(Base):
    """Snapshot of a ContentPage's translations taken immediately before
    each overwrite, so an admin can see history and roll back a bad
    edit without needing a full external CMS."""

    __tablename__ = "content_page_version"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(48), ForeignKey("content_page.slug", ondelete="CASCADE"), nullable=False, index=True)
    translations: Mapped[dict] = mapped_column(JSON, nullable=False)
    saved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    saved_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    saved_by_username: Mapped[str | None] = mapped_column(String(64), nullable=True)


class FaqItem(Base):
    """One row per FAQ entry. Same translations-blob pattern as
    ContentPage, validated against content_schema.FAQ_FIELDS."""

    __tablename__ = "faq_item"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    translations: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("admin_user.id"), nullable=True)


class Appointment(Base):
    """One row per booking. `date`/`time` are kept as separate strings
    (ISO date, 'HH:MM') rather than a single datetime because every
    piece of booking logic — slot generation, availability, the
    workdays/hours settings — is inherently day-and-slot shaped, not a
    continuous timestamp; storing it that way avoids timezone-conversion
    bugs creeping into what's fundamentally a "which slot" question.
    The confirmation code (id) is the primary key and is what a visitor
    quotes back to look up, cancel, or reschedule — always paired with
    the email on file, checked in booking_service.py."""

    __tablename__ = "appointment"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM, 24h
    # The IANA timezone booking.timezone held *at the moment this
    # appointment was booked* (or last rescheduled) — snapshotted here
    # rather than re-read live from settings by everything that later
    # needs to turn date/time back into an actual instant (notice-window
    # checks, the Google Calendar event, drift detection). Without this,
    # an admin changing booking.timezone after appointments exist
    # silently reinterprets every existing appointment's stored
    # date/time under the new zone. Nullable for rows created before
    # this column existed; every read falls back to the live
    # booking.timezone setting when null (see booking_service.py /
    # calendar_sync_service.py), which is exactly today's behavior for
    # that legacy data — this can only protect appointments booked from
    # here on, not retroactively recover a timezone nothing recorded.
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lang: Mapped[str] = mapped_column(String(8), default="en", nullable=False)  # for notification template language
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    # Free-text description, kept for appointments made before a Service
    # catalog existed (and as a fallback if someone books without
    # picking one). Not shown on the booking form once service_id is set.
    service: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    # Nullable on purpose: a booking made against the catalog (Pass 8)
    # points here; nothing enforces every booking having one, since a
    # site can run booking without ever defining a Service, exactly as
    # it did before this pass. When null, slot duration/buffers fall
    # back to the global booking.slot_minutes setting — see
    # booking_service.py.
    service_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("service.id"), nullable=True)
    notes: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    # confirmed | pending | cancelled. Pass 10 (docs/CALENDAR_MODULE_PLAN.md):
    # a Service with requires_confirmation=True produces a "pending"
    # booking instead of an immediately "confirmed" one — see
    # booking_service.py::create_appointment. A pending appointment
    # holds its slot exactly like a confirmed one (booking_service.py
    # ::_booked_intervals), a deliberate product decision documented in
    # PASS10_NOTES.md: double-booking while awaiting approval is a
    # worse failure mode than a slot briefly looking unavailable.
    status: Mapped[str] = mapped_column(String(16), default="confirmed", nullable=False)
    # Set only when a pending appointment is admin-accepted; stays null
    # for anything that was auto-confirmed, so "was this ever pending"
    # is reconstructable from the data without a separate history table.
    confirmed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Pass 12: set when this appointment's confirmation created a
    # matching event on the connected Google Calendar, so a later
    # cancel/reschedule knows which external event to delete/update
    # instead of leaving a stale entry on the business's real calendar.
    # Null for every appointment made before sync existed, and for any
    # made while sync was off or event-creation itself failed
    # (best-effort — see calendar_sync_service.py).
    external_event_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Set by calendar_sync_service.detect_drift when the linked Google
    # Calendar event no longer matches this row (edited or deleted
    # directly on Google's side rather than through this app) — a short
    # human-readable description of the mismatch, or null when nothing's
    # flagged. Cleared automatically once the mismatch resolves (another
    # sync sees them match again) or an admin acts on it (reschedule/
    # edit-in-place pushes our side back to Google).
    calendar_drift: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (Index("ix_appointment_date_status", "date", "status"),)


class BookingLock(Base):
    """A single sentinel row (id=1, always present) used purely as a
    serialization point for booking_service._acquire_booking_lock.

    Why this exists: create_appointment/reschedule_appointment read
    available_slots() and then insert/move an appointment as two
    separate steps. Without something forcing concurrent requests to
    run that check-then-write one at a time, two visitors requesting
    the same slot in the same instant can both pass the availability
    check before either has committed, and both get booked into it.
    _acquire_booking_lock closes that gap by taking a real write-lock
    on this row (via UPDATE) before the check runs, and holding it
    until the caller's transaction commits or rolls back — so the next
    request's check can't start until the previous request's write has
    actually landed. See booking_service.py for the acquire/seed logic."""

    __tablename__ = "booking_lock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    touched_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class AppointmentQuestionAnswer(Base):
    """One row per answer to a Service's custom intake question,
    captured at booking time. `question_label` is a denormalized copy
    of the question's label as it read when this appointment was
    booked — if an admin later edits or deletes the question, this
    historical answer still reads sensibly instead of showing a blank
    or a dangling id. `question_id` is kept (nullable, SET NULL on
    delete) purely so a future UI *can* still link back to the live
    question when it still exists; nothing depends on it being set."""

    __tablename__ = "appointment_question_answer"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("appointment.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("service_custom_question.id", ondelete="SET NULL"), nullable=True
    )
    question_label: Mapped[str] = mapped_column(String(200), nullable=False)
    answer: Mapped[str] = mapped_column(String(2000), default="", nullable=False)


class Service(Base):
    """One row per bookable service — the calendar module's equivalent
    of Cal.com's per-user "event type," scoped to this single business
    instead of to an account. This is Pass 0 of the plan in
    docs/CALENDAR_MODULE_PLAN.md: the admin-managed catalog of services
    exists as its own resource, but the public booking flow
    (app/booking_service.py, app/models.py::Appointment) is not yet
    wired to it — that migration is the next slice of Pass 8. Until
    then `booking.slot_minutes` in the settings registry remains the
    live scheduling value; it becomes only a default once Appointment
    gains a service_id.

    `translations` follows the same {lang_code: {field_key: str}}
    pattern as ContentPage, for a public-facing name/description once
    the public booking page is updated to show these."""

    __tablename__ = "service"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_before_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # in_person | phone | link_provided — no embedded video-conferencing
    # integration; see docs/CALENDAR_MODULE_PLAN.md §2.5 for why that
    # was deliberately dropped from this plan.
    location_type: Mapped[str] = mapped_column(String(20), default="in_person", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    translations: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("admin_user.id"), nullable=True)

    questions: Mapped[list["ServiceCustomQuestion"]] = relationship(
        back_populates="service", cascade="all, delete-orphan", order_by="ServiceCustomQuestion.position"
    )

    __table_args__ = (Index("ix_service_active_position", "is_active", "position"),)


class ServiceCustomQuestion(Base):
    """A per-service intake question for the public booking form
    (rendered once the public flow adopts Service in a later pass).
    Its own table rather than a JSON column on Service, since questions
    are added/removed/reordered independently of the service they
    belong to, and each answer will need a stable id to reference back
    to (AppointmentQuestionAnswer, added alongside the public wiring)."""

    __tablename__ = "service_custom_question"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    service_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # text | textarea | number | bool | phone
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    service: Mapped["Service"] = relationship(back_populates="questions")


class AvailabilityRule(Base):
    """Pass 9 (docs/CALENDAR_MODULE_PLAN.md): admin-editable business
    hours, replacing the four global booking.workdays/day_start_hour/
    day_end_hour settings with real rows an admin can add, edit, and
    delete. A rule is either `weekly` (recurring, tied to a weekday) or
    `date_override` (a specific date — a holiday closure, or a one-off
    change in hours). `service_id` null means "business-wide default";
    a non-null value overrides that default for just one service.

    Precedence, most to least specific, is resolved in
    availability_service.effective_ranges: service+date override >
    business-wide date override > service weekly > business-wide
    weekly. If literally no AvailabilityRule exists anywhere yet (a
    fresh install, or one that hasn't been migrated onto this model),
    booking_service.py falls back to the legacy booking.workdays/
    day_start_hour/day_end_hour settings entirely, so nothing breaks
    for an install that predates this pass."""

    __tablename__ = "availability_rule"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    service_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("service.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # weekly | date_override
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Monday .. 6=Sunday
    date: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)  # YYYY-MM-DD
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # HH:MM
    end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # HH:MM
    # A date_override row can mark a date fully closed (holiday). A
    # weekly row could too, defensively, though the normal way to
    # represent "closed on Sundays" is simply not having a weekly rule
    # for Sunday at all.
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_availability_rule_service_weekday", "service_id", "weekday"),
        Index("ix_availability_rule_service_date", "service_id", "date"),
    )


class Webhook(Base):
    """Pass 11 (docs/CALENDAR_MODULE_PLAN.md): lets the business wire
    external systems into calendar events without polling. `events` is
    a JSON list of event-name strings validated against the fixed
    allow-list in webhook_service.py — the same six strings
    notification_service.py's six notify_booking_* functions already
    correspond to one-for-one.

    `secret` is Fernet-encrypted at rest, identical treatment to
    `SiteSetting.is_secret` rows (see app/security.py) — generated once
    at creation, returned in plaintext exactly once (the creation
    response), never again. Regenerating replaces it the same way."""

    __tablename__ = "webhook"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted
    events: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class WebhookDelivery(Base):
    """One row per delivery attempt (no retries in this first pass —
    see PASS11_NOTES.md), so the admin UI's delivery log is a direct,
    unfiltered record of what actually happened. `response_status`
    null means the request never completed at all (DNS failure,
    connection refused, timeout) as distinct from the target
    responding with an HTTP error status, which is recorded as-is."""

    __tablename__ = "webhook_delivery"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    webhook_id: Mapped[str] = mapped_column(String(32), ForeignKey("webhook.id", ondelete="CASCADE"), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class CalendarCredential(Base):
    """Pass 12 (docs/CALENDAR_MODULE_PLAN.md): one connected external
    calendar account for the whole business — deliberately not a
    per-admin-user thing, since there's one calendar to sync, not one
    per admin login. `provider` is a plain string rather than a
    hardcoded enum so a second provider (Office 365, CalDAV — neither
    built yet, see docs/CALENDAR_MODULE_PLAN.md §2.4 Pass 12) wouldn't
    need a schema migration, just a new value.

    `access_token`/`refresh_token` get the exact same at-rest treatment
    as `Webhook.secret` and `SiteSetting.is_secret` rows — Fernet-
    encrypted via app/security.py, no new crypto path. `calendar_id` is
    nullable: a row can exist mid-connect (tokens stored, calendar not
    yet chosen) before `POST /admin/api/calendar-sync/select` sets it
    and flips `is_active`."""

    __tablename__ = "calendar_credential"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(32), default="google", nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted
    token_expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calendar_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    connected_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # Google's incremental-sync cursor (Events.list `nextSyncToken`) —
    # null until the first successful detect_drift run, at which point
    # every later run asks Google for "only what changed since this"
    # instead of re-listing the whole calendar. A 410 response means
    # Google considers it stale; calendar_sync_service clears it back to
    # null and falls back to a fresh time-bounded listing.
    sync_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Lead(Base):
    """A contact worth following up with — captured automatically
    whenever a booking is made (source='booking') or an email address
    appears in a chat conversation (source='chat'), rather than
    requiring a separate lead-capture form. Multiple touches from the
    same email upsert into one record (see leads_service.py) so a
    visitor who chats and later books shows up as one lead with a
    fuller picture, not two disconnected ones."""

    __tablename__ = "lead"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # chat | booking
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    # new | contacted | qualified | converted | lost
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)  # admin's own notes
    transcript: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # [{from, text, at}]
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class KnowledgeSource(Base):
    """A document (uploaded file) or web page an admin has added so the
    chat assistant can ground its answers in real, current information
    instead of only what's baked into the system prompt — a Perennia
    org chart, a pricing sheet, a policy document, a page from the
    live site, etc. No embeddings/vector search: chat_service.py
    concatenates the (capped) text of every active source into the
    system prompt for each reply, the same approach used by the
    reference implementation this was modeled on. `source_ref` is the
    original filename or the URL; re-fetching (URL sources only)
    updates `text` in place rather than creating a new row, so a
    source's identity persists across refreshes."""

    __tablename__ = "knowledge_source"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # file | url
    content_type: Mapped[str] = mapped_column(String(16), nullable=False)  # pdf | docx | html | text | markdown
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(2048), nullable=False)  # filename or URL
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    chars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("admin_user.id"), nullable=True)
