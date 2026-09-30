import { useCallback, useEffect, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import PageDetailPanel from "../components/PageDetailPanel.jsx";
import "./ServicesPage.css";

export default function PagesPage() {
  const { handleSessionExpired } = useAuth();
  const [pages, setPages] = useState(null);
  const [error, setError] = useState("");
  const [selectedSlug, setSelectedSlug] = useState(null);
  const [creating, setCreating] = useState(false);
  const [reordering, setReordering] = useState(false);

  const load = useCallback(() => {
    adminApi
      .listPages()
      .then((list) => setPages([...list].sort((a, b) => a.order - b.order)))
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [handleSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated(page) {
    setPages((prev) => [...(prev ?? []), page]);
    setCreating(false);
    setSelectedSlug(page.slug);
  }

  function handleUpdated(updated) {
    setPages((prev) => prev.map((p) => (p.slug === updated.slug ? updated : p)));
  }

  function handleDeleted(slug) {
    setPages((prev) => prev.filter((p) => p.slug !== slug));
    setSelectedSlug(null);
  }

  async function move(index, direction) {
    const target = index + direction;
    if (!pages || target < 0 || target >= pages.length) return;
    const reordered = [...pages];
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    setPages(reordered);
    setReordering(true);
    try {
      await adminApi.reorderPages(reordered.map((p) => p.slug));
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setError(e.message);
      load(); // reconcile with server state on failure
    } finally {
      setReordering(false);
    }
  }

  const selectedPage = pages?.find((p) => p.slug === selectedSlug) ?? null;

  return (
    <div>
      <PageHeader
        title="Pages"
        subtitle="Every standalone content page on the site — nav label, home teaser, and full Markdown body, per language."
        actions={
          <button className="row-action primary" onClick={() => { setCreating(true); setSelectedSlug(null); }}>
            + New page
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
                <th>Slug</th>
                <th>Nav label (EN)</th>
                <th>Visible</th>
                <th>In nav</th>
              </tr>
            </thead>
            <tbody>
              {pages === null && (
                <tr><td colSpan={5} className="table-empty">Loading…</td></tr>
              )}
              {pages?.length === 0 && (
                <tr><td colSpan={5} className="table-empty">No pages yet — add your first one.</td></tr>
              )}
              {pages?.map((p, i) => (
                <tr
                  key={p.slug}
                  className={selectedSlug === p.slug ? "row-selected" : ""}
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
                        disabled={reordering || i === pages.length - 1}
                        onClick={() => move(i, 1)}
                        aria-label="Move down"
                      >
                        ↓
                      </button>
                    </div>
                  </td>
                  <td onClick={() => { setSelectedSlug(p.slug); setCreating(false); }}>
                    <span className="mono-chip-inline">{p.slug}</span>
                  </td>
                  <td onClick={() => { setSelectedSlug(p.slug); setCreating(false); }}>
                    {p.translations?.en?.nav_label || <span className="table-subtext">—</span>}
                  </td>
                  <td onClick={() => { setSelectedSlug(p.slug); setCreating(false); }}>
                    <span className={`status-pill ${p.is_visible ? "confirmed" : "cancelled"}`}>
                      {p.is_visible ? "visible" : "hidden"}
                    </span>
                  </td>
                  <td onClick={() => { setSelectedSlug(p.slug); setCreating(false); }}>
                    {p.show_in_nav ? "Yes" : "No"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {creating && (
          <PageDetailPanel mode="create" onClose={() => setCreating(false)} onCreated={handleCreated} />
        )}

        {!creating && selectedPage && (
          <PageDetailPanel
            key={selectedPage.slug}
            mode="edit"
            page={selectedPage}
            onClose={() => setSelectedSlug(null)}
            onUpdated={handleUpdated}
            onDeleted={handleDeleted}
          />
        )}
      </div>
    </div>
  );
}
