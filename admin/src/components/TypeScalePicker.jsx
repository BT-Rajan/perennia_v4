import "./TypeScalePicker.css";

// Mirrors theme.type_scale's ENUM choices in
// backend/app/settings_registry.py and the [data-type-scale="..."]
// rules in src/styles/themeVariants.css.
const SCALES = [
  { id: "standard", name: "Standard", description: "Today's sizes. The default." },
  { id: "compact", name: "Compact", description: "Smaller body text and headings — fits more on screen." },
  { id: "comfortable", name: "Comfortable", description: "Slightly larger, easier-reading text." },
  { id: "large", name: "Large", description: "The largest option, for maximum readability." },
];

/**
 * Visual picker for theme.type_scale — one toggle for body text,
 * small text, and section-card heading sizes site-wide. Doesn't touch
 * the homepage headline, which sizes itself to fit the page.
 */
export default function TypeScalePicker({ value, onChange }) {
  return (
    <div className="type-scale-picker">
      <label className="setting-label">Text size scale</label>
      <p className="setting-help">
        Size for body text, small text, and section-card headings site-wide. The homepage headline is
        unaffected — it sizes itself to fit the page.
      </p>

      <div className="type-scale-row">
        {SCALES.map((s) => (
          <button
            key={s.id}
            type="button"
            className={s.id === value ? "type-scale-card active" : "type-scale-card"}
            onClick={() => onChange(s.id)}
            title={s.description}
          >
            <span className={`type-scale-preview type-scale-preview-${s.id}`}>Aa</span>
            <span className="type-scale-name">{s.name}</span>
          </button>
        ))}
      </div>

      {SCALES.find((s) => s.id === value) && (
        <p className="type-scale-desc">{SCALES.find((s) => s.id === value).description}</p>
      )}
    </div>
  );
}
