import { useCallback, useEffect, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import WebhookDetailPanel from "../components/WebhookDetailPanel.jsx";
import "./WebhooksPage.css";

export default function WebhooksPage() {
  const { handleSessionExpired } = useAuth();
  const [webhooks, setWebhooks] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    adminApi
      .listWebhooks()
      .then(setWebhooks)
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [handleSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated(webhook) {
    setWebhooks((prev) => [...(prev ?? []), webhook]);
    setCreating(false);
    setSelectedId(webhook.id);
  }

  function handleUpdated(updated) {
    setWebhooks((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
  }

  function handleDeleted(id) {
    setWebhooks((prev) => prev.filter((w) => w.id !== id));
    setSelectedId(null);
  }

  const selectedWebhook = webhooks?.find((w) => w.id === selectedId) ?? null;

  return (
    <div>
      <PageHeader
        title="Webhooks"
        subtitle="Send calendar events to your own systems — a CRM, a spreadsheet automation, Slack — without polling."
        actions={
          <button className="row-action primary" onClick={() => { setCreating(true); setSelectedId(null); }}>
            + New webhook
          </button>
        }
      />

      {error && <div className="page-error">{error}</div>}

      <div className="webhooks-layout">
        <div className="card webhooks-table-wrap">
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Events</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {webhooks === null && (
                <tr><td colSpan={3} className="table-empty">Loading…</td></tr>
              )}
              {webhooks?.length === 0 && (
                <tr><td colSpan={3} className="table-empty">No webhooks yet — add one to send calendar events elsewhere.</td></tr>
              )}
              {webhooks?.map((w) => (
                <tr
                  key={w.id}
                  className={selectedId === w.id ? "row-selected" : ""}
                  onClick={() => { setSelectedId(w.id); setCreating(false); }}
                  style={{ cursor: "pointer" }}
                >
                  <td><span className="mono-chip-inline">{w.url}</span></td>
                  <td>
                    <div className="webhooks-event-tags">
                      {w.events.map((e) => <span key={e} className="mono-chip">{e}</span>)}
                    </div>
                  </td>
                  <td><span className={`status-pill ${w.is_active ? "confirmed" : "cancelled"}`}>{w.is_active ? "active" : "inactive"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {creating && (
          <WebhookDetailPanel mode="create" onClose={() => setCreating(false)} onCreated={handleCreated} />
        )}

        {!creating && selectedWebhook && (
          <WebhookDetailPanel
            key={selectedWebhook.id}
            mode="edit"
            webhook={selectedWebhook}
            onClose={() => setSelectedId(null)}
            onUpdated={handleUpdated}
            onDeleted={handleDeleted}
          />
        )}
      </div>
    </div>
  );
}
