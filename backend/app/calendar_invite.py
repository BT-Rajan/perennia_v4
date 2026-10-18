"""
Builds the .ics calendar invite attached to booking emails, so the
visitor (and the internal alert recipient) get the meeting in whatever
calendar they use — Gmail, Outlook, Apple — without this site needing
access to anyone's calendar.

One UID per appointment, so a reschedule updates the existing entry
and a cancellation removes it instead of adding a second one. SEQUENCE
is the send time in seconds: always increasing, so the newest email
wins no matter how many changes came before it. Times are written in
UTC, which every client converts to its own local zone — no VTIMEZONE
block to get wrong.
"""
from __future__ import annotations

import datetime as dt
import time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Service
from app.settings_service import get_setting

REQUEST = "REQUEST"  # new or changed meeting
CANCEL = "CANCEL"    # removes the meeting from the calendar


def _escape(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545: lines longer than 75 octets continue on the next line
    after a single leading space."""
    data = line.encode("utf-8")
    if len(data) <= 75:
        return line
    parts, chunk = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(chunk) + len(b) > (75 if not parts else 74):
            parts.append(chunk.decode("utf-8"))
            chunk = b""
        chunk += b
    parts.append(chunk.decode("utf-8"))
    return "\r\n ".join(parts)


def _utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _duration_minutes(db: Session, appt: dict) -> int:
    if appt.get("service_id"):
        svc = db.get(Service, appt["service_id"])
        if svc is not None and svc.duration_minutes:
            return svc.duration_minutes
    return get_setting(db, "booking.slot_minutes") or 30


def build_invite(db: Session, appt: dict, *, method: str = REQUEST) -> str:
    """appt is booking_service._serialize()'s dict."""
    tz = ZoneInfo(appt.get("timezone") or get_setting(db, "booking.timezone") or "UTC")
    start = dt.datetime.strptime(f"{appt['date']} {appt['time']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    end = start + dt.timedelta(minutes=_duration_minutes(db, appt))

    site_name = get_setting(db, "branding.site_name")
    if isinstance(site_name, dict):
        site_name = site_name.get("en") or next(iter(site_name.values()), "")
    site_name = site_name or "Appointment"
    service = appt.get("service_name") or appt.get("service") or ""
    summary = f"{service} — {site_name}" if service else f"Meeting with {site_name}"

    organizer_email = get_setting(db, "notifications.from_email") or ""
    organizer_name = get_setting(db, "notifications.from_name") or site_name
    address = get_setting(db, "contact.address")
    if isinstance(address, dict):
        address = address.get(appt.get("lang") or "en") or address.get("en") or ""
    description = f"Confirmation code: {appt['id']}"
    if appt.get("notes"):
        description += f"\n\n{appt['notes']}"

    cancelled = method == CANCEL
    domain = organizer_email.rpartition("@")[2] or "localhost"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{_escape(site_name)}//Booking//EN",
        "CALSCALE:GREGORIAN",
        f"METHOD:{method}",
        "BEGIN:VEVENT",
        f"UID:appointment-{appt['id']}@{domain}",
        f"SEQUENCE:{int(time.time())}",
        f"DTSTAMP:{_utc(dt.datetime.now(dt.timezone.utc))}",
        f"DTSTART:{_utc(start)}",
        f"DTEND:{_utc(end)}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
    ]
    if address:
        lines.append(f"LOCATION:{_escape(address)}")
    if organizer_email:
        lines.append(f"ORGANIZER;CN={_escape(organizer_name)}:mailto:{organizer_email}")
    lines += [
        f"ATTENDEE;CN={_escape(appt.get('name', ''))};ROLE=REQ-PARTICIPANT;"
        f"PARTSTAT={'DECLINED' if cancelled else 'ACCEPTED'};RSVP=FALSE:mailto:{appt['email']}",
        f"STATUS:{'CANCELLED' if cancelled else 'CONFIRMED'}",
        "TRANSP:OPAQUE",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
