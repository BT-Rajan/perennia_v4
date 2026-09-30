import { useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import "./ServiceDetailPanel.css";

const LANGS = ["en", "ar"];

function emptyTranslations() {
  const t = {};
  for (const lang of LANGS) t[lang] = { q: "", a: "" };
  return t;
}

export default function FaqDetailPanel({ mode, item, onClose, onCreated, onUpdated, onDeleted }) {
  const { handleSessionExpired } = useAuth();
  const [lang, setLang] = useState("en");
  const [translations, setTranslations] = useState(
    mode === "edit" ? { ...emptyTranslations(), ...item.translations } : emptyTranslations()
  );
  const [isActive, setIsActive] = useState(mode === "edit" ? item.is_active : true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function setField(field, value) {
    setTranslations((prev) => ({ ...prev, [lang]: { ...prev[lang], [field]: value } }));
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
        const created = await adminApi.createFaq({ translations, is_active: isActive, order: 0 });
        onCreated(created);
      } else {
        const updated = await adminApi.updateFaq(item.id, {
          translations, is_active: isActive, order: item.order,
        });
        onUpdated(updated);
      }
    } catch (e) {
      handleApiError(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this FAQ item? This removes it from the site immediately and can't be undone.")) return;
    try {
      await adminApi.deleteFaq(item.id);
      onDeleted(item.id);
    } catch (e) {
      handleApiError(e);
    }
  }

  const t = translations[lang] || {};
  const canSave = LANGS.some((l) => translations[l]?.q?.trim() && translations[l]?.a?.trim());

  return (
    <aside className="card service-panel">
      <div className="service-panel-head">
        <div className="service-panel-title">{mode === "create" ? "New FAQ item" : "Edit FAQ item"}</div>
        <button className="service-panel-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      <div className="service-panel-check" style={{ marginTop: 8 }}>
        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
        Active (shown on the public site)
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

      <label className="service-panel-label">Question — {lang.toUpperCase()}</label>
      <input value={t.q || ""} onChange={(e) => setField("q", e.target.value)} />

      <label className="service-panel-label">Answer — {lang.toUpperCase()}</label>
      <textarea rows={4} value={t.a || ""} onChange={(e) => setField("a", e.target.value)} />

      {error && <div className="service-panel-error">{error}</div>}

      <button className="service-panel-save" onClick={handleSave} disabled={saving || !canSave}>
        {saving ? "Saving…" : "Save question"}
      </button>

      {mode === "edit" && (
        <button className="service-panel-delete" onClick={handleDelete}>
          Delete question
        </button>
      )}
    </aside>
  );
}
