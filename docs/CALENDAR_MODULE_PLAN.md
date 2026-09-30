# Calendar Module — Feature Inventory & Build Plan

Reference app: [`BT-Rajan/calendar-sample`](https://github.com/BT-Rajan/calendar-sample)
(a Cal.com / Calendso fork — Next.js + Prisma + tRPC)
Target app: `perennia-v2` (FastAPI + SQLAlchemy + Pydantic backend, Vite + React
public site, separate Vite + React admin dashboard)

This document has two parts:

1. **What `calendar-sample` actually does** — a feature inventory, read directly
   out of its Prisma schema, routers, and pages.
2. **How we bring the useful parts into `perennia-v2`** — mapped onto our stack
   and our existing `booking.*` module, delivered as a sequence of passes in
   the style of `backend/PASS1_NOTES.md` … `PASS7_NOTES.md`.

---

## 1. Feature inventory — `calendar-sample`

Derived from `prisma/schema.prisma` (models: `EventType`, `User`, `Team`,
`Membership`, `Booking`, `Attendee`, `BookingReference`, `Schedule`,
`Availability`, `SelectedCalendar`, `EventTypeCustomInput`, `Payment`,
`Webhook`, `ReminderMail`, `Credential`, `DailyEventReference`), the
`server/routers/` tRPC routers, and `pages/`.

### 1.1 Event types
- A user (or team) defines one or more **event types**: title, slug,
  description, length in minutes, a **scheduling type**
  (`ROUND_ROBIN` / `COLLECTIVE` for team events), position/ordering.
- **Period type** controls how far the booking window extends:
  `UNLIMITED`, `ROLLING` (N days from today), or `RANGE` (fixed start/end
  date) — `EventType.periodType` / `periodDays` / `periodStartDate` /
  `periodEndDate`.
- **Buffer time** before/after a booking (`beforeEventBuffer`,
  `afterEventBuffer`), **minimum booking notice**
  (`minimumBookingNotice`), and configurable **slot interval**.
- **Custom booking questions** (`EventTypeCustomInput`): per event type,
  admin-defined extra fields (text / textlong / number / bool / phone),
  each markable required, shown on the public booking page.
- **Location** options per event type (in-person address, phone, Zoom,
  Daily.co video, etc. — `lib/location.ts`), and a **hidden/placeholder**
  flag so an event type can exist without being publicly bookable.
- **Custom event name** template, **custom brand color**,
  **hide-branding** toggle — light per-tenant white-labeling.

### 1.2 Availability
- A **Schedule** is a named, reusable set of weekly working hours; a user
  can have several (e.g. "Default", "Sales hours") and assign a specific
  one per event type, or fall back to their default.
- **Availability** rows are `(day-of-week or date, start time, end time)`
  ranges — supports both recurring weekly rules and one-off date
  overrides.
- Slot generation (`lib/slots.ts`, `pages/api/availability/*`) combines:
  the schedule's open hours, minus already-booked times, minus buffer
  time, minus anything blocked by a **connected external calendar**
  (busy-time lookup), respecting the event type's own timezone and the
  viewer's browser timezone.
- `test/lib/slots.test.ts` / `getWorkingHours.test.ts` cover the slot math
  directly — this is the part of the reference app worth the most care to
  port correctly, since it's pure timezone/interval arithmetic and easy to
  get subtly wrong (DST edges, cross-midnight ranges, etc).

### 1.3 Bookings
- `Booking` records the confirmed appointment: event type, organizer,
  one or more `Attendee`s (each with their own name/email/timezone —
  supports guests), start/end time, `uid` (public confirmation code),
  title, description, `BookingStatus` (`ACCEPTED` / `PENDING` /
  `CANCELLED` / `REJECTED`), and a `rescheduled` link back to the prior
  booking it replaced.
- **Booking requests**: an event type can require organizer confirmation
  before a booking is `ACCEPTED` (vs. auto-confirm) — `PENDING` status +
  organizer accept/reject flow, with its own email templates
  (`organizer-request-email`, `organizer-request-reminder-email`).
- Self-service **cancel** and **reschedule** by the attendee, gated by the
  same notice-window logic as the original booking.
- `BookingReference` rows link a `Booking` to the external artifacts it
  created — a Google Calendar event ID, a Zoom meeting ID — so those can
  be cleaned up / updated on cancel or reschedule.

### 1.4 Team scheduling
- `Team`, `Membership` (`role`: OWNER / MEMBER, plus invite-accepted
  flag), team-level event types with `ROUND_ROBIN` (distributes across
  available members) or `COLLECTIVE` (requires all members free)
  scheduling.
- Team branding: slug, logo, bio, custom brand color; a public
  `/team/[slug]` booking page separate from individual `/[user]` pages.

### 1.5 Calendar & conferencing integrations
- `lib/integrations/`: Google Calendar, Office 365 Calendar, Apple
  Calendar (CalDAV), generic CalDAV — each an adapter implementing
  "list calendars," "get busy times," "create/update/delete event."
- `SelectedCalendar` — which of a user's connected calendars are checked
  for conflicts vs. purely available for writing new events to.
- Video: Zoom and Daily.co adapters (`DailyVideoApiAdapter`,
  `ZoomVideoApiAdapter`) auto-create a meeting link on booking and store
  it on the `Booking`/`DailyEventReference`.
- OAuth `Credential` model stores per-user tokens for each connected
  service; add/callback routes live under
  `pages/api/integrations/{service}/{add,callback}.ts`.

### 1.6 Payments (enterprise/`ee/` folder)
- Stripe: `Payment` model, `PaymentType` enum, checkout + webhook
  handling (`ee/pages/api/integrations/stripepayment/*`) — a paid event
  type isn't confirmed until payment succeeds; refund-on-cancel handling
  with its own failure-notification email.

### 1.7 Notifications
- `lib/emails/templates/`: scheduled / rescheduled / cancelled /
  declined / awaiting-payment, one pair each for attendee and organizer,
  plus a forgot-password email and a team-invite email — all built on a
  shared `lib/emails/templates/common/` layout.
- `ReminderMail` + `pages/api/cron/bookingReminder.ts` — a cron-triggered
  reminder sent ahead of the appointment, deduplicated via a
  `ReminderType` + booking pairing.

### 1.8 Webhooks
- `Webhook` model: per-user, a target URL + subscribed
  `WebhookTriggerEvents` (booking created / cancelled / rescheduled).
  `lib/webhooks/subscriptions.tsx` fires an HMAC-signed payload
  (`lib/webhooks/sendPayload.tsx`) on each event — lets a tenant wire the
  calendar into their own systems without polling.

### 1.9 Account / security
- Auth via `next-auth` (`pages/api/auth/[...nextauth].tsx`), email
  verification, forgot/reset password, **TOTP two-factor auth**
  (`otplib`, `pages/api/auth/two-factor/*`).
- `UserPlan` (FREE / TRIAL / PRO) and a `downgradeUsers` cron —
  subscription-gating that doesn't apply to us but is worth naming so we
  consciously *don't* port it.

### 1.10 Everything intentionally out of scope for us
Multi-tenant SaaS billing (`UserPlan`, Stripe *subscriptions* as opposed
to one-off event payments), the `ee/` licensing split itself, and
`next-auth` as an auth system (we already have our own admin session
model in `app/security.py`) are all artifacts of "this is a
multi-tenant, sign-up-your-own-account product." Perennia is a single
business's site; there's one calendar, not one per signed-up user. We
port the *scheduling* feature set, not the SaaS shell around it.

---

## 2. Mapping onto `perennia-v2`

### 2.1 What we already have
`app/models.py::Appointment` + `app/booking_service.py` is a *complete but
minimal* version of §1.1–1.3 collapsed into a single implicit event type:
one global slot length, one set of business hours, no per-service
duration or location, no organizer confirmation step, no external
calendar sync. `booking.*` in `settings_registry.py` holds the config
that in `calendar-sample` would live on `EventType` + `Schedule`. This is
good news — the slot-generation core (`available_slots`), the
notice-window math, and the confirmation-code pattern don't need to be
rebuilt, only generalized.

### 2.2 Design decisions (deliberately narrower than the reference app)
- **No multi-tenant `User`/`Team` layer.** "Organizer" stays implicit —
  it's the business. What generalizes is **`Service`** (≈ `EventType`
  without the per-user ownership): name, duration, buffer, its own
  optional hours override, its own custom questions, its own
  confirm-required flag. No round-robin/collective scheduling — there's
  one calendar.
- **`Schedule`/`Availability` becomes a single set of weekly hours plus
  date-specific overrides** (holidays, one-off closures, one-off extra
  hours), attached to the business, with an optional per-`Service`
  override — not a per-user library of named schedules.
- **Calendar sync (Google/Office365/CalDAV) is a later, explicitly
  optional pass**, gated behind a `features.*` flag exactly like
  `features.booking_enabled` today — most of the value (a real
  scheduling module instead of a single-service slot picker) is
  delivered before we touch OAuth with a third party.
- **No video-conferencing integration.** `calendar-sample`'s Zoom/Daily
  adapters are explicitly out of scope for this plan — see §2.5. A
  `Service.location` free-text/enum field (in person / phone / "link
  provided separately") covers what the business actually needs without
  a third-party meeting-provider dependency.
- **Payments**: only relevant if a `Service` is ever paid; kept as a
  stubbed hook (`payment_required` bool on `Service`) until there's an
  actual product need, rather than importing Stripe subscriptions
  wholesale.
- **Webhooks**: straightforward to port (HMAC-signed POST on
  created/cancelled/rescheduled) and cheap relative to its usefulness —
  early pass, reusing the existing `notification_service.py` event
  points.
- Every new table goes through the same patterns already established:
  `Base`/`Mapped[...]` in `models.py`, config through
  `settings_registry.py` (never a new hardcoded column for something an
  admin should be able to change), admin routes under `/admin/api/...`
  behind `get_current_admin` + `require_csrf`, public routes under
  `/api/...` behind `slowapi` rate limits, audit-logged writes via
  `AuditLog`, and Pydantic request models in the router (matching
  `public_booking.py`'s style) rather than a separate schemas file.

### 2.3 Proposed data model additions
```
Service                 id, name, slug, duration_minutes, buffer_before_minutes,
                         buffer_after_minutes, requires_confirmation, payment_required,
                         location_type (in_person|phone|link_provided), is_active,
                         position, translations (JSON, i18n like ContentPage)

ServiceCustomQuestion    id, service_id FK, kind (text/textarea/number/bool/phone),
                         label, required, position

AvailabilityRule         id, kind (weekly|date_override), weekday (0-6, nullable),
                         date (nullable, for one-off overrides), start_time, end_time,
                         is_closed (bool — an override can also mark a date fully closed)
                         [replaces the single booking.workdays/day_start_hour/day_end_hour
                          settings with data an admin edits as rows, same spirit as the
                          content_page -> content_page_version pattern already in use]

Appointment              (existing table) + service_id FK, status gains "pending"
                         alongside confirmed/cancelled, confirmed_at

AppointmentQuestionAnswer id, appointment_id FK, question_id FK, answer (text)

Webhook                  id, url, secret, events (JSON list), is_active
WebhookDelivery           id, webhook_id FK, event, payload (JSON), response_status,
                         attempted_at   [audit trail for the admin UI, mirrors AuditLog]
```

### 2.4 Passes — detailed requirements

Each pass is scoped the way the existing `PASS*_NOTES.md` files are:
backend-first, its own tests, its own `PASSn_NOTES.md` explaining what
changed and why, admin UI catching up once the API is stable. Numbering
continues from the existing `PASS7_NOTES.md` (admin dashboard UI). No
video-conferencing pass exists in this plan — see §2.5.

---

#### Pass 8 — Services (multi–event-type foundation)

**Goal.** Replace the single implicit "one service" booking model with
real, admin-managed `Service` rows, each with its own duration, buffers,
and custom intake questions — without breaking any currently-booked
appointment.

**Data model**
- `Service`: `id` (uuid hex, PK), `name` (str ≤120, required),
  `slug` (str ≤64, unique, auto-generated from `name` via the existing
  `slugify` pattern if not supplied), `duration_minutes` (int, 5–480),
  `buffer_before_minutes` (int, 0–120, default 0),
  `buffer_after_minutes` (int, 0–120, default 0),
  `requires_confirmation` (bool, default False — value unused until
  Pass 10, stored now to avoid a later migration),
  `payment_required` (bool, default False — stubbed, no payment logic
  yet), `location_type` (enum `in_person|phone|link_provided`, default
  `in_person`), `is_active` (bool, default True), `position` (int,
  default 0), `translations` (JSON, same shape/validation pattern as
  `ContentPage.translations`), `created_at`/`updated_at`.
- `ServiceCustomQuestion`: `id`, `service_id` FK (`ondelete=CASCADE`),
  `kind` (enum `text|textarea|number|bool|phone`), `label` (str ≤200,
  required), `required` (bool, default False), `position` (int).
- `Appointment.service_id`: nullable FK on add; a migration script
  creates one `Service` row ("General", duration = current
  `booking.slot_minutes` setting, buffers 0) and backfills every
  existing `Appointment.service_id` to it, then the column can be made
  `nullable=False` for new rows going forward. `booking.slot_minutes`
  in the settings registry becomes documented as "default duration
  for a new Service" rather than the live scheduling value.
- `AppointmentQuestionAnswer`: `id`, `appointment_id` FK
  (`ondelete=CASCADE`), `question_id` FK (`ondelete=SET NULL` — a
  deleted question shouldn't delete historical answers), `question_label`
  (str, denormalized copy of the label at booking time, so history
  survives a later question edit/delete), `answer` (text ≤2000).

**API — admin** (`admin_services.py`, prefix `/admin/api/services`,
behind `get_current_admin` + `require_csrf`)
- `GET /` — list all services (active and inactive), ordered by
  `position`.
- `POST /` — create; body validates `duration_minutes` ≥ buffers'
  practical minimum (a slot shorter than its own buffers is rejected
  with a 422), `slug` uniqueness enforced at the DB and surfaced as a
  409 on conflict.
- `GET /{id}` — full detail including its `ServiceCustomQuestion` list.
- `PATCH /{id}` — partial update; changing `duration_minutes` on a
  service with future confirmed appointments does **not** retroactively
  resize them (documented explicitly, since this is an easy source of
  silent data corruption).
- `DELETE /{id}` — soft-delete only (`is_active = False`); a service
  with any `Appointment` referencing it can never be hard-deleted.
- `POST /{id}/questions`, `PATCH /{id}/questions/{qid}`,
  `DELETE /{id}/questions/{qid}` — custom question CRUD; `position`
  reordering via a bulk `PUT /{id}/questions/reorder` taking an ordered
  id list (matches the reorder pattern already used for
  `ContentPage.order`/`FaqItem.order`).
- Every write logs to `AuditLog` (`action="service.create"` etc.),
  matching the existing convention.

**API — public**
- `GET /api/booking/services` — active services only, each including
  its custom questions; returned in `position` order. Replaces the
  implicit "there is one service" assumption on the public booking
  page.
- `GET /api/booking/slots?service_id=&date=` — `booking_service.
  available_slots` signature gains a required `service_id`; 404 if the
  service is inactive or doesn't exist. Slot arithmetic uses the
  service's own `duration_minutes` + both buffers instead of the global
  `booking.slot_minutes`.
- `POST /api/booking/appointments` — body gains `service_id` (required)
  and `answers: [{question_id, answer}]`. Server re-validates every
  `required=True` question has a non-empty answer (never trust the
  client-side form) and rejects (422) any `question_id` that doesn't
  belong to the given `service_id`.

**Admin UI** — none in this pass; Pass 13 (renumbered) covers it. The
existing `NewAppointmentForm.jsx`/`BookingPanel.jsx` on the *public*
site do get a service picker (first step before the date/slot picker
currently shown), since the public booking flow can't function without
one.

**Tests**
- Two services with different durations booked back-to-back on the same
  day don't produce overlapping/undersized gaps.
- Buffer time is excluded from `available_slots` for services that have
  it, and unaffected for services that don't.
- Required-question omission is rejected server-side even if the public
  form is bypassed (direct API call).
- Migration test: a pre-migration `Appointment` fixture ends up pointed
  at the backfilled "General" service with an unchanged `date`/`time`.

**Definition of done.** Every existing booking-flow test still passes
unmodified against the "General" service; new tests above pass; no
change to appointment confirmation-code format or email templates.

---

#### Pass 9 — Real availability model

**Goal.** Replace the four global `booking.*` hour/workday settings
with admin-editable `AvailabilityRule` rows supporting per-service
overrides and one-off date exceptions, with zero behavior change on
the day of cutover.

**Data model**
- `AvailabilityRule`: `id`, `service_id` (nullable FK — null means
  "business-wide default rule"), `kind` (enum `weekly|date_override`),
  `weekday` (int 0–6, required when `kind=weekly`, else null),
  `date` (ISO date string, required when `kind=date_override`, else
  null), `start_time`/`end_time` (`HH:MM`, required unless
  `is_closed=True`), `is_closed` (bool, default False — a
  `date_override` row with `is_closed=True` and no times marks a full
  closure, e.g. a holiday), `created_at`/`updated_at`.
  Constraint: `CHECK` (enforced in the service layer, not just the DB,
  since SQLite's CHECK support is limited) that exactly one of
  `weekday`/`date` is set per `kind`.
- Migration: for each weekday currently in `booking.workdays`, insert
  one `AvailabilityRule(service_id=None, kind="weekly", weekday=d,
  start_time=booking.day_start_hour, end_time=booking.day_end_hour)`.
  The four settings (`workdays`, `day_start_hour`, `day_end_hour`) stay
  in the registry but become **read-only / deprecated**, displayed in
  the admin settings page as "migrated to Availability — see
  Availability page" rather than deleted outright, so an admin who
  built automation against the settings API isn't surprised by a 404.

**API — admin** (`admin_availability.py`, prefix
`/admin/api/availability`)
- `GET /rules?service_id=` — list (service-specific rules if given,
  else business-wide rules, i.e. `service_id IS NULL`).
- `POST /rules` — create a weekly or date-override rule; overlapping
  weekly ranges for the same `(service_id, weekday)` are rejected (409)
  rather than silently merged, so the admin UI never has to reconcile
  ambiguous overlapping hours.
- `PATCH /rules/{id}`, `DELETE /rules/{id}`.
- `GET /effective?service_id=&date=` — debugging/preview endpoint that
  returns the resolved hours for a specific service+date after
  applying: service-specific weekly rule → business-wide weekly rule →
  service-specific date override → business-wide date override (most
  specific wins), so an admin can verify "what will Tuesday actually
  look like" without reading raw rule rows.

**Slot-generation rewrite**
- `booking_service._all_slots_for_day(cfg, date, service)` resolves
  effective hours via the precedence above instead of reading
  `cfg["workdays"]`/`day_start_hour`/`day_end_hour` directly.
- A `date_override` with `is_closed=True` short-circuits to "no slots,"
  regardless of what the weekly rule for that weekday would say.
- Timezone handling is unchanged (`booking.timezone` stays a global
  setting — no per-service timezones planned; a single business
  operates in one timezone).

**Tests — must include, before the cutover ships**
- DST spring-forward day: a weekly rule spanning the "missing hour"
  doesn't produce a slot inside the gap or crash.
- DST fall-back day: no duplicate slot for the repeated hour.
- A date-override closure correctly suppresses an otherwise-open
  weekday.
- A service-specific rule overrides the business-wide rule for the same
  weekday; a service with no rules of its own falls back cleanly.
- Regression: every Pass-8 slot test still passes against the rewritten
  function with equivalent `AvailabilityRule` fixtures standing in for
  the old settings-based fixtures.

**Admin UI** — none in this pass (bundled into Pass 13).

**Definition of done.** `booking.workdays`/`day_start_hour`/
`day_end_hour` are provably unused by any code path (grep-clean outside
migration/legacy-display code); all DST/override tests above pass;
existing appointments unaffected.

---

#### Pass 10 — Confirmation workflow

**Goal.** Let a `Service` require organizer approval before a booking
is final, with its own status, notification, and admin action surface.

**Data model**
- `Appointment.status` gains `"pending"` as a valid value alongside the
  existing `"confirmed"`/`"cancelled"` (column is already a plain
  `String`, no enum migration needed — just widen the validated set in
  `booking_service.py`).
- `Appointment.confirmed_at` (nullable datetime) — set when a pending
  appointment is accepted; null for appointments that were auto-confirmed
  (so "was this ever pending" stays reconstructable from the data).

**Product decision to document explicitly in `PASS10_NOTES.md`
(not assumed silently):** does a `pending` appointment hold its slot
(blocking other bookers) or not? Recommendation: **it holds the slot**
— the alternative (double-taking the same slot while awaiting approval)
creates a worse failure mode for a small business than a slot briefly
looking unavailable. `available_slots` therefore treats `pending` the
same as `confirmed` when computing `_booked_times`.

**Business logic**
- `create_appointment`: if `service.requires_confirmation`, new rows are
  created with `status="pending"` instead of `"confirmed"`; response
  `ok=True` but includes `"pending": true` so the public UI can show
  "request sent" instead of "confirmed" messaging.
- `admin_accept_appointment(db, appt_id)`: valid only from `pending`;
  sets `status="confirmed"`, `confirmed_at=now`; invalid-state transition
  (e.g. already cancelled) returns a typed error, not a generic 500.
- `admin_reject_appointment(db, appt_id, reason: str = "")`: valid only
  from `pending`; sets `status="cancelled"`; `reason` stored in
  `Appointment.notes` prefixed distinguishably (e.g.
  `"[declined] {reason}"`) rather than a new column, consistent with
  keeping the schema lean.
- Self-service cancel/reschedule (existing `cancel_appointment`/
  `reschedule_appointment`) work unchanged on `pending` rows — a
  requester can withdraw a request they haven't heard back on yet.

**API**
- `admin_booking.py`: `POST /admin/api/booking/appointments/{id}/accept`,
  `POST /admin/api/booking/appointments/{id}/reject` (body:
  `{"reason": str = ""}`).
- `admin_booking.py` `GET /appointments` gains a `status=pending` filter
  value (already supports arbitrary status filtering — no shape change,
  just a new valid value to filter by).

**Notifications** (`notification_service.py`)
- New: `notify_booking_requested` (to organizer, on create when pending),
  `notify_booking_accepted` (to attendee), `notify_booking_declined` (to
  attendee, includes `reason` if present) — each following the existing
  template-pair convention (attendee vs organizer facing).
- `lang` on the stored `Appointment` continues to select the template
  language, unchanged from the existing pattern.

**Tests**
- A `requires_confirmation=True` service produces a `pending`
  appointment that occupies the slot (verified via a second booking
  attempt on the same slot failing with `slot_unavailable`).
- Accept/reject only succeed from `pending`; both are rejected (typed
  error, not exception) from `confirmed` or `cancelled`.
- Each of the three new notification triggers fires exactly once per
  transition (no double-send on retry/idempotent re-calls).

**Definition of done.** A non-confirmation service's behavior is
byte-for-byte unchanged from Pass 9; a confirmation-required service's
full request → accept and request → reject paths are covered by tests
and match the documented slot-holding decision above.

---

#### Pass 11 — Webhooks

**Goal.** Let the business wire external systems (its own CRM, a
spreadsheet automation, Slack, etc.) into calendar events without
polling, via signed outbound HTTP calls.

**Data model**
- `Webhook`: `id`, `url` (str ≤2048, must be `https://` in production —
  `http://` allowed only when `settings.is_production` is False, to
  support local testing), `secret` (str, generated server-side,
  `Fernet`-style handling identical to how `SiteSetting.is_secret`
  values are treated — never returned in a `GET` response body after
  creation, only a masked placeholder), `events` (JSON list of event
  names, validated against a fixed allow-list — see below), `is_active`
  (bool, default True), `created_at`/`updated_at`.
- `WebhookDelivery`: `id`, `webhook_id` FK (`ondelete=CASCADE`), `event`
  (str), `payload` (JSON, the exact body sent), `response_status` (int,
  nullable — null means "request never completed," e.g. DNS/timeout
  failure), `attempted_at` (datetime), `duration_ms` (int).

**Event allow-list** (exact strings, matching `notification_service.py`
trigger points plus Pass 10's new ones):
`booking.confirmed`, `booking.cancelled`, `booking.rescheduled`,
`booking.requested`, `booking.accepted`, `booking.declined`.

**Delivery mechanics**
- Fired synchronously but non-blocking to the request/response cycle
  where practical: dispatched via the same background-safe pattern
  `notification_service.py` already uses for outbound email (no new
  async framework introduced).
- Payload: `{"event": ..., "appointment": {...same shape as
  booking_service._serialize...}, "sent_at": iso8601}`.
- Signature header `X-Perennia-Signature: sha256=<hmac hex>` computed
  over the raw JSON body with the webhook's `secret` — same scheme
  `calendar-sample`'s `sendPayload.tsx` uses, so it's a familiar
  integration shape for anyone who's consumed a Cal.com webhook before.
- **No automatic retries in this pass.** A failed delivery is logged to
  `WebhookDelivery` with its failure status/timeout and surfaced in the
  admin UI; retry logic is deferred until there's evidence it's needed
  (keeps this pass small and avoids building a queue/backoff system
  speculatively).
- One webhook subscribed to multiple events fires one delivery per
  matching event, not a single batched call.

**API**
- `admin_webhooks.py`, prefix `/admin/api/webhooks`: `GET /`,
  `POST /` (returns the `secret` **once**, in the creation response
  only), `PATCH /{id}` (cannot change `secret` — only regenerate via a
  dedicated `POST /{id}/regenerate-secret`), `DELETE /{id}`,
  `GET /{id}/deliveries` (paginated, most recent first),
  `POST /{id}/test` (fires a synthetic `booking.confirmed` payload
  against a fabricated fixture appointment, for the admin to verify
  their endpoint before going live).

**Tests**
- Signature verification: a local Flask/FastAPI stub receiver in the
  test suite recomputes the HMAC and asserts it matches.
- A webhook subscribed only to `booking.cancelled` never receives a
  `booking.confirmed` delivery.
- A non-2xx response from the receiver is recorded with its actual
  status, not swallowed.
- `secret` is never present in any `GET` response body after the
  initial `POST`.

**Definition of done.** All six allow-listed events are wired to their
existing trigger points with no change to the trigger points'
surrounding logic; delivery log is queryable and accurate; `secret`
handling passes the same scrutiny as any other credential in this
codebase (masked at rest in responses, never logged in plaintext).

---

#### Pass 12 — External calendar sync (opt-in, Google first)

**Goal.** Let the business connect one real Google Calendar so that
events on it block availability, without introducing a new secret-
handling path outside what `security.py` already provides.

**Scope guard.** Entirely behind `features.calendar_sync_enabled`
(new registry flag, default `False`, same pattern as
`features.booking_enabled`). Office 365 / CalDAV are explicitly **not**
built in this pass — only considered later if there's an actual
business need once Google sync is live and proven.

**Data model**
- `CalendarCredential`: `id`, `provider` (str, `"google"` only for now
  but stored as a string not a hardcoded enum so a second provider
  doesn't need a migration), `access_token`/`refresh_token` (Fernet-
  encrypted via the existing `security.py` helper — same at-rest
  treatment as `SiteSetting.is_secret` rows, not a new crypto path),
  `token_expires_at`, `calendar_id` (the specific Google calendar
  chosen to sync, since an account can have several), `connected_at`,
  `is_active`.

**OAuth flow**
- `admin_calendar_sync.py`: `GET /admin/api/calendar-sync/connect` —
  redirects to Google's OAuth consent screen with `access_type=offline`
  (to get a refresh token); `GET /admin/api/calendar-sync/callback` —
  exchanges the code, stores the encrypted tokens, lists the account's
  calendars so the admin can pick which one to sync
  (`POST /admin/api/calendar-sync/select` with `calendar_id`).
- `POST /admin/api/calendar-sync/disconnect` — revokes locally (deletes
  the `CalendarCredential` row) and best-effort revokes the token with
  Google; a revoke failure on Google's side still completes the local
  disconnect (never leave an admin stuck with a credential they can't
  remove because an external call failed).

**Slot-generation integration**
- `available_slots` gains a busy-time lookup step, only when
  `calendar_sync_enabled` and an active `CalendarCredential` exists:
  fetch busy blocks for the requested date range from the Google
  Free/Busy API, subtract any overlapping slot.
- Busy-time fetch is cached per (date range, request) — not re-fetched
  once per candidate slot — to keep the endpoint's external-call count
  bounded regardless of how many slots a day generates.
- A Google API failure (timeout, revoked token, quota) **fails open by
  configuration, not by default**: the registry gets a
  `booking.calendar_sync_fail_open` bool (default `False`, meaning "if
  we can't confirm real availability, show no slots rather than risk a
  double-booking") — documented as a deliberate safety-over-convenience
  default the admin can flip if they'd rather degrade to
  ignore-external-calendar behavior.

**Event creation on confirm (optional sub-feature, same pass)**
- On `status` transitioning to `confirmed`, optionally create a Google
  Calendar event on the selected calendar (title from
  `Service.name` + attendee name, description from `Appointment.notes`
  + custom-question answers); the created event's Google event id is
  stored so a later cancel/reschedule can update/delete it via
  `BookingReference`-equivalent tracking (`Appointment.
  external_event_id`, nullable).

**Tests**
- Busy-time subtraction correctly removes an overlapping slot and
  leaves adjacent slots untouched.
- Token refresh path exercised with a mocked expired-token response.
- `calendar_sync_fail_open=False` (default) returns zero slots on a
  simulated API failure rather than falling back to "ignore the
  external calendar."
- Disconnect removes the credential even when the mocked revoke call
  to Google fails.

**Definition of done.** With sync disabled, behavior is identical to
Pass 11. With sync enabled and connected, a manually-created event on
the synced Google Calendar provably removes the corresponding slot from
`GET /api/booking/slots` in an integration test against a mocked Google
client (no live Google account required to run the test suite).

---

#### Pass 13 — Admin UI catch-up

**Goal.** Bring the admin dashboard up to date with every backend
capability added in Passes 8–12, mirroring how Pass 7 followed the
earlier backend-only passes once there was a stable API surface to
build against.

**New pages** (`admin/src/pages/`)
- `ServicesPage.jsx` — list with drag-to-reorder (`position`), create/
  edit form (duration, buffers, location type, confirmation toggle,
  payment-required toggle, active toggle), nested custom-question
  editor (add/remove/reorder/required-toggle per question).
- `AvailabilityPage.jsx` — weekly-hours editor (business-wide, plus a
  per-service override view reachable from `ServicesPage`), a simple
  list-style date-override editor (add a closed date or a one-off
  hours change) — explicitly *not* a full month-grid calendar widget in
  this first cut, matching the plan's "list, not full calendar" scope
  from §2.4 Pass 9.
- `WebhooksPage.jsx` — CRUD form, one-time secret reveal on creation
  with a copy-to-clipboard affordance and a clear "this won't be shown
  again" notice, delivery log table with status/timestamp/response
  code, a "send test event" button.
- `CalendarSyncPage.jsx` — connect/disconnect button, connected-account
  display (email + which calendar is selected), calendar picker if the
  account has more than one calendar, fail-open toggle exposed here
  rather than buried in generic settings (it's a booking-safety
  decision, deserves its own visible control).

**Updated pages**
- `AppointmentsPage.jsx` — service column + filter, a distinct visual
  treatment for `pending` rows, inline accept/reject actions (Pass 10),
  a "requested" tab/queue view so pending items aren't lost in the
  general list, custom-question answers shown in the existing detail
  panel.
- `OverviewPage.jsx` — stat card for pending-confirmation count (a
  number an admin needs to see at a glance, same reasoning as the
  existing appointment/lead stat cards).

**Cross-cutting**
- Every new page follows the existing `PageHeader`/`StatCard` component
  conventions already established in Pass 7 rather than introducing new
  UI primitives.
- No new client-side state library — same `AuthContext` + local
  component state pattern as the rest of `admin/`.

**Definition of done.** An admin can fully configure and operate the
calendar module (services, hours, confirmation workflow, webhooks,
calendar sync) without touching the API directly or needing a database
console — the same bar Pass 7 set for appointments/leads.

### 2.5 Explicitly deferred / not planned
Team/round-robin/collective scheduling, multi-tenant `User` accounts,
`UserPlan` billing tiers, TOTP 2FA for a *booker* (as opposed to the
admin 2FA, a separate already-tracked backlog item), **and
video-conferencing integration (Zoom/Daily/any embedded meeting
provider)** all stay out of scope. Video conferencing in particular was
considered and dropped from this plan: `Service.location_type` covers
"this is a remote appointment" without Perennia taking on an OAuth
relationship with a meeting provider or a dependency on that provider's
uptime for its own booking flow to work. If a real business need for
in-app video links appears later, it re-enters as its own scoped pass
with its own requirements document — not retrofitted into this plan.
