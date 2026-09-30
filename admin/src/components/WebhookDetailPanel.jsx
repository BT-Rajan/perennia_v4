import { useEffect, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./WebhookDetailPanel.css";

const EVENT_CHOICES = [
  { value: "booking.confirmed", label: "Booking confirmed" },
  { value: "booking.cancelled", label: "Booking cancelled" },
  { value: "booking.rescheduled", label: "Booking rescheduled" },
  { value: "booking.requested", label: "Booking requested (needs confirmation)" },
  { value: "booking.accepted", label: "Booking request accepted" },
  { value: "booking.declined", label: "Booking request declined" },
];

const EMPTY_FORM = { url: "", events: ["booking.confirmed"], is_active: true };

export default function WebhookDetailPanel({ mode, webhook, onClose, onCreated, onUpdated, onDeleted }) {
  const { handleSessionExpired } = useAuth();
  const [form, setForm] = useState(
    mode === "edit" ? { url: webhook.url, events: webhook.events, is_active: webhook.is_active } : EMPTY_FORM
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [revealedSecret, setRevealedSecret] = useState(null);
  const [deliveries, setDeliveries] = useState(null);
  const [testing, setTesting] = useState(false);

  function toggleEvent(value) {
    setForm((prev) => ({
      ...prev,
      events: prev.events.includes(value) ? prev.events.filter((e) => e !== value) : [...prev.events, value],
    }));
  }

  function handleApiError(e) {
    if (e.status === 401) handleSessionExpired();
    else setError(e.message);
  }

  function loadDeliveries(id) {
    adminApi.listWebhookDeliveries(id).then(setDeliveries).catch(handleApiError);
  }

  useEffect(() => {
    if (mode === "edit") loadDeliveries(webhook.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, webhook?.id]);

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      if (mode === "create") {
        const created = await adminApi.createWebhook(form);
        setRevealedSecret(created.secret);
        // eslint-disable-next-line no-unused-vars
        const { secret: _secret, ...rest } = created;
        onCreated(rest);
      } else {
        const updated = await adminApi.updateWebhook(webhook.id, form);
        onUpdated(updated);
      }
    } catch (e) {
      handleApiError(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleRegenerateSecret() {
    if (!confirm("Regenerate the signing secret? Any endpoint verifying the old signature will need updating.")) return;
    try {
      const { secret } = await adminApi.regenerateWebhookSecret(webhook.id);
      setRevealedSecret(secret);
    } catch (e) {
      handleApiError(e);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete this webhook? It will stop receiving events immediately.`)) return;
    try {
      await adminApi.deleteWebhook(webhook.id);
      onDeleted(webhook.id);
    } catch (e) {
      handleApiError(e);
    }
  }

  async function handleTest() {
    setTesting(true);
    setError("");
    try {
      await adminApi.testWebhook(webhook.id);
      loadDeliveries(webhook.id);
    } catch (e) {
      handleApiError(e);
    } finally {
      setTesting(false);
    }
  }

  return (
    <aside className="card webhook-panel">
      <div className="webhook-panel-head">
        <div className="webhook-panel-title">{mode === "create" ? "New webhook" : "Edit webhook"}</div>
        <button className="webhook-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      {revealedSecret && (
        <div className="webhook-secret-banner">
          <div className="webhook-secret-banner-label">Signing secret — shown once, copy it now</div>
          <code className="webhook-secret-value">{revealedSecret}</code>
        </div>
      )}

      <label className="webhook-panel-label">Endpoint URL</label>
      <input value={form.url} onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
             placeholder="https://your-system.example.com/hooks/perennia" />

      <label className="webhook-panel-label">Events</label>
      <div className="webhook-events-list">
        {EVENT_CHOICES.map((opt) => (
          <label key={opt.value} className="webhook-panel-check">
            <input type="checkbox" checked={form.events.includes(opt.value)} onChange={() => toggleEvent(opt.value)} />
            {opt.label}
          </label>
        ))}
      </div>

      <label className="webhook-panel-check">
        <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
        Active
      </label>

      {error && <div className="webhook-panel-error">{error}</div>}

      <button className="webhook-panel-save" onClick={handleSave} disabled={saving || !form.url.trim() || form.events.length === 0}>
        {saving ? "Saving…" : mode === "create" ? "Create webhook" : "Save changes"}
      </button>

      {mode === "edit" && (
        <>
          <div className="webhook-panel-actions">
            <button className="row-action" onClick={handleTest} disabled={testing}>
              {testing ? "Sending…" : "Send test event"}
            </button>
            <button className="row-action" onClick={handleRegenerateSecret}>Regenerate secret</button>
            <button className="row-action danger" onClick={handleDelete}>Delete</button>
          </div>

          <label className="webhook-panel-label">Recent deliveries</label>
          {deliveries === null && <div className="table-subtext">Loading…</div>}
          {deliveries?.length === 0 && <div className="table-subtext">No deliveries yet.</div>}
          <div className="webhook-deliveries-list">
            {deliveries?.map((d) => (
              <div key={d.id} className="webhook-delivery-row">
                <span className="mono-chip">{d.event}</span>
                <span className={d.response_status && d.response_status < 300 ? "webhook-delivery-ok" : "webhook-delivery-fail"}>
                  {d.response_status ?? "no response"}
                </span>
                <span className="table-subtext">{d.duration_ms}ms</span>
                <span className="table-subtext">{new Date(d.attempted_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  );
}
