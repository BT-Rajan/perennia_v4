import { useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./LeadDetailPanel.css";

const STATUSES = ["new", "contacted", "qualified", "converted", "lost"];

export default function LeadDetailPanel({ lead, onClose, onUpdated, onDeleted }) {
  const { handleSessionExpired } = useAuth();
  const [notes, setNotes] = useState(lead.notes);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleStatusChange(status) {
    try {
      const updated = await adminApi.updateLead(lead.id, { status });
      onUpdated(updated);
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setError(e.message);
    }
  }

  async function handleSaveNotes() {
    setSaving(true);
    setError("");
    try {
      const updated = await adminApi.updateLead(lead.id, { notes });
      onUpdated(updated);
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete the lead record for ${lead.email}? This can't be undone.`)) return;
    try {
      await adminApi.deleteLead(lead.id);
      onDeleted(lead.id);
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setError(e.message);
    }
  }

  return (
    <aside className="card lead-panel">
      <div className="lead-panel-head">
        <div>
          <div className="lead-panel-name">{lead.name || "No name given"}</div>
          <div className="lead-panel-email">{lead.email}</div>
        </div>
        <button className="lead-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      {lead.phone && <div className="lead-panel-row"><span>Phone</span>{lead.phone}</div>}
      <div className="lead-panel-row"><span>Source</span>{lead.source}</div>
      <div className="lead-panel-row"><span>Captured</span>{new Date(lead.created_at).toLocaleString()}</div>

      <label className="lead-panel-label">Status</label>
      <select value={lead.status} onChange={(e) => handleStatusChange(e.target.value)}>
        {STATUSES.map((s) => (
          <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>
        ))}
      </select>

      <label className="lead-panel-label">Notes</label>
      <textarea rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Internal notes…" />
      <button className="lead-panel-save" onClick={handleSaveNotes} disabled={saving || notes === lead.notes}>
        {saving ? "Saving…" : "Save notes"}
      </button>

      {error && <div className="lead-panel-error">{error}</div>}

      {lead.transcript.length > 0 && (
        <>
          <label className="lead-panel-label">Transcript</label>
          <div className="lead-transcript">
            {lead.transcript.map((entry, i) => (
              <div key={i} className="lead-transcript-entry">
                <div className="lead-transcript-meta">
                  {entry.from} · {new Date(entry.at).toLocaleString()}
                </div>
                <div>{entry.text}</div>
              </div>
            ))}
          </div>
        </>
      )}

      <button className="lead-panel-delete" onClick={handleDelete}>Delete lead</button>
    </aside>
  );
}
