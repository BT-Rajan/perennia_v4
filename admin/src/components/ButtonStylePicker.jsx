import "./ButtonStylePicker.css";

// Mirrors theme.button_style's ENUM choices in
// backend/app/settings_registry.py and the [data-button-style="..."]
// rules in src/styles/themeVariants.css.
const STYLES = [
  { id: "default", name: "Default", description: "Each button keeps its own current look (not uniform today — pills are outlined, sticky buttons are solid)." },
  { id: "solid", name: "Solid", description: "Every button/pill filled solid gold." },
  { id: "outline", name: "Outline", description: "Every button/pill transparent with a gold border." },
  { id: "ghost", name: "Ghost", description: "Every button/pill borderless and transparent until hovered." },
  { id: "gradient", name: "Gradient", description: "Every button/pill filled with a gold gradient and soft glow." },
];

function ButtonThumb({ id }) {
  return (
    <span className="button-thumb">
      <span className={`button-thumb-pill button-thumb-pill-${id}`}>Ab</span>
    </span>
  );
}

/**
 * Visual picker for theme.button_style — covers CTA-style buttons and
 * pills site-wide (homepage quick links, centered-card pills, the two
 * sticky buttons) with one toggle. "Default" is explicitly not
 * uniform — it's what's live today — every other choice unifies all
 * of them, including color.
 */
export default function ButtonStylePicker({ value, onChange }) {
  return (
    <div className="button-style-picker">
      <label className="setting-label">Buttons &amp; pills</label>
      <p className="setting-help">
        Fill treatment for call-to-action buttons and pills site-wide. "Default" leaves each button's
        current look as-is; any other choice makes them all match one style, including color.
      </p>

      <div className="button-style-row">
        {STYLES.map((s) => (
          <button
            key={s.id}
            type="button"
            className={s.id === value ? "button-style-card active" : "button-style-card"}
            onClick={() => onChange(s.id)}
            title={s.description}
          >
            <ButtonThumb id={s.id} />
            <span className="button-style-name">{s.name}</span>
          </button>
        ))}
      </div>

      {STYLES.find((s) => s.id === value) && (
        <p className="button-style-desc">{STYLES.find((s) => s.id === value).description}</p>
      )}
    </div>
  );
}
