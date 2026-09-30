import "./SurfaceStylePicker.css";

// Mirrors theme.surface_style's ENUM choices in
// backend/app/settings_registry.py and the [data-surface-style="..."]
// rules in src/styles/themeVariants.css.
const STYLES = [
  { id: "glass", name: "Glass", description: "Blurred, translucent panels with a soft border. The original look." },
  { id: "solid", name: "Solid", description: "Flat, opaque fill. No blur." },
  { id: "outline", name: "Outline", description: "Transparent fill, just a border. No blur, no shadow." },
  { id: "elevated", name: "Elevated", description: "Solid fill with a stronger drop shadow for extra depth." },
];

function SurfaceThumb({ id }) {
  return <span className={`surface-thumb surface-thumb-${id}`} />;
}

/**
 * Visual picker for theme.surface_style — covers every card/panel
 * surface site-wide (the chat widget, booking panel, homepage nav and
 * content cards) with one toggle. Same gallery pattern as the other
 * theme pickers; only ever writes this one enum field.
 */
export default function SurfaceStylePicker({ value, onChange }) {
  return (
    <div className="surface-style-picker">
      <label className="setting-label">Card &amp; panel surface</label>
      <p className="setting-help">
        Fill treatment for cards and panels site-wide — the chat widget, booking panel, and homepage
        nav/content cards all follow this one setting.
      </p>

      <div className="surface-style-row">
        {STYLES.map((s) => (
          <button
            key={s.id}
            type="button"
            className={s.id === value ? "surface-style-card active" : "surface-style-card"}
            onClick={() => onChange(s.id)}
            title={s.description}
          >
            <SurfaceThumb id={s.id} />
            <span className="surface-style-name">{s.name}</span>
          </button>
        ))}
      </div>

      {STYLES.find((s) => s.id === value) && (
        <p className="surface-style-desc">{STYLES.find((s) => s.id === value).description}</p>
      )}
    </div>
  );
}
