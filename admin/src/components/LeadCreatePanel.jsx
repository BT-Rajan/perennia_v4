import { useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./ServiceDetailPanel.css";

const STATUSES = ["new", "contacted", "qualified", "converted", "lost"];

export default function LeadCreatePanel({ onClose, onCreated }) {
  const { handleSessionExpired } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", phone: "", status: "new", notes: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const lead = await adminApi.createLead(form);
      onCreated(lead);
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <aside className="card service-panel">
      <div className="service-panel-head">
        <div className="service-panel-title">New lead</div>
        <button className="service-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      <label className="service-panel-label">Name</label>
      <input value={form.name} onChange={(e) => set("name", e.target.value)} />

      <label className="service-panel-label">Email</label>
      <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />

      <label className="service-panel-label">Phone</label>
      <input value={form.phone} onChange={(e) => set("phone", e.target.value)} />

      <label className="service-panel-label">Status</label>
      <select value={form.status} onChange={(e) => set("status", e.target.value)}>
        {STATUSES.map((s) => (
          <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>
        ))}
      </select>

      <label className="service-panel-label">Notes</label>
      <textarea rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} />

      {error && <div className="service-panel-error">{error}</div>}

      <button className="service-panel-save" onClick={handleSave} disabled={saving || !form.email}>
        {saving ? "Saving…" : "Add lead"}
      </button>
    </aside>
  );
}
