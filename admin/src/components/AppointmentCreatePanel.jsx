import { useEffect, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./ServiceDetailPanel.css";

const EMPTY_FORM = {
  date: "", time: "", name: "", email: "", phone: "", service_id: "", service: "", notes: "", lang: "en",
};

export default function AppointmentCreatePanel({ onClose, onCreated }) {
  const { handleSessionExpired } = useAuth();
  const [form, setForm] = useState(EMPTY_FORM);
  const [services, setServices] = useState([]);
  const [slots, setSlots] = useState([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    adminApi.listServices().then((list) => setServices(list.filter((s) => s.is_active))).catch(() => {});
  }, []);

  useEffect(() => {
    if (!form.date) { setSlots([]); return; }
    setSlotsLoading(true);
    adminApi
      .getSlots(form.date, form.service_id || undefined)
      .then((res) => setSlots(res?.slots ?? res ?? []))
      .catch(() => setSlots([]))
      .finally(() => setSlotsLoading(false));
  }, [form.date, form.service_id]);

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const result = await adminApi.createAppointment(form);
      onCreated(result.appointment ?? result);
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
        <div className="service-panel-title">New appointment</div>
        <button className="service-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      <label className="service-panel-label">Service (optional)</label>
      <select value={form.service_id} onChange={(e) => set("service_id", e.target.value)}>
        <option value="">— No service / general enquiry —</option>
        {services.map((s) => (
          <option key={s.id} value={s.id}>{s.name} ({s.duration_minutes} min)</option>
        ))}
      </select>

      {!form.service_id && (
        <>
          <label className="service-panel-label">Description (if no service picked)</label>
          <input value={form.service} onChange={(e) => set("service", e.target.value)} placeholder="e.g. General enquiry" />
        </>
      )}

      <div className="service-panel-row-2">
        <div>
          <label className="service-panel-label">Date</label>
          <input type="date" value={form.date} onChange={(e) => set("date", e.target.value)} />
        </div>
        <div>
          <label className="service-panel-label">Time slot</label>
          <select value={form.time} onChange={(e) => set("time", e.target.value)} disabled={!form.date || slotsLoading}>
            <option value="">{slotsLoading ? "Loading…" : "Select a time"}</option>
            {slots.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>
      {form.date && !slotsLoading && slots.length === 0 && (
        <div className="table-subtext">No open slots on that date.</div>
      )}

      <label className="service-panel-label">Name</label>
      <input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Visitor's full name" />

      <label className="service-panel-label">Email</label>
      <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />

      <label className="service-panel-label">Phone</label>
      <input value={form.phone} onChange={(e) => set("phone", e.target.value)} />

      <label className="service-panel-label">Notes</label>
      <textarea rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} />

      <label className="service-panel-label">Language</label>
      <select value={form.lang} onChange={(e) => set("lang", e.target.value)}>
        <option value="en">English</option>
        <option value="ar">Arabic</option>
      </select>

      {error && <div className="service-panel-error">{error}</div>}

      <button className="service-panel-save" onClick={handleSave} disabled={saving || !form.date || !form.time || !form.name || !form.email}>
        {saving ? "Booking…" : "Create appointment"}
      </button>
    </aside>
  );
}
