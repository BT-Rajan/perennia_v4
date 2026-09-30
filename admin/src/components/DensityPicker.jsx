import "./DensityPicker.css";

// Mirrors theme.density's ENUM choices in
// backend/app/settings_registry.py and the [data-density="..."]
// rules in src/styles/themeVariants.css.
const LEVELS = [
  { id: "compact", name: "Compact", description: "Tighter padding, gaps, and line-height throughout — fits more on screen." },
  { id: "comfortable", name: "Comfortable", description: "Today's spacing. The default." },
  { id: "spacious", name: "Spacious", description: "Looser padding, gaps, and line-height — an airier feel." },
];

function DensityThumb({ id }) {
  const gap = id === "compact" ? 3 : id === "spacious" ? 9 : 6;
  const bars = id === "compact" ? 4 : id === "spacious" ? 2 : 3;
  return (
    <span className="density-thumb" style={{ gap: `${gap}px` }}>
      {Array.from({ length: bars }).map((_, i) => (
        <span key={i} className="density-thumb-bar" />
      ))}
    </span>
  );
}

/**
 * Visual picker for theme.density — one toggle for padding, gaps, and
 * prose line-height site-wide (every card, button, and text block
 * moves together).
 */
export default function DensityPicker({ value, onChange }) {
  return (
    <div className="density-picker">
      <label className="setting-label">Spacing density</label>
      <p className="setting-help">
        Padding, gaps, and text line-height site-wide — every card, button, and text block scales together.
      </p>

      <div className="density-row">
        {LEVELS.map((l) => (
          <button
            key={l.id}
            type="button"
            className={l.id === value ? "density-card active" : "density-card"}
            onClick={() => onChange(l.id)}
            title={l.description}
          >
            <DensityThumb id={l.id} />
            <span className="density-name">{l.name}</span>
          </button>
        ))}
      </div>

      {LEVELS.find((l) => l.id === value) && (
        <p className="density-desc">{LEVELS.find((l) => l.id === value).description}</p>
      )}
    </div>
  );
}
