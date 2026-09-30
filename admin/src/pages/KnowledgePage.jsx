import { useCallback, useEffect, useRef, useState } from "react";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import "./KnowledgePage.css";

const TYPE_ICON = { pdf: "📄", docx: "📝", html: "🌐", markdown: "📋", text: "📃", unknown: "❓" };

export default function KnowledgePage() {
  const { handleSessionExpired } = useAuth();
  const [sources, setSources] = useState(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [url, setUrl] = useState("");
  const [addingUrl, setAddingUrl] = useState(false);
  const [previewId, setPreviewId] = useState(null);
  const [previewText, setPreviewText] = useState("");
  const fileInputRef = useRef(null);

  const load = useCallback(() => {
    adminApi
      .listKnowledge()
      .then(setSources)
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [handleSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await adminApi.uploadKnowledgeFile(file);
      load();
    } catch (err) {
      if (err.status === 401) handleSessionExpired();
      else setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleAddUrl(e) {
    e.preventDefault();
    if (!url.trim()) return;
    setAddingUrl(true);
    setError("");
    try {
      await adminApi.addKnowledgeUrl(url.trim());
      setUrl("");
      load();
    } catch (err) {
      if (err.status === 401) handleSessionExpired();
      else setError(err.message);
    } finally {
      setAddingUrl(false);
    }
  }

  async function handleRefresh(id) {
    try {
      await adminApi.refreshKnowledgeSource(id);
      load();
    } catch (err) {
      if (err.status === 401) handleSessionExpired();
      else alert(err.message);
    }
  }

  async function handleToggleActive(source) {
    try {
      await adminApi.setKnowledgeSourceActive(source.id, !source.is_active);
      load();
    } catch (err) {
      if (err.status === 401) handleSessionExpired();
      else alert(err.message);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Remove this source? The assistant will stop using it right away.")) return;
    try {
      await adminApi.deleteKnowledgeSource(id);
      if (previewId === id) setPreviewId(null);
      load();
    } catch (err) {
      if (err.status === 401) handleSessionExpired();
      else alert(err.message);
    }
  }

  async function togglePreview(id) {
    if (previewId === id) {
      setPreviewId(null);
      return;
    }
    try {
      const detail = await adminApi.getKnowledgeSource(id);
      setPreviewText(detail.text);
      setPreviewId(id);
    } catch (err) {
      if (err.status === 401) handleSessionExpired();
      else alert(err.message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        subtitle="Documents and web pages the chat assistant uses as reference when answering - .txt, .md, .html, .docx, .pdf, or a URL."
      />

      {error && <div className="page-error">{error}</div>}

      <div className="kb-add-row">
        <div className="card kb-add-card">
          <label className="setting-label">Upload a file</label>
          <p className="kb-add-hint">.txt, .md, .html, .docx, or .pdf - up to 8MB</p>
          <button
            className="row-action"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Uploading..." : "Choose file"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.html,.htm,.docx,.pdf"
            hidden
            onChange={handleFileChange}
          />
        </div>

        <form className="card kb-add-card" onSubmit={handleAddUrl}>
          <label className="setting-label" htmlFor="kb-url">Add a website address</label>
          <p className="kb-add-hint">Fetched once, then refreshable any time from the list below</p>
          <div className="kb-url-row">
            <input
              id="kb-url"
              type="url"
              placeholder="https://example.com/pricing"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button className="row-action" type="submit" disabled={addingUrl || !url.trim()}>
              {addingUrl ? "Adding..." : "Add"}
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Source</th>
              <th>Type</th>
              <th>Size</th>
              <th>Status</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sources === null && <tr><td colSpan={7} className="table-empty">Loading...</td></tr>}
            {sources?.length === 0 && (
              <tr><td colSpan={7} className="table-empty">No sources yet - upload a file or add a URL above.</td></tr>
            )}
            {sources?.map((s) => (
              <>
                <tr key={s.id}>
                  <td>{TYPE_ICON[s.content_type] || "❓"}</td>
                  <td>
                    <button className="kb-title-btn" onClick={() => togglePreview(s.id)} disabled={!s.ok}>
                      {s.title}
                    </button>
                    {s.kind === "url" && <div className="table-subtext">{s.source_ref}</div>}
                  </td>
                  <td>{s.content_type}</td>
                  <td>{s.chars.toLocaleString()} chars{s.truncated && " (truncated)"}</td>
                  <td>
                    {s.ok ? (
                      <span className="status-pill confirmed">ready</span>
                    ) : (
                      <span className="status-pill cancelled" title={s.error_message}>error</span>
                    )}
                  </td>
                  <td>
                    <label className="setting-toggle">
                      <input type="checkbox" checked={s.is_active} onChange={() => handleToggleActive(s)} />
                    </label>
                  </td>
                  <td className="kb-actions">
                    {s.kind === "url" && (
                      <button className="row-action" onClick={() => handleRefresh(s.id)}>Refresh</button>
                    )}
                    <button className="row-action danger" onClick={() => handleDelete(s.id)}>Delete</button>
                  </td>
                </tr>
                {previewId === s.id && (
                  <tr key={`${s.id}-preview`}>
                    <td colSpan={7}>
                      <pre className="kb-preview">{previewText || "(no extracted text)"}</pre>
                    </td>
                  </tr>
                )}
                {!s.ok && s.error_message && (
                  <tr key={`${s.id}-error`}>
                    <td colSpan={7} className="kb-error-row">{s.error_message}</td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
