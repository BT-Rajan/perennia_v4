import { useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./AppointmentDetailPanel.css";

export default function AppointmentDetailPanel({ appointment, onClose, onUpdated }) {
  const { handleSessionExpired } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [rescheduling, setRescheduling] = useState(false);
  const [newDate, setNewDate] = useState(appointment.date);
  const [newTime, setNewTime] = useState(appointment.time);

  function handleApiError(e) {
    if (e.status === 401) handleSessionExpired();
    else setError(e.message);
  }

  async function handleCancel() {
    if (!confirm(`Cancel appointment ${appointment.id}? The visitor's cancellation email will still go out if notifications are enabled.`)) return;
    setBusy(true);
    setError("");
    try {
      const updated = await adminApi.cancelAppointment(appointment.id);
      onUpdated(updated);
    } catch (e) {
      handleApiError(e);
    } finally {
      setBusy(false);
    }
  }

  async function handleAccept() {
    setBusy(true);
    setError("");
    try {
      const updated = await adminApi.acceptAppointment(appointment.id);
      onUpdated(updated);
    } catch (e) {
      handleApiError(e);
    } finally {
      setBusy(false);
    }
  }

  async function handleReject() {
    const reason = prompt("Reason for declining (optional, shown to the visitor):", "");
    if (reason === null) return;
    setBusy(true);
    setError("");
    try {
      const updated = await adminApi.rejectAppointment(appointment.id, reason);
      onUpdated(updated);
    } catch (e) {
      handleApiError(e);
    } finally {
      setBusy(false);
    }
  }

  async function handleReschedule() {
    setBusy(true);
    setError("");
    try {
      const updated = await adminApi.rescheduleAppointment(appointment.id, newDate, newTime);
      onUpdated(updated);
      setRescheduling(false);
    } catch (e) {
      handleApiError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="card appt-panel">
      <div className="appt-panel-head">
        <div>
          <div className="appt-panel-name">{appointment.name}</div>
          <div className="appt-panel-code">{appointment.id}</div>
        </div>
        <button className="appt-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      <div className="appt-panel-row"><span>Status</span><span className={`status-pill ${appointment.status}`}>{appointment.status}</span></div>
      <div className="appt-panel-row"><span>Email</span>{appointment.email}</div>
      {appointment.phone && <div className="appt-panel-row"><span>Phone</span>{appointment.phone}</div>}
      <div className="appt-panel-row"><span>When</span>{appointment.date} · {appointment.time}</div>
      <div className="appt-panel-row"><span>Service</span>{appointment.service_name || appointment.service || "—"}</div>

      {appointment.calendar_drift && (
        <div className="appt-panel-drift">
          ⚠ Google Calendar mismatch: {appointment.calendar_drift} Rescheduling or editing here will push this
          appointment's time back to Google and clear this warning.
        </div>
      )}

      {rescheduling && appointment.status !== "cancelled" && (
        <div className="appt-panel-reschedule">
          <label className="appt-panel-label">New date</label>
          <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
          <label className="appt-panel-label">New time</label>
          <input type="time" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
          <div className="appt-panel-reschedule-actions">
            <button className="row-action primary" disabled={busy} onClick={handleReschedule}>
              {busy ? "Saving…" : "Save new time"}
            </button>
            <button className="row-action" disabled={busy} onClick={() => setRescheduling(false)}>Cancel</button>
          </div>
        </div>
      )}

      {appointment.answers?.length > 0 && (
        <>
          <label className="appt-panel-label">Intake answers</label>
          <div className="appt-answers-list">
            {appointment.answers.map((ans) => (
              <div key={ans.question_id ?? ans.label} className="appt-answer-item">
                <span className="appt-answer-label">{ans.label}</span>
                <span>{ans.answer}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {error && <div className="appt-panel-error">{error}</div>}

      <div className="appt-panel-actions">
        {(appointment.status === "confirmed" || appointment.status === "pending") && !rescheduling && (
          <button className="row-action" disabled={busy} onClick={() => setRescheduling(true)}>
            Reschedule
          </button>
        )}
        {appointment.status === "confirmed" && (
          <button className="row-action danger" disabled={busy} onClick={handleCancel}>
            {busy ? "Cancelling…" : "Cancel appointment"}
          </button>
        )}
        {appointment.status === "pending" && (
          <>
            <button className="row-action primary" disabled={busy} onClick={handleAccept}>
              {busy ? "Working…" : "Accept"}
            </button>
            <button className="row-action danger" disabled={busy} onClick={handleReject}>
              {busy ? "Working…" : "Decline"}
            </button>
          </>
        )}
      </div>
    </aside>
  );
}
