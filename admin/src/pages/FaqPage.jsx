import { useCallback, useEffect, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FaqDetailPanel from "../components/FaqDetailPanel.jsx";
import "./ServicesPage.css";

/**
 * Admin management for the FAQ items shown in the chat assistant's
 * "Quick Questions" screen (copy.chat.faq_title — see
 * settings_registry.py). Mirrors PagesPage.jsx's table + side-panel
 * shape: content_service.py/admin_content.py have carried full FAQ
 * CRUD (create/update/delete/reorder) since the pages feature shipped,
 * but nothing in the admin ever called it — this is that missing UI.
 */
export default function FaqPage() {
  const { handleSessionExpired } = useAuth();
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [reordering, setReordering] = useState(false);

  const load = useCallback(() => {
    adminApi
      .listFaq()
      .then((list) => setItems([...list].sort((a, b) => a.order - b.order)))
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [handleSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated(item) {
    setItems((prev) => [...(prev ?? []), item]);
    setCreating(false);
    setSelectedId(item.id);
  }

  function handleUpdated(updated) {
    setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
  }

  function handleDeleted(id) {
    setItems((prev) => prev.filter((i) => i.id !== id));
    setSelectedId(null);
  }

  async function move(index, direction) {
    const target = index + direction;
    if (!items || target < 0 || target >= items.length) return;
    const reordered = [...items];
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    setItems(reordered);
    setReordering(true);
    try {
      await adminApi.reorderFaq(reordered.map((i) => i.id));
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setError(e.message);
      load(); // reconcile with server state on failure
    } finally {
      setReordering(false);
    }
  }

  const selectedItem = items?.find((i) => i.id === selectedId) ?? null;

  return (
    <div>
      <PageHeader
        title="FAQ"
        subtitle="Quick questions shown in the AI Assistant's Quick Questions screen, per language."
        actions={
          <button className="row-action primary" onClick={() => { setCreating(true); setSelectedId(null); }}>
            + New question
          </button>
        }
      />

      {error && <div className="page-error">{error}</div>}

      <div className="services-layout">
        <div className="card services-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Order</th>
                <th>Question (EN)</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {items === null && (
                <tr><td colSpan={3} className="table-empty">Loading…</td></tr>
              )}
              {items?.length === 0 && (
                <tr><td colSpan={3} className="table-empty">No FAQ items yet — add your first one.</td></tr>
              )}
              {items?.map((item, i) => (
                <tr
                  key={item.id}
                  className={selectedId === item.id ? "row-selected" : ""}
                  style={{ cursor: "pointer" }}
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        className="row-action"
                        disabled={reordering || i === 0}
                        onClick={() => move(i, -1)}
                        aria-label="Move up"
                      >
                        ↑
                      </button>
                      <button
                        className="row-action"
                        disabled={reordering || i === items.length - 1}
                        onClick={() => move(i, 1)}
                        aria-label="Move down"
                      >
                        ↓
                      </button>
                    </div>
                  </td>
                  <td onClick={() => { setSelectedId(item.id); setCreating(false); }}>
                    {item.translations?.en?.q || <span className="table-subtext">—</span>}
                  </td>
                  <td onClick={() => { setSelectedId(item.id); setCreating(false); }}>
                    <span className={`status-pill ${item.is_active ? "confirmed" : "cancelled"}`}>
                      {item.is_active ? "active" : "inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {creating && (
          <FaqDetailPanel mode="create" onClose={() => setCreating(false)} onCreated={handleCreated} />
        )}

        {!creating && selectedItem && (
          <FaqDetailPanel
            key={selectedItem.id}
            mode="edit"
            item={selectedItem}
            onClose={() => setSelectedId(null)}
            onUpdated={handleUpdated}
            onDeleted={handleDeleted}
          />
        )}
      </div>
    </div>
  );
}
