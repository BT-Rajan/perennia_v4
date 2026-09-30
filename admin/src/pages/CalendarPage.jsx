import { useCallback, useEffect, useMemo, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import "./CalendarPage.css";

function toLocalInputValue(iso) {
  if (!iso) return "";
  // datetime-local inputs want "YYYY-MM-DDTHH:mm" with no timezone suffix.
  return iso.slice(0, 16);
}

function startOfWeek(d) {
  const date = new Date(d);
  const day = date.getDay();
  date.setDate(date.getDate() - day);
  return date;
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

const EMPTY_FORM = { summary: "", description: "", start: "", end: "" };

// A general "manage anything on the connected calendar" screen —
// separate from Appointments, which only shows bookings this app
// created. This is the "full calendar controls" surface: create, edit,
// or delete any event on the account's calendar, whether or not it's
// tied to a booking.
export default function CalendarPage() {
  const { handleSessionExpired } = useAuth();
  const [connected, setConnected] = useState(null);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [events, setEvents] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState(null); // null = not editing, "new" = creating
  const [form, setForm] = useState(EMPTY_FORM);

  const rangeEnd = useMemo(() => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 6);
    return d;
  }, [weekStart]);

  function handleApiError(e) {
    if (e.status === 401) handleSessionExpired();
    else setError(e.message);
  }

  const load = useCallback(() => {
    adminApi
      .getCalendarSyncStatus()
      .then((status) => {
        setConnected(status.connected);
        if (!status.connected) {
          setEvents([]);
          return null;
        }
        return adminApi.listCalendarEvents(isoDate(weekStart), isoDate(rangeEnd)).then(setEvents);
      })
      .catch(handleApiError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weekStart]);

  useEffect(() => {
    load();
  }, [load]);

  function openCreate() {
    const base = new Date(weekStart);
    base.setHours(9, 0, 0, 0);
    const end = new Date(base);
    end.setHours(10, 0, 0, 0);
    setForm({
      summary: "", description: "",
      start: toLocalInputValue(base.toISOString()),
      end: toLocalInputValue(end.toISOString()),
    });
    setEditingId("new");
    setError("");
  }

  function openEdit(ev) {
    setForm({
      summary: ev.summary === "(no title)" ? "" : ev.summary,
      description: ev.description || "",
      start: toLocalInputValue(ev.start),
      end: toLocalInputValue(ev.end),
    });
    setEditingId(ev.id);
    setError("");
  }

  async function handleSave() {
    if (!form.summary.trim() || !form.start || !form.end) {
      setError("Title, start, and end are required.");
      return;
    }
    setBusy(true);
    setError("");
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const body = { summary: form.summary, description: form.description, start: form.start, end: form.end, timezone };
    try {
      if (editingId === "new") {
        await adminApi.createCalendarEvent(body);
      } else {
        await adminApi.updateCalendarEvent(editingId, body);
      }
      setEditingId(null);
      setForm(EMPTY_FORM);
      load();
    } catch (e) {
      handleApiError(e);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this event from Google Calendar? This can't be undone.")) return;
    setBusy(true);
    setError("");
    try {
      await adminApi.deleteCalendarEvent(id);
      if (editingId === id) setEditingId(null);
      load();
    } catch (e) {
      handleApiError(e);
    } finally {
      setBusy(false);
    }
  }

  function shiftWeek(delta) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + delta * 7);
    setWeekStart(d);
  }

  return (
    <div>
      <PageHeader
        title="Calendar"
        subtitle="Full control over the connected Google Calendar — create, edit, or delete any event, not just bookings."
        actions={
          connected ? (
            <button className="row-action primary" onClick={openCreate}>+ New event</button>
          ) : null
        }
      />

      {error && <div className="page-error">{error}</div>}

      {connected === false && (
        <div className="card calendar-page-empty">
          No Google Calendar is connected yet. Connect one under Settings → Calendar Sync to manage
          events from here.
        </div>
      )}

      {connected && (
        <div className="calendar-page-layout">
          <div className="card calendar-page-events">
            <div className="calendar-page-week-nav">
              <button className="row-action" onClick={() => shiftWeek(-1)}>← Prev week</button>
              <span>{isoDate(weekStart)} – {isoDate(rangeEnd)}</span>
              <button className="row-action" onClick={() => shiftWeek(1)}>Next week →</button>
            </div>

            <table>
              <thead>
                <tr><th>When</th><th>Title</th><th></th></tr>
              </thead>
              <tbody>
                {events === null && <tr><td colSpan={3} className="table-empty">Loading…</td></tr>}
                {events?.length === 0 && <tr><td colSpan={3} className="table-empty">No events this week.</td></tr>}
                {events?.map((ev) => (
                  <tr key={ev.id} className={editingId === ev.id ? "row-selected" : ""}>
                    <td>{ev.all_day ? ev.start : new Date(ev.start).toLocaleString()}</td>
                    <td>{ev.summary}</td>
                    <td className="calendar-page-row-actions">
                      <button className="row-action" onClick={() => openEdit(ev)} disabled={ev.all_day}>Edit</button>
                      <button className="row-action danger" onClick={() => handleDelete(ev.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {editingId && (
            <aside className="card calendar-page-form">
              <div className="calendar-page-form-head">
                <span>{editingId === "new" ? "New event" : "Edit event"}</span>
                <button className="appt-panel-close" onClick={() => setEditingId(null)} aria-label="Close">×</button>
              </div>
              <label className="setting-label">Title</label>
              <input className="setting-input" value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
              <label className="setting-label">Description</label>
              <textarea className="setting-input" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              <label className="setting-label">Start</label>
              <input type="datetime-local" className="setting-input" value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} />
              <label className="setting-label">End</label>
              <input type="datetime-local" className="setting-input" value={form.end} onChange={(e) => setForm({ ...form, end: e.target.value })} />
              <div className="calendar-page-form-actions">
                <button className="row-action primary" disabled={busy} onClick={handleSave}>
                  {busy ? "Saving…" : "Save"}
                </button>
                <button className="row-action" disabled={busy} onClick={() => setEditingId(null)}>Cancel</button>
              </div>
            </aside>
          )}
        </div>
      )}
    </div>
  );
}
