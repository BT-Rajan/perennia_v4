import "./BackgroundIntensityPicker.css";

// Mirrors theme.background_intensity's ENUM choices in
// backend/app/settings_registry.py and the
// [data-background-intensity="..."] rules in
// src/styles/themeVariants.css. Opacity values here are illustrative
// of the real ones (0.022/0.045/0.08/0) — approximated for a readable
// preview swatch rather than pixel-matched.
const LEVELS = [
  { id: "subtle", name: "Subtle", opacity: 0.15, description: "Barely-there texture. Today's default." },
  { id: "soft", name: "Soft", opacity: 0.3, description: "A bit more visible." },
  { id: "bold", name: "Bold", opacity: 0.5, description: "Clearly visible texture." },
  { id: "off", name: "Off", opacity: 0, description: "Hides the pattern entirely, regardless of which one is selected above." },
];

/**
 * Visual picker for theme.background_intensity — how strong the
 * background pattern (selected above) renders.
 */
export default function BackgroundIntensityPicker({ value, onChange }) {
  return (
    <div className="background-intensity-picker">
      <label className="setting-label">Background intensity</label>
      <p className="setting-help">
        How strong the background pattern above is. "Off" hides it entirely, whichever pattern is selected.
      </p>

      <div className="background-intensity-row">
        {LEVELS.map((l) => (
          <button
            key={l.id}
            type="button"
            className={l.id === value ? "background-intensity-card active" : "background-intensity-card"}
            onClick={() => onChange(l.id)}
            title={l.description}
          >
            <span
              className="background-intensity-swatch"
              style={{
                backgroundImage: `linear-gradient(rgba(251,191,36,${l.opacity}) 1px, transparent 1px), linear-gradient(90deg, rgba(251,191,36,${l.opacity}) 1px, transparent 1px)`,
                backgroundSize: "8px 8px",
              }}
            />
            <span className="background-intensity-name">{l.name}</span>
          </button>
        ))}
      </div>

      {LEVELS.find((l) => l.id === value) && (
        <p className="background-intensity-desc">{LEVELS.find((l) => l.id === value).description}</p>
      )}
    </div>
  );
}
