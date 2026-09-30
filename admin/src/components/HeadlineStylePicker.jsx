import "./HeadlineStylePicker.css";

// Mirrors theme.headline_style's ENUM choices in
// backend/app/settings_registry.py and the CSS in src/components/hero/
// Hero.css ([data-headline-style="..."] rules). Previews approximate
// the real effect with plain CSS (no animation in the small preview,
// to keep the settings page calm) — the live homepage is the real
// preview.
const STYLES = [
  { id: "ripple-gradient", name: "Ripple gradient", description: "A light sweep travels through a gold/blue gradient fill. The original style." },
  { id: "solid-gold", name: "Solid gold", description: "Plain, static gold text. No animation." },
  { id: "solid-white", name: "Solid white", description: "Plain, static white text. No animation." },
  { id: "two-tone", name: "Two-tone", description: "A static (non-moving) split between white and gold." },
  { id: "outline", name: "Outline", description: "Transparent fill with a thin gold outline stroke." },
];

/**
 * Visual picker for theme.headline_style — same "gallery of cards,
 * click to select" pattern as ThemePresetPicker/LayoutTemplatePicker.
 * Deliberately narrow in scope: only ever writes this one enum field,
 * so it can't touch the headline's actual text (that's on-screen text
 * copy) or the page's layout template.
 */
export default function HeadlineStylePicker({ value, onChange }) {
  return (
    <div className="headline-style-picker">
      <label className="setting-label">Headline style</label>
      <p className="setting-help">
        Visual treatment of the homepage headline text. Content comes from the on-screen text settings —
        this only changes how it's drawn.
      </p>

      <div className="headline-style-row">
        {STYLES.map((s) => (
          <button
            key={s.id}
            type="button"
            className={s.id === value ? "headline-style-card active" : "headline-style-card"}
            onClick={() => onChange(s.id)}
            title={s.description}
          >
            <span className="headline-style-preview">
              <span className={`headline-style-preview-fill headline-style-preview-${s.id}`}>Aa</span>
            </span>
            <span className="headline-style-name">{s.name}</span>
          </button>
        ))}
      </div>

      {STYLES.find((s) => s.id === value) && (
        <p className="headline-style-desc">{STYLES.find((s) => s.id === value).description}</p>
      )}
    </div>
  );
}
