// Curated theme presets for the admin "Theme" settings page.
//
// The whole site derives its entire look — surfaces, glass cards,
// gradients, borders, glow effects — from just a handful of base
// tokens via color-mix() (see src/styles/tokens.css). Every preset
// here works within that system rather than fighting it: all three
// keep a dark base surface, because the shared component CSS uses
// light-on-dark glassmorphism (translucent white overlays for cards,
// faded-white tokens for secondary text) that only reads correctly
// against a dark background — a light preset would wash out every
// card border and mute every secondary label. Luxury and variety come
// from hue, gold tone, and type pairing instead, each still validated
// for contrast in both directions (as body text on the background,
// and as button text via --on-gold-text, which resolves to the
// background color placed on top of the primary color).
//
// Keys here match the `theme.*` setting keys exactly, so a preset's
// `values` object can be merged straight into SettingsPage's form
// state.

export const THEME_PRESETS = [
  {
    id: "midnight-gold",
    name: "Midnight Gold",
    description: "Deep navy with a warm gold signature — the original Perennia look.",
    values: {
      "theme.background_color": "#0a0e27",
      "theme.primary_color": "#fbbf24",
      "theme.accent_color": "#3b82f6",
      "theme.text_color": "#f0f5ff",
      "theme.font_display": '"Cormorant Garamond", Georgia, serif',
      "theme.font_body": '"Inter", system-ui, -apple-system, sans-serif',
      "theme.font_ar": '"Noto Kufi Arabic", "Arial Unicode MS", sans-serif',
      "theme.google_fonts_url":
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700" +
        "&family=Cormorant+Garamond:wght@500;600;700&family=Noto+Kufi+Arabic:wght@300;400;500;600;700" +
        "&display=swap",
      "theme.header_height_px": 64,
      "theme.content_max_width_px": 1180,
      "theme.corner_radius_px": 16,
    },
  },
  {
    id: "emerald-noir",
    name: "Emerald Noir",
    description: "Near-black emerald with antique gold and a crisp, architectural edge.",
    values: {
      "theme.background_color": "#071a16",
      "theme.primary_color": "#d4af37",
      "theme.accent_color": "#10b981",
      "theme.text_color": "#f2ede1",
      "theme.font_display": '"Playfair Display", Georgia, serif',
      "theme.font_body": '"Manrope", system-ui, -apple-system, sans-serif',
      "theme.font_ar": '"Noto Kufi Arabic", "Arial Unicode MS", sans-serif',
      "theme.google_fonts_url":
        "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700" +
        "&family=Playfair+Display:wght@500;600;700&family=Noto+Kufi+Arabic:wght@300;400;500;600;700" +
        "&display=swap",
      "theme.header_height_px": 68,
      "theme.content_max_width_px": 1180,
      "theme.corner_radius_px": 10,
    },
  },
  {
    id: "onyx-rose-gold",
    name: "Onyx & Rose Gold",
    description: "Near-black onyx, soft rose gold, and a hint of amethyst — softer, boutique feel.",
    values: {
      "theme.background_color": "#120d14",
      "theme.primary_color": "#e0b0a3",
      "theme.accent_color": "#a78bfa",
      "theme.text_color": "#f5eef0",
      "theme.font_display": '"Bodoni Moda", Georgia, serif',
      "theme.font_body": '"Inter", system-ui, -apple-system, sans-serif',
      "theme.font_ar": '"Noto Kufi Arabic", "Arial Unicode MS", sans-serif',
      "theme.google_fonts_url":
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700" +
        "&family=Bodoni+Moda:wght@500;600;700&family=Noto+Kufi+Arabic:wght@300;400;500;600;700" +
        "&display=swap",
      "theme.header_height_px": 64,
      "theme.content_max_width_px": 1180,
      "theme.corner_radius_px": 20,
    },
  },
  {
    id: "ember-pulse",
    name: "Ember Pulse",
    description: "Deep violet-black with a warm coral signature and an electric violet accent — bold, modern, voice-tech energy.",
    values: {
      "theme.background_color": "#0c0a16",
      "theme.primary_color": "#ff7a45",
      "theme.accent_color": "#a855f7",
      "theme.text_color": "#f4f0fa",
      "theme.font_display": '"Space Grotesk", system-ui, -apple-system, sans-serif',
      "theme.font_body": '"Inter", system-ui, -apple-system, sans-serif',
      "theme.font_ar": '"Noto Kufi Arabic", "Arial Unicode MS", sans-serif',
      "theme.google_fonts_url":
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700" +
        "&family=Space+Grotesk:wght@500;600;700&family=Noto+Kufi+Arabic:wght@300;400;500;600;700" +
        "&display=swap",
      "theme.header_height_px": 64,
      "theme.content_max_width_px": 1180,
      "theme.corner_radius_px": 18,
    },
  },
];

// Which of the 4 signature color fields identify a preset — used to
// detect whether the current form values match a known preset (so the
// dropdown reflects reality) or have been hand-edited since.
const SIGNATURE_KEYS = [
  "theme.background_color",
  "theme.primary_color",
  "theme.accent_color",
  "theme.text_color",
];

export function detectActivePreset(values) {
  for (const preset of THEME_PRESETS) {
    if (SIGNATURE_KEYS.every((k) => (values[k] || "").toLowerCase() === preset.values[k].toLowerCase())) {
      return preset.id;
    }
  }
  return null;
}
