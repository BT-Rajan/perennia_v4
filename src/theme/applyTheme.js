// ──────────────────────────────────────────────────────────
// Applies theme + branding settings to the live document. This is
// what turns the *static* fallback values baked into tokens.css and
// index.html into genuinely runtime-configurable ones: every value
// here can come from the backend (theme.* / branding.* in
// backend/app/settings_registry.py) and, when it does, silently
// overrides the CSS/HTML defaults with no rebuild required.
// ──────────────────────────────────────────────────────────

const CSS_VAR_MAP = {
  backgroundColor: "--brand-bg",
  primaryColor: "--brand-primary",
  accentColor: "--brand-accent",
  textColor: "--brand-text",
  fontDisplay: "--font-display",
  fontBody: "--font-body",
  fontAr: "--font-ar",
};

const PX_VAR_MAP = {
  headerHeightPx: "--header-h",
  contentMaxWidthPx: "--content-max",
  cornerRadiusPx: "--radius-md",
};

const MS_VAR_MAP = {
  headlineDissolveMs: "--headline-dissolve-ms",
};

/**
 * @param {object} theme - camelCase theme fields (see siteContent.js)
 * @param {{siteName: string, faviconUrl: string, metaDescription: string}} branding - already resolved to the current language
 */
export function applyTheme(theme, branding) {
  const root = document.documentElement.style;

  for (const [key, cssVar] of Object.entries(CSS_VAR_MAP)) {
    if (theme[key]) root.setProperty(cssVar, theme[key]);
  }
  for (const [key, cssVar] of Object.entries(PX_VAR_MAP)) {
    if (theme[key] != null) root.setProperty(cssVar, `${theme[key]}px`);
  }
  for (const [key, cssVar] of Object.entries(MS_VAR_MAP)) {
    if (theme[key] != null) root.setProperty(cssVar, `${theme[key]}ms`);
  }

  if (theme.googleFontsUrl) {
    const link = document.getElementById("google-fonts-link");
    if (link && link.href !== theme.googleFontsUrl) link.href = theme.googleFontsUrl;
  }

  if (branding.siteName) document.title = branding.siteName;

  if (branding.faviconUrl) {
    const favicon = document.getElementById("favicon-link");
    if (favicon) favicon.href = branding.faviconUrl;
  }

  if (branding.metaDescription) {
    const meta = document.getElementById("meta-description");
    if (meta) meta.content = branding.metaDescription;
  }

  const themeColorMeta = document.getElementById("theme-color-meta");
  if (themeColorMeta && theme.backgroundColor) themeColorMeta.content = theme.backgroundColor;

  // Whole-page style system (see src/styles/themeVariants.css) — one
  // attribute per pass, each independently togglable. Falls back to
  // the value that reproduces today's actual appearance (see the
  // comment on theme.surface_style/theme.button_style in
  // backend/app/settings_registry.py), so a site that never touches
  // these looks unchanged.
  document.documentElement.dataset.surfaceStyle = theme.surfaceStyle || "glass";
  document.documentElement.dataset.buttonStyle = theme.buttonStyle || "default";
  document.documentElement.dataset.typeScale = theme.typeScale || "standard";
  document.documentElement.dataset.headingCase = theme.headingCase || "as-is";
  document.documentElement.dataset.backgroundStyle = theme.backgroundStyle || "grid";
  document.documentElement.dataset.backgroundIntensity = theme.backgroundIntensity || "subtle";
  document.documentElement.dataset.density = theme.density || "comfortable";
  document.documentElement.dataset.sectionRhythm = theme.sectionRhythm || "standard";
}
