import { useState } from "react";
import { adminApi } from "../api/client.js";
import "./SettingField.css";

const LANG_LABELS = { en: "English", ar: "Arabic" };

function langLabel(code) {
  return LANG_LABELS[code] || code;
}

// A handful of types need their raw string edited as JSON (LIST, JSON) —
// this wraps that in one place: keep a local text buffer so the admin
// can type freely, only attempt to parse (and only report an error) on
// blur, rather than fighting them mid-keystroke.
function JsonTextArea({ value, onChange, onError, rows = 4, describedBy, controlId }) {
  const [text, setText] = useState(() => JSON.stringify(value, null, 2));

  function handleBlur() {
    try {
      const parsed = JSON.parse(text);
      onError(null);
      onChange(parsed);
    } catch {
      onError("Not valid JSON.");
    }
  }

  return (
    <textarea
      id={controlId}
      className="setting-input setting-input-mono"
      rows={rows}
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={handleBlur}
      spellCheck={false}
      aria-describedby={describedBy}
    />
  );
}

// Backs any `image`-typed setting (branding.logo_url, branding.favicon_url).
// An admin can either paste a URL directly or upload a file — uploading
// posts to the existing /admin/api/uploads/image endpoint (PNG/JPEG/WEBP/
// ICO, sniffed server-side) and drops the returned URL straight into the
// text field, so both paths end up setting the exact same string value.
function ImageField({ value, onChange, onError, describedBy, controlId }) {
  const [uploading, setUploading] = useState(false);
  const inputId = `img-upload-${Math.random().toString(36).slice(2)}`;

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file next time
    if (!file) return;
    setUploading(true);
    onError(null);
    try {
      const { url } = await adminApi.uploadImage(file);
      onChange(url);
    } catch (err) {
      onError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="setting-image-field">
      {value && (
        <img src={value} alt="" className="setting-image-preview" onError={(e) => (e.target.style.display = "none")} />
      )}
      <div className="setting-image-controls">
        <input
          id={controlId}
          type="text"
          className="setting-input"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder="/path/to/image.png or https://…"
          aria-describedby={describedBy}
        />
        <label htmlFor={inputId} className="setting-image-upload-btn">
          {uploading ? "Uploading…" : "Upload file"}
        </label>
        <input
          id={inputId}
          type="file"
          accept="image/png,image/jpeg,image/webp,.ico"
          onChange={handleFileChange}
          disabled={uploading}
          hidden
        />
      </div>
    </div>
  );
}

function SingleControl({ def, value, onChange, onError, describedBy, controlId }) {
  switch (def.type) {
    case "bool":
      return (
        <label className="setting-toggle">
          <input id={controlId} type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)}
                 aria-describedby={describedBy} />
          <span>{value ? "On" : "Off"}</span>
        </label>
      );

    case "text":
      return (
        <textarea
          id={controlId}
          className="setting-input"
          rows={4}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={describedBy}
        />
      );

    case "int":
      return (
        <input
          id={controlId}
          type="number"
          step="1"
          className="setting-input"
          value={value ?? 0}
          onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
          aria-describedby={describedBy}
        />
      );

    case "float":
      return (
        <input
          id={controlId}
          type="number"
          step="0.01"
          className="setting-input"
          value={value ?? 0}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          aria-describedby={describedBy}
        />
      );

    case "color":
      return (
        <div className="setting-color-row">
          <input type="color" value={value || "#000000"} onChange={(e) => onChange(e.target.value)} />
          <input
            id={controlId}
            type="text"
            className="setting-input setting-input-mono"
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            aria-describedby={describedBy}
          />
        </div>
      );

    case "enum":
      return (
        <select id={controlId} className="setting-input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}
                aria-describedby={describedBy}>
          {(def.choices || []).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      );

    case "list":
      return (
        <input
          id={controlId}
          type="text"
          className="setting-input"
          value={Array.isArray(value) ? value.join(", ") : ""}
          onChange={(e) => {
            const items = e.target.value.split(",").map((s) => s.trim()).filter((s) => s !== "");
            // Preserve numeric lists (e.g. booking.workdays) rather than
            // turning them into strings of digits.
            const allOriginallyNumeric = Array.isArray(value) && value.every((v) => typeof v === "number");
            onChange(allOriginallyNumeric ? items.map(Number) : items);
          }}
          placeholder="Comma-separated"
          aria-describedby={describedBy}
        />
      );

    case "json":
      return <JsonTextArea value={value} onChange={onChange} onError={onError} rows={6} describedBy={describedBy} controlId={controlId} />;

    case "url":
      return (
        <input id={controlId} type="text" className="setting-input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}
               aria-describedby={describedBy} />
      );

    case "email":
      return (
        <input id={controlId} type="email" className="setting-input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}
               aria-describedby={describedBy} />
      );

    case "image":
      return <ImageField value={value} onChange={onChange} onError={onError} describedBy={describedBy} controlId={controlId} />;

    case "string":
    default:
      return (
        <input id={controlId} type="text" className="setting-input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}
               aria-describedby={describedBy} />
      );
  }
}

export default function SettingField({ field, value, error, onChange, onError }) {
  const errorId = `err-${field.key}`;
  const describedBy = error ? errorId : undefined;

  // JSON types (including i18n JSON, e.g. templates.*) are edited as a
  // single raw JSON blob per language rather than exploded into
  // sub-fields — keeps this fully generic instead of hardcoding the
  // shape of every template.
  const isSecretText = field.secret;

  // The label's htmlFor needs to match whichever control actually
  // gets id={...} below. An i18n field renders one control per
  // language sharing the same field.key, so those get a per-language
  // id instead and the label targets the first one.
  let firstControlId = field.key;

  let control;
  if (isSecretText) {
    control = (
      <input
        id={field.key}
        type="password"
        className="setting-input"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Leave blank to keep the current value"
        autoComplete="new-password"
        aria-describedby={describedBy}
      />
    );
  } else if (field.i18n) {
    const langs = Object.keys(field.default && typeof field.default === "object" ? field.default : { en: "" });
    firstControlId = `${field.key}-${langs[0]}`;
    control = (
      <div className="setting-i18n-group">
        {langs.map((lang) => (
          <div key={lang} className="setting-i18n-row">
            <span className="setting-i18n-lang">{langLabel(lang)}</span>
            <SingleControl
              def={field}
              value={value?.[lang]}
              onChange={(v) => onChange({ ...value, [lang]: v })}
              onError={(msg) => onError(msg)}
              describedBy={describedBy}
              controlId={`${field.key}-${lang}`}
            />
          </div>
        ))}
      </div>
    );
  } else {
    control = <SingleControl def={field} value={value} onChange={onChange} onError={onError} describedBy={describedBy} controlId={field.key} />;
  }

  return (
    <div className="setting-field">
      <label className="setting-label" htmlFor={firstControlId}>
        {field.label}
        {isSecretText && <span className="setting-secret-badge">secret</span>}
      </label>
      {field.help_text && <p className="setting-help">{field.help_text}</p>}
      {control}
      {error && <p className="setting-error" id={errorId} role="alert">{error}</p>}
    </div>
  );
}
