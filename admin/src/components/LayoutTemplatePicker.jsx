import "./LayoutTemplatePicker.css";

// Mirrors the LAYOUTS map in src/components/hero/Hero.jsx exactly —
// these ids are theme.layout_template's ENUM choices in
// backend/app/settings_registry.py. Each thumbnail is a tiny, purely
// decorative CSS mockup (no real content/copy) just to convey the
// arrangement at a glance; the real preview is the live site itself.
const LAYOUTS = [
  {
    id: "classic",
    name: "Classic",
    description: "Centered headline, quick-chat box, and a card grid of page links below. The original layout.",
  },
  {
    id: "split",
    name: "Split",
    description: "Headline and quick-chat on one side, page links stacked as a list on the other.",
  },
  {
    id: "centered-card",
    name: "Centered card",
    description: "Everything — headline, quick-chat, and page links — inside one bordered card. Compact and boutique.",
  },
  {
    id: "editorial",
    name: "Editorial",
    description: "Large left-aligned headline with page links in a horizontal scrolling strip. Magazine-style.",
  },
];

function LayoutThumbnail({ id }) {
  if (id === "split") {
    return (
      <span className="layout-thumb layout-thumb-split">
        <span className="layout-thumb-col">
          <span className="layout-thumb-bar layout-thumb-bar-lg" />
          <span className="layout-thumb-bar layout-thumb-bar-sm" />
          <span className="layout-thumb-pill" />
        </span>
        <span className="layout-thumb-col">
          <span className="layout-thumb-row" />
          <span className="layout-thumb-row" />
          <span className="layout-thumb-row" />
        </span>
      </span>
    );
  }
  if (id === "centered-card") {
    return (
      <span className="layout-thumb layout-thumb-card">
        <span className="layout-thumb-inner-card">
          <span className="layout-thumb-bar layout-thumb-bar-lg" />
          <span className="layout-thumb-bar layout-thumb-bar-sm" />
          <span className="layout-thumb-pill" />
          <span className="layout-thumb-dots">
            <span className="layout-thumb-dot" />
            <span className="layout-thumb-dot" />
            <span className="layout-thumb-dot" />
          </span>
        </span>
      </span>
    );
  }
  if (id === "editorial") {
    return (
      <span className="layout-thumb layout-thumb-editorial">
        <span className="layout-thumb-bar layout-thumb-bar-lg layout-thumb-bar-left" />
        <span className="layout-thumb-bar layout-thumb-bar-sm layout-thumb-bar-left" />
        <span className="layout-thumb-pill layout-thumb-pill-left" />
        <span className="layout-thumb-strip">
          <span className="layout-thumb-card-sm" />
          <span className="layout-thumb-card-sm" />
          <span className="layout-thumb-card-sm" />
        </span>
      </span>
    );
  }
  // classic
  return (
    <span className="layout-thumb layout-thumb-classic">
      <span className="layout-thumb-bar layout-thumb-bar-lg" />
      <span className="layout-thumb-bar layout-thumb-bar-sm" />
      <span className="layout-thumb-pill" />
      <span className="layout-thumb-grid">
        <span className="layout-thumb-card-sm" />
        <span className="layout-thumb-card-sm" />
        <span className="layout-thumb-card-sm" />
      </span>
    </span>
  );
}

/**
 * Visual picker for theme.layout_template — same "gallery of cards,
 * click to select" pattern as ThemePresetPicker, but for page
 * structure instead of color/font. Deliberately narrow in scope: this
 * only ever writes the one enum field, so picking a layout can't
 * touch colors, fonts, or any other setting.
 */
export default function LayoutTemplatePicker({ value, onChange }) {
  return (
    <div className="layout-template-picker">
      <label className="setting-label">Homepage layout</label>
      <p className="setting-help">
        How the homepage headline, quick-chat box, and page links are arranged. Colors and fonts come
        from the theme preset above — this only changes structure. Nothing goes live until you hit Save.
      </p>

      <div className="layout-template-row">
        {LAYOUTS.map((l) => (
          <button
            key={l.id}
            type="button"
            className={l.id === value ? "layout-template-card active" : "layout-template-card"}
            onClick={() => onChange(l.id)}
            title={l.description}
          >
            <LayoutThumbnail id={l.id} />
            <span className="layout-template-name">{l.name}</span>
          </button>
        ))}
      </div>

      {LAYOUTS.find((l) => l.id === value) && (
        <p className="layout-template-desc">{LAYOUTS.find((l) => l.id === value).description}</p>
      )}
    </div>
  );
}
