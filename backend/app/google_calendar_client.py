"""
Thin client for Google's OAuth token endpoint and Calendar API.
Mirrors whatsapp_client.py's shape: plain httpx calls, no vendor SDK,
every function takes exactly what it needs as arguments rather than
reaching into settings/DB itself — that's calendar_sync_service.py's
job. Keeping this layer free of any app-specific state is what makes
it trivially mockable in tests (monkeypatch one function at a time,
no client object to construct).
"""
from __future__ import annotations

import datetime as dt

import httpx

AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
EVENTS_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
EVENT_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"

SCOPES = "https://www.googleapis.com/auth/calendar"
REQUEST_TIMEOUT_SECONDS = 15.0


class GoogleCalendarError(Exception):
    """Raised for any failure talking to Google — a timeout, a
    non-2xx response, a malformed reply. Callers (calendar_sync_service.py)
    decide what to do about it (fail-open vs fail-closed for slot
    generation, best-effort-and-swallow for event creation).

    status_code carries the HTTP status when the failure was an actual
    non-2xx response from Google — None for a timeout, connection
    error, or malformed reply, where there wasn't one to carry. Lets a
    caller that needs to tell "the resource is gone" (404) apart from
    "something else went wrong" (a 429, a 500, a timeout) check that
    directly instead of parsing this exception's message string."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SyncTokenExpired(GoogleCalendarError):
    """Google returns HTTP 410 when a stored sync token is no longer
    valid (expired, or the calendar's sync history was reset). Per
    Google's Events.list contract, the caller must discard the token
    and perform a fresh time-bounded listing instead of retrying with
    the same token."""


def build_auth_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    from urllib.parse import urlencode
    params = {
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state,
    }
    return f"{AUTH_BASE_URL}?{urlencode(params)}"


def _post_token(data: dict) -> dict:
    try:
        resp = httpx.post(TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise GoogleCalendarError(f"Token endpoint returned {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise GoogleCalendarError(f"Token endpoint request failed: {e}") from e


def exchange_code(*, client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    """Returns {access_token, refresh_token, expires_in, ...} — Google
    only returns refresh_token on the *first* consent for a given
    account+scope, which is exactly why access_type=offline and
    prompt=consent are both set on the auth URL above."""
    return _post_token({
        "client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri,
        "code": code, "grant_type": "authorization_code",
    })


def refresh_access_token(*, client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Returns {access_token, expires_in, ...} — no new refresh_token
    is issued by this flow; the original one keeps working until
    revoked."""
    return _post_token({
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token",
    })


def revoke_token(token: str) -> bool:
    """Best-effort: returns False rather than raising on failure,
    since callers (calendar_sync_service.disconnect) must complete a
    local disconnect regardless of whether Google's side succeeds."""
    try:
        resp = httpx.post(REVOKE_URL, params={"token": token}, timeout=REQUEST_TIMEOUT_SECONDS)
        return resp.status_code < 300
    except httpx.HTTPError:
        return False


def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def list_calendars(access_token: str) -> list[dict]:
    """Returns [{id, summary, primary}, ...]."""
    try:
        resp = httpx.get(CALENDAR_LIST_URL, headers=_auth_headers(access_token), timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except httpx.HTTPStatusError as e:
        raise GoogleCalendarError(f"Calendar list request returned {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise GoogleCalendarError(f"Calendar list request failed: {e}") from e
    return [{"id": c["id"], "summary": c.get("summary", c["id"]), "primary": c.get("primary", False)} for c in items]


def get_busy_times(access_token: str, *, calendar_id: str, time_min: dt.datetime, time_max: dt.datetime) -> list[tuple[str, str]]:
    """Returns [(start_iso, end_iso), ...] busy blocks on `calendar_id`
    within [time_min, time_max). One request regardless of how many
    candidate slots the caller will check against the result — see
    calendar_sync_service.busy_minutes_for_date, which calls this once
    per (date, calendar) rather than once per slot."""
    body = {
        "timeMin": time_min.isoformat(), "timeMax": time_max.isoformat(),
        "items": [{"id": calendar_id}],
    }
    try:
        resp = httpx.post(FREEBUSY_URL, headers=_auth_headers(access_token), json=body, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        raise GoogleCalendarError(f"Free/busy request returned {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise GoogleCalendarError(f"Free/busy request failed: {e}") from e

    calendars = data.get("calendars", {})
    entry = calendars.get(calendar_id, {})
    if entry.get("errors"):
        raise GoogleCalendarError(f"Free/busy API reported an error for {calendar_id!r}: {entry['errors']}")
    return [(b["start"], b["end"]) for b in entry.get("busy", [])]


def create_event(access_token: str, *, calendar_id: str, summary: str, description: str,
                  start_iso: str, end_iso: str, timezone: str) -> str:
    """Returns the created event's Google event id."""
    body = {
        "summary": summary, "description": description,
        "start": {"dateTime": start_iso, "timeZone": timezone},
        "end": {"dateTime": end_iso, "timeZone": timezone},
    }
    try:
        resp = httpx.post(
            EVENTS_URL_TEMPLATE.format(calendar_id=calendar_id),
            headers=_auth_headers(access_token), json=body, timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()["id"]
    except httpx.HTTPStatusError as e:
        raise GoogleCalendarError(f"Event creation returned {e.response.status_code}",
                                   status_code=e.response.status_code) from e
    except httpx.HTTPError as e:
        raise GoogleCalendarError(f"Event creation request failed: {e}") from e


def update_event(access_token: str, *, calendar_id: str, event_id: str, summary: str, description: str,
                  start_iso: str, end_iso: str, timezone: str) -> str:
    """PATCHes an existing event in place and returns its (unchanged)
    id. Used for reschedules and admin edits so the event keeps its
    Google-assigned identity and anything attached to it there
    (attendees, color, other manual edits) instead of the old
    delete-then-recreate approach, which threw all of that away on
    every reschedule."""
    body = {
        "summary": summary, "description": description,
        "start": {"dateTime": start_iso, "timeZone": timezone},
        "end": {"dateTime": end_iso, "timeZone": timezone},
    }
    try:
        resp = httpx.patch(
            EVENT_URL_TEMPLATE.format(calendar_id=calendar_id, event_id=event_id),
            headers=_auth_headers(access_token), json=body, timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()["id"]
    except httpx.HTTPStatusError as e:
        raise GoogleCalendarError(f"Event update returned {e.response.status_code}",
                                   status_code=e.response.status_code) from e
    except httpx.HTTPError as e:
        raise GoogleCalendarError(f"Event update request failed: {e}") from e


def list_events_page(access_token: str, *, calendar_id: str, time_min: str | None = None,
                      time_max: str | None = None, sync_token: str | None = None,
                      page_token: str | None = None) -> dict:
    """One page of Events.list. Exactly one of (time_min/time_max) or
    sync_token drives the request — Google rejects a sync_token request
    that also carries time_min/time_max/q. showDeleted=true is required
    for sync_token requests to surface cancellations, and harmless to
    always send otherwise. Raises SyncTokenExpired on a 410 rather than
    the generic GoogleCalendarError, so callers can tell 'the token is
    stale, do a full resync' apart from 'something else went wrong'."""
    params: dict[str, str | int] = {"singleEvents": "true", "showDeleted": "true", "maxResults": 250}
    if page_token:
        params["pageToken"] = page_token
    if sync_token:
        params["syncToken"] = sync_token
    else:
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        params["orderBy"] = "startTime"
    try:
        resp = httpx.get(
            EVENTS_URL_TEMPLATE.format(calendar_id=calendar_id),
            headers=_auth_headers(access_token), params=params, timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if resp.status_code == 410:
            raise SyncTokenExpired("Sync token expired or invalid; a full resync is required", status_code=410)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise GoogleCalendarError(f"Event list request returned {e.response.status_code}",
                                   status_code=e.response.status_code) from e
    except httpx.HTTPError as e:
        raise GoogleCalendarError(f"Event list request failed: {e}") from e


def list_all_events(access_token: str, *, calendar_id: str, time_min: str | None = None,
                     time_max: str | None = None, sync_token: str | None = None) -> tuple[list[dict], str | None]:
    """Pages through every page of one Events.list call. Returns
    (all items across pages, the final nextSyncToken if Google sent
    one — only present once the last page is reached)."""
    items: list[dict] = []
    page_token: str | None = None
    next_sync_token: str | None = None
    while True:
        page = list_events_page(
            access_token, calendar_id=calendar_id, time_min=time_min, time_max=time_max,
            sync_token=sync_token, page_token=page_token,
        )
        items.extend(page.get("items", []))
        next_sync_token = page.get("nextSyncToken", next_sync_token)
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    return items, next_sync_token


def delete_event(access_token: str, *, calendar_id: str, event_id: str) -> None:
    try:
        resp = httpx.delete(
            EVENT_URL_TEMPLATE.format(calendar_id=calendar_id, event_id=event_id),
            headers=_auth_headers(access_token), timeout=REQUEST_TIMEOUT_SECONDS,
        )
        # 404/410 mean the event is already gone on Google's side -
        # exactly the outcome we wanted, not a failure to report.
        if resp.status_code not in (204, 404, 410) and resp.status_code >= 300:
            raise GoogleCalendarError(f"Event deletion returned {resp.status_code}", status_code=resp.status_code)
    except httpx.HTTPError as e:
        raise GoogleCalendarError(f"Event deletion request failed: {e}") from e
