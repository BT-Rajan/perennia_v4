import { useEffect, useRef, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./ServiceDetailPanel.css";

const LANGS = ["en", "ar"];

function emptyTranslations() {
  const t = {};
  for (const lang of LANGS) {
    t[lang] = { nav_label: "", section_title: "", section_body: "", tagline_line1: "", tagline_line2: "", tagline_sub: "", body_markdown: "" };
  }
  return t;
}

export default function PageDetailPanel({ mode, page, onClose, onCreated, onUpdated, onDeleted }) {
  const { handleSessionExpired } = useAuth();
  const [slug, setSlug] = useState(mode === "edit" ? page.slug : "");
  const [lang, setLang] = useState("en");
  const [translations, setTranslations] = useState(
    mode === "edit" ? { ...emptyTranslations(), ...page.translations } : emptyTranslations()
  );
  const [isVisible, setIsVisible] = useState(mode === "edit" ? page.is_visible : true);
  const [showInNav, setShowInNav] = useState(mode === "edit" ? page.show_in_nav : true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  // Version history — every save (edit mode only; a brand-new page has
  // no prior state to snapshot) writes a version server-side, so an
  // admin can see what changed and undo a bad edit without having to
  // remember or retype the previous copy.
  const [versions, setVersions] = useState(null);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versionsError, setVersionsError] = useState("");
  const [rollingBackId, setRollingBackId] = useState(null);

  useEffect(() => {
    if (mode !== "edit") return;
    adminApi
      .listPageVersions(page.slug)
      .then(setVersions)
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setVersionsError(e.message)));
  }, [mode, page?.slug, handleSessionExpired]);

  function setField(field, value) {
    setTranslations((prev) => ({ ...prev, [lang]: { ...prev[lang], [field]: value } }));
  }

  function handleApiError(e) {
    if (e.status === 401) handleSessionExpired();
    else setError(e.message);
  }

  async function handleRollback(versionId) {
    if (!confirm("Restore this earlier version? Your current unsaved edits above will be replaced.")) return;
    setRollingBackId(versionId);
    setVersionsError("");
    try {
      const restored = await adminApi.rollbackPage(page.slug, versionId);
      setTranslations({ ...emptyTranslations(), ...restored.translations });
      setIsVisible(restored.is_visible);
      setShowInNav(restored.show_in_nav);
      onUpdated(restored);
      const fresh = await adminApi.listPageVersions(page.slug);
      setVersions(fresh);
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setVersionsError(e.message);
    } finally {
      setRollingBackId(null);
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      setField("body_markdown", text);
    } catch {
      setError("Couldn't read that file — make sure it's a plain text/Markdown file.");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleSave() {
    if (!slug.trim()) {
      setError("Slug is required (e.g. \"about\", \"faq\", \"warranty\").");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const cleanSlug = slug.trim().toLowerCase().replace(/[^a-z0-9-]/g, "-");
      const saved = await adminApi.upsertPage(cleanSlug, {
        translations, is_visible: isVisible, show_in_nav: showInNav,
      });
      if (mode === "create") onCreated(saved);
      else {
        onUpdated(saved);
        // The backend snapshots the pre-edit state on every save, so
        // the version list has a new entry the moment this succeeds.
        adminApi.listPageVersions(saved.slug).then(setVersions).catch(() => {});
      }
    } catch (e) {
      handleApiError(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete the page "${page.slug}"? This removes it from the site immediately and can't be undone.`)) return;
    try {
      await adminApi.deletePage(page.slug);
      onDeleted(page.slug);
    } catch (e) {
      handleApiError(e);
    }
  }

  const t = translations[lang] || {};

  return (
    <aside className="card service-panel">
      <div className="service-panel-head">
        <div className="service-panel-title">{mode === "create" ? "New page" : page.slug}</div>
        <button className="service-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      {mode === "create" && (
        <>
          <label className="service-panel-label">Slug</label>
          <input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="e.g. warranty" />
        </>
      )}

      <div className="service-panel-check" style={{ marginTop: 8 }}>
        <input type="checkbox" checked={isVisible} onChange={(e) => setIsVisible(e.target.checked)} />
        Visible on the public site
      </div>
      <div className="service-panel-check">
        <input type="checkbox" checked={showInNav} onChange={(e) => setShowInNav(e.target.checked)} />
        Show in nav menu
      </div>

      <div className="service-panel-row-2" style={{ marginTop: 12 }}>
        {LANGS.map((l) => (
          <button
            key={l}
            type="button"
            className="service-panel-save"
            style={lang === l ? {} : { background: "transparent", color: "var(--text-muted)", border: "1px solid var(--border)" }}
            onClick={() => setLang(l)}
          >
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      <label className="service-panel-label">Nav menu label</label>
      <input value={t.nav_label || ""} onChange={(e) => setField("nav_label", e.target.value)} />

      <label className="service-panel-label">Home teaser title</label>
      <input value={t.section_title || ""} onChange={(e) => setField("section_title", e.target.value)} />

      <label className="service-panel-label">Home teaser text</label>
      <textarea rows={2} value={t.section_body || ""} onChange={(e) => setField("section_body", e.target.value)} />

      <label className="service-panel-label">Page header — line 1</label>
      <input value={t.tagline_line1 || ""} onChange={(e) => setField("tagline_line1", e.target.value)} />

      <label className="service-panel-label">Page header — line 2 (accent)</label>
      <input value={t.tagline_line2 || ""} onChange={(e) => setField("tagline_line2", e.target.value)} />

      <label className="service-panel-label">Page header — subtitle</label>
      <input value={t.tagline_sub || ""} onChange={(e) => setField("tagline_sub", e.target.value)} />

      <label className="service-panel-label">
        Full page body (Markdown) — {lang.toUpperCase()}
      </label>
      <textarea
        rows={10}
        value={t.body_markdown || ""}
        onChange={(e) => setField("body_markdown", e.target.value)}
        placeholder="Paste Markdown here, or upload a .md file below."
        style={{ fontFamily: "monospace", fontSize: 12.5 }}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept=".md,.markdown,.txt"
        onChange={handleFileUpload}
        style={{ marginTop: 6 }}
      />

      {error && <div className="service-panel-error">{error}</div>}

      <button className="service-panel-save" onClick={handleSave} disabled={saving}>
        {saving ? "Saving…" : "Save page"}
      </button>

      {mode === "edit" && (
        <button className="service-panel-delete" onClick={handleDelete}>
          Delete page
        </button>
      )}

      {mode === "edit" && (
        <>
          <button
            type="button"
            className="service-panel-save"
            style={{ background: "transparent", color: "var(--text-muted)", border: "1px solid var(--border)" }}
            onClick={() => setVersionsOpen((o) => !o)}
          >
            {versionsOpen ? "Hide" : "Show"} version history{versions ? ` (${versions.length})` : ""}
          </button>

          {versionsOpen && (
            <div className="question-list">
              {versions === null && !versionsError && (
                <div className="table-subtext">Loading…</div>
              )}
              {versions?.length === 0 && (
                <div className="table-subtext">No earlier versions yet — one is saved automatically every time you edit this page.</div>
              )}
              {versions?.map((v) => (
                <div className="question-row" key={v.id}>
                  <div className="question-row-main">
                    {new Date(v.saved_at).toLocaleString()}
                    {v.saved_by_username ? ` — ${v.saved_by_username}` : ""}
                  </div>
                  <div className="question-row-actions">
                    <button
                      type="button"
                      className="row-action"
                      disabled={rollingBackId === v.id}
                      onClick={() => handleRollback(v.id)}
                    >
                      {rollingBackId === v.id ? "Restoring…" : "Restore this version"}
                    </button>
                  </div>
                </div>
              ))}
              {versionsError && <div className="service-panel-error">{versionsError}</div>}
            </div>
          )}
        </>
      )}
    </aside>
  );
}
