import "./HeadingCasePicker.css";

// Mirrors theme.heading_case's ENUM choices in
// backend/app/settings_registry.py and the [data-heading-case="..."]
// rules in src/styles/themeVariants.css.
const CASES = [
  { id: "as-is", name: "As-is", description: "Today's normal-case section headings. The default." },
  { id: "uppercase-tracked", name: "Uppercase", description: "All-caps with wider letter-spacing — a common corporate/editorial look." },
  { id: "sentence-case", name: "Sentence case", description: "Plain sentence casing, no letter-spacing adjustment." },
];

function CasePreview({ id }) {
  if (id === "uppercase-tracked") {
    return <span className="heading-case-preview heading-case-preview-upper">ABOUT US</span>;
  }
  return <span className="heading-case-preview">About us</span>;
}

/**
 * Visual picker for theme.heading_case — casing/tracking for
 * section-card titles (e.g. the homepage nav cards) site-wide.
 */
export default function HeadingCasePicker({ value, onChange }) {
  return (
    <div className="heading-case-picker">
      <label className="setting-label">Section heading style</label>
      <p className="setting-help">
        Casing and letter-spacing for section/card titles, like the homepage nav cards.
      </p>

      <div className="heading-case-row">
        {CASES.map((c) => (
          <button
            key={c.id}
            type="button"
            className={c.id === value ? "heading-case-card active" : "heading-case-card"}
            onClick={() => onChange(c.id)}
            title={c.description}
          >
            <CasePreview id={c.id} />
            <span className="heading-case-name">{c.name}</span>
          </button>
        ))}
      </div>

      {CASES.find((c) => c.id === value) && (
        <p className="heading-case-desc">{CASES.find((c) => c.id === value).description}</p>
      )}
    </div>
  );
}
