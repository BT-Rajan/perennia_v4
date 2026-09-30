import { THEME_PRESETS, detectActivePreset } from "../data/themePresets.js";
import "./ThemePresetPicker.css";

export default function ThemePresetPicker({ values, onApply }) {
  const activeId = detectActivePreset(values);
  const activePreset = THEME_PRESETS.find((p) => p.id === activeId);

  function handleChange(e) {
    const preset = THEME_PRESETS.find((p) => p.id === e.target.value);
    if (preset) onApply(preset.values);
  }

  return (
    <div className="theme-preset-picker">
      <label className="setting-label" htmlFor="theme-preset-select">
        Theme preset
      </label>
      <p className="setting-help">
        Pick a starting point, then fine-tune anything below. Applying a preset only changes this
        form — nothing goes live until you hit Save.
      </p>

      <select
        id="theme-preset-select"
        className="setting-input theme-preset-select"
        value={activeId ?? ""}
        onChange={handleChange}
      >
        {!activeId && <option value="">Custom (unsaved edits)</option>}
        {THEME_PRESETS.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      <div className="theme-preset-swatch-row">
        {THEME_PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={p.id === activeId ? "theme-preset-card active" : "theme-preset-card"}
            onClick={() => onApply(p.values)}
            title={p.description}
          >
            <span
              className="theme-preset-swatch"
              style={{
                background: p.values["theme.background_color"],
                borderColor: p.values["theme.primary_color"],
              }}
            >
              <span className="theme-preset-dot" style={{ background: p.values["theme.primary_color"] }} />
              <span className="theme-preset-dot" style={{ background: p.values["theme.accent_color"] }} />
              <span
                className="theme-preset-sample"
                style={{
                  color: p.values["theme.text_color"],
                  fontFamily: p.values["theme.font_display"],
                }}
              >
                Aa
              </span>
            </span>
            <span className="theme-preset-name">{p.name}</span>
          </button>
        ))}
      </div>

      {activePreset && <p className="theme-preset-desc">{activePreset.description}</p>}
    </div>
  );
}
