import "./BackgroundStylePicker.css";

// Mirrors theme.background_style's ENUM choices in
// backend/app/settings_registry.py and the
// [data-background-style="..."] rules in src/styles/themeVariants.css.
const STYLES = [
  { id: "grid", name: "Grid", description: "A faint line-mesh overlay across the whole page. Today's look." },
  { id: "dot-grid", name: "Dot grid", description: "A faint dot pattern instead of lines." },
  { id: "radial-glow", name: "Radial glow", description: "Soft colored glows instead of a repeating pattern." },
  { id: "solid", name: "Solid", description: "No texture — a plain flat background." },
];

function BackgroundThumb({ id }) {
  return <span className={`background-thumb background-thumb-${id}`} />;
}

/**
 * Visual picker for theme.background_style — the texture behind all
 * page content, site-wide.
 */
export default function BackgroundStylePicker({ value, onChange }) {
  return (
    <div className="background-style-picker">
      <label className="setting-label">Background pattern</label>
      <p className="setting-help">Texture behind all page content. Works together with the intensity setting below.</p>

      <div className="background-style-row">
        {STYLES.map((s) => (
          <button
            key={s.id}
            type="button"
            className={s.id === value ? "background-style-card active" : "background-style-card"}
            onClick={() => onChange(s.id)}
            title={s.description}
          >
            <BackgroundThumb id={s.id} />
            <span className="background-style-name">{s.name}</span>
          </button>
        ))}
      </div>

      {STYLES.find((s) => s.id === value) && (
        <p className="background-style-desc">{STYLES.find((s) => s.id === value).description}</p>
      )}
    </div>
  );
}
