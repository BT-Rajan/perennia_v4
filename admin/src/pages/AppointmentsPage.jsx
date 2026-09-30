import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import AppointmentCreatePanel from "../components/AppointmentCreatePanel.jsx";
import AppointmentDetailPanel from "../components/AppointmentDetailPanel.jsx";
import "./AppointmentsPage.css";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "confirmed", label: "Confirmed" },
  { value: "pending", label: "Pending confirmation" },
  { value: "cancelled", label: "Cancelled" },
];

export default function AppointmentsPage() {
  const { handleSessionExpired } = useAuth();
  const navigate = useNavigate();
  const { id: selectedId } = useParams();
  const [appointments, setAppointments] = useState(null);
  const [statusFilter, setStatusFilter] = useState("confirmed");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    adminApi
      .listAppointments({ status_filter: statusFilter, date_from: dateFrom, date_to: dateTo })
      .then(setAppointments)
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [statusFilter, dateFrom, dateTo, handleSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCancel(id) {
    if (!confirm(`Cancel appointment ${id}? The visitor's cancellation email will still go out if notifications are enabled.`)) return;
    setBusyId(id);
    try {
      await adminApi.cancelAppointment(id);
      load();
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else alert(e.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleAccept(id) {
    setBusyId(id);
    try {
      await adminApi.acceptAppointment(id);
      load();
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else alert(e.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(id) {
    const reason = prompt("Reason for declining (optional, shown to the visitor):", "");
    if (reason === null) return; // dismissed the prompt — leave the request untouched
    setBusyId(id);
    try {
      await adminApi.rejectAppointment(id, reason);
      load();
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else alert(e.message);
    } finally {
      setBusyId(null);
    }
  }

  function handlePanelUpdated() {
    load();
  }

  const selectedAppointment = appointments?.find((a) => a.id === selectedId) ?? null;

  return (
    <div>
      <PageHeader
        title="Appointments"
        subtitle="Every booking made through the site."
        actions={
          <button className="row-action primary" onClick={() => { setCreating(true); navigate("/appointments"); }}>
            + New appointment
          </button>
        }
      />

      {creating && (
        <AppointmentCreatePanel
          onClose={() => setCreating(false)}
          onCreated={() => { setCreating(false); load(); }}
        />
      )}

      <div className="filters-row">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} title="From date" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} title="To date" />
        {(dateFrom || dateTo) && (
          <button className="clear-filter" onClick={() => { setDateFrom(""); setDateTo(""); }}>Clear dates</button>
        )}
      </div>

      {error && <div className="page-error">{error}</div>}

      <div className="appointments-layout">
        <div className="card appointments-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Contact</th>
                <th>When</th>
                <th>Service</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {appointments === null && (
                <tr><td colSpan={7} className="table-empty">Loading…</td></tr>
              )}
              {appointments?.length === 0 && (
                <tr><td colSpan={7} className="table-empty">No appointments match these filters.</td></tr>
              )}
              {appointments?.map((a) => (
                <tr
                  key={a.id}
                  className={selectedId === a.id ? "row-selected" : ""}
                  onClick={() => { setCreating(false); navigate(`/appointments/${a.id}`); }}
                  style={{ cursor: "pointer" }}
                >
                  <td><span className="mono-chip">{a.id}</span></td>
                  <td>{a.name}</td>
                  <td>
                    <div>{a.email}</div>
                    {a.phone && <div className="table-subtext">{a.phone}</div>}
                  </td>
                  <td>{a.date} · {a.time}</td>
                  <td>
                    {a.service_name || a.service || "—"}
                    {a.answers?.length > 0 && <span className="table-subtext"> · {a.answers.length} answer{a.answers.length > 1 ? "s" : ""}</span>}
                  </td>
                  <td><span className={`status-pill ${a.status}`}>{a.status}</span></td>
                  <td>
                    {a.status === "confirmed" && (
                      <button
                        className="row-action danger"
                        disabled={busyId === a.id}
                        onClick={(e) => { e.stopPropagation(); handleCancel(a.id); }}
                      >
                        {busyId === a.id ? "Cancelling…" : "Cancel"}
                      </button>
                    )}
                    {a.status === "pending" && (
                      <div className="appt-pending-actions">
                        <button
                          className="row-action primary"
                          disabled={busyId === a.id}
                          onClick={(e) => { e.stopPropagation(); handleAccept(a.id); }}
                        >
                          Accept
                        </button>
                        <button
                          className="row-action danger"
                          disabled={busyId === a.id}
                          onClick={(e) => { e.stopPropagation(); handleReject(a.id); }}
                        >
                          Decline
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!creating && selectedAppointment && (
          <AppointmentDetailPanel
            key={selectedAppointment.id}
            appointment={selectedAppointment}
            onClose={() => navigate("/appointments")}
            onUpdated={handlePanelUpdated}
          />
        )}
      </div>
    </div>
  );
}
