import "./SectionRhythmPicker.css";

// Mirrors theme.section_rhythm's ENUM choices in
// backend/app/settings_registry.py and the
// [data-section-rhythm="..."] rules in src/styles/themeVariants.css.
const LEVELS = [
  { id: "tight", name: "Tight", description: "Less breathing room between major page sections, regardless of the density setting above." },
  { id: "standard", name: "Standard", description: "Scales proportionally with the density setting above. The default." },
  { id: "loose", name: "Loose", description: "More breathing room between major page sections, regardless of density." },
];

function RhythmThumb({ id }) {
  const gap = id === "tight" ? 4 : id === "loose" ? 14 : 8;
  return (
    <span className="rhythm-thumb">
      <span className="rhythm-thumb-block" />
      <span className="rhythm-thumb-spacer" style={{ height: `${gap}px` }} />
      <span className="rhythm-thumb-block" />
    </span>
  );
}

/**
 * Visual picker for theme.section_rhythm — breathing room between
 * major page sections/blocks (e.g. the gap before the homepage's
 * nav-card grid), independent of theme.density above.
 */
export default function SectionRhythmPicker({ value, onChange }) {
  return (
    <div className="rhythm-picker">
      <label className="setting-label">Section rhythm</label>
      <p className="setting-help">
        Breathing room specifically between major page sections — independent of the spacing density
        above, so you can pair tight card spacing with generous section gaps, or vice versa.
      </p>

      <div className="rhythm-row">
        {LEVELS.map((l) => (
          <button
            key={l.id}
            type="button"
            className={l.id === value ? "rhythm-card active" : "rhythm-card"}
            onClick={() => onChange(l.id)}
            title={l.description}
          >
            <RhythmThumb id={l.id} />
            <span className="rhythm-name">{l.name}</span>
          </button>
        ))}
      </div>

      {LEVELS.find((l) => l.id === value) && (
        <p className="rhythm-desc">{LEVELS.find((l) => l.id === value).description}</p>
      )}
    </div>
  );
}
