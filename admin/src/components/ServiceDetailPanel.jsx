import { useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./ServiceDetailPanel.css";

const LOCATION_TYPES = [
  { value: "in_person", label: "In person" },
  { value: "phone", label: "Phone" },
  { value: "link_provided", label: "Link provided separately" },
];

const QUESTION_KINDS = ["text", "textarea", "number", "bool", "phone"];

const EMPTY_FORM = {
  name: "", slug: "", duration_minutes: 30, buffer_before_minutes: 0, buffer_after_minutes: 0,
  location_type: "in_person", requires_confirmation: false, payment_required: false, is_active: true,
};

function serviceToForm(service) {
  return {
    name: service.name, slug: service.slug, duration_minutes: service.duration_minutes,
    buffer_before_minutes: service.buffer_before_minutes, buffer_after_minutes: service.buffer_after_minutes,
    location_type: service.location_type, requires_confirmation: service.requires_confirmation,
    payment_required: service.payment_required, is_active: service.is_active,
  };
}

export default function ServiceDetailPanel({ mode, service, onClose, onCreated, onUpdated, onDeactivated }) {
  const { handleSessionExpired } = useAuth();
  const [form, setForm] = useState(mode === "edit" ? serviceToForm(service) : EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleApiError(e) {
    if (e.status === 401) handleSessionExpired();
    else setError(e.message);
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      if (mode === "create") {
        const created = await adminApi.createService(form);
        onCreated(created);
      } else {
        const updated = await adminApi.updateService(service.id, form);
        onUpdated(updated);
      }
    } catch (e) {
      handleApiError(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate() {
    if (!confirm(`Deactivate "${service.name}"? It will stop appearing as bookable — this can be reversed.`)) return;
    try {
      const updated = await adminApi.deleteService(service.id);
      onDeactivated(updated ?? { ...service, is_active: false });
    } catch (e) {
      handleApiError(e);
    }
  }

  return (
    <aside className="card service-panel">
      <div className="service-panel-head">
        <div className="service-panel-title">{mode === "create" ? "New service" : service.name}</div>
        <button className="service-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      <label className="service-panel-label">Name</label>
      <input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Initial Consultation" />

      <label className="service-panel-label">Slug (optional — auto-generated from name)</label>
      <input value={form.slug} onChange={(e) => set("slug", e.target.value)} placeholder="auto" />

      <div className="service-panel-row-2">
        <div>
          <label className="service-panel-label">Duration (minutes)</label>
          <input type="number" min={5} max={480} value={form.duration_minutes}
                 onChange={(e) => set("duration_minutes", Number(e.target.value))} />
        </div>
        <div>
          <label className="service-panel-label">Location</label>
          <select value={form.location_type} onChange={(e) => set("location_type", e.target.value)}>
            {LOCATION_TYPES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
        </div>
      </div>

      <div className="service-panel-row-2">
        <div>
          <label className="service-panel-label">Buffer before (min)</label>
          <input type="number" min={0} max={120} value={form.buffer_before_minutes}
                 onChange={(e) => set("buffer_before_minutes", Number(e.target.value))} />
        </div>
        <div>
          <label className="service-panel-label">Buffer after (min)</label>
          <input type="number" min={0} max={120} value={form.buffer_after_minutes}
                 onChange={(e) => set("buffer_after_minutes", Number(e.target.value))} />
        </div>
      </div>

      <label className="service-panel-check">
        <input type="checkbox" checked={form.requires_confirmation}
               onChange={(e) => set("requires_confirmation", e.target.checked)} />
        Requires admin confirmation before it's booked
      </label>
      <label className="service-panel-check">
        <input type="checkbox" checked={form.payment_required}
               onChange={(e) => set("payment_required", e.target.checked)} />
        Payment required (not yet enforced — reserved for a later pass)
      </label>
      <label className="service-panel-check">
        <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} />
        Active (visible as bookable)
      </label>

      {error && <div className="service-panel-error">{error}</div>}

      <button className="service-panel-save" onClick={handleSave} disabled={saving || !form.name.trim()}>
        {saving ? "Saving…" : mode === "create" ? "Create service" : "Save changes"}
      </button>

      {mode === "edit" && (
        <>
          <QuestionsEditor service={service} onSessionExpired={handleSessionExpired} onChanged={onUpdated} />
          {service.is_active && (
            <button className="service-panel-delete" onClick={handleDeactivate}>Deactivate service</button>
          )}
        </>
      )}
    </aside>
  );
}

function QuestionsEditor({ service, onSessionExpired, onChanged }) {
  const [adding, setAdding] = useState(false);
  const [newLabel, setNewLabel] = useState("");
  const [newKind, setNewKind] = useState("text");
  const [newRequired, setNewRequired] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    const fresh = await adminApi.getService(service.id);
    onChanged(fresh);
  }

  function handleApiError(e) {
    if (e.status === 401) onSessionExpired();
    else setError(e.message);
  }

  async function handleAdd() {
    if (!newLabel.trim()) return;
    try {
      await adminApi.addServiceQuestion(service.id, {
        kind: newKind, label: newLabel.trim(), required: newRequired, position: service.questions.length,
      });
      setNewLabel(""); setNewKind("text"); setNewRequired(false); setAdding(false);
      await refresh();
    } catch (e) {
      handleApiError(e);
    }
  }

  async function handleDelete(questionId) {
    try {
      await adminApi.deleteServiceQuestion(service.id, questionId);
      await refresh();
    } catch (e) {
      handleApiError(e);
    }
  }

  async function handleToggleRequired(question) {
    try {
      await adminApi.updateServiceQuestion(service.id, question.id, { required: !question.required });
      await refresh();
    } catch (e) {
      handleApiError(e);
    }
  }

  async function handleMove(index, direction) {
    const ids = service.questions.map((q) => q.id);
    const target = index + direction;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    try {
      await adminApi.reorderServiceQuestions(service.id, ids);
      await refresh();
    } catch (e) {
      handleApiError(e);
    }
  }

  return (
    <>
      <label className="service-panel-label">Booking questions</label>
      {error && <div className="service-panel-error">{error}</div>}

      {service.questions.length === 0 && !adding && (
        <div className="table-subtext" style={{ marginBottom: 8 }}>No custom questions yet.</div>
      )}

      <div className="question-list">
        {service.questions.map((q, i) => (
          <div className="question-row" key={q.id}>
            <div className="question-row-main">
              <span className="mono-chip">{q.kind}</span>
              <span>{q.label}</span>
              {q.required && <span className="status-pill contacted">required</span>}
            </div>
            <div className="question-row-actions">
              <button className="row-action" onClick={() => handleMove(i, -1)} disabled={i === 0} aria-label="Move up">↑</button>
              <button className="row-action" onClick={() => handleMove(i, 1)} disabled={i === service.questions.length - 1} aria-label="Move down">↓</button>
              <button className="row-action" onClick={() => handleToggleRequired(q)}>
                {q.required ? "Make optional" : "Make required"}
              </button>
              <button className="row-action danger" onClick={() => handleDelete(q.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>

      {adding ? (
        <div className="question-add-form">
          <input placeholder="Question label" value={newLabel} onChange={(e) => setNewLabel(e.target.value)} />
          <select value={newKind} onChange={(e) => setNewKind(e.target.value)}>
            {QUESTION_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
          <label className="service-panel-check">
            <input type="checkbox" checked={newRequired} onChange={(e) => setNewRequired(e.target.checked)} />
            Required
          </label>
          <div className="question-add-actions">
            <button className="row-action primary" onClick={handleAdd} disabled={!newLabel.trim()}>Add</button>
            <button className="row-action" onClick={() => setAdding(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <button className="row-action" onClick={() => setAdding(true)}>+ Add question</button>
      )}
    </>
  );
}
