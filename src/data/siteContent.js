// ──────────────────────────────────────────────────────────
// Single place that knows how to turn (a) the backend's public config
// + content API responses, or (b) the bundled fallback data, into the
// exact shape LangContext hands to every component: { copy, nav,
// sections, faq, pages }, each keyed by language.
//
// Both go through buildFromApi: the bundled data (src/content/*.json
// and *.md) is first shaped exactly like the API's responses, so there
// is one code path and the two can't render differently. Components
// read only useLang() and never import content modules directly.
// ──────────────────────────────────────────────────────────
import { BRAND, FAQ_ITEMS, PAGE_RECORDS, SITE_COPY } from "./content.js";
import { LEGAL_PAGE_IDS, PAGE_CONTENT } from "./pages.js";
import { fetchContentPages, fetchFaqItems, fetchPublicConfig } from "../api/publicContent.js";

const RTL_LANGS = new Set(["ar", "he", "fa", "ur"]);

function dirFor(lang) {
  return RTL_LANGS.has(lang) ? "rtl" : "ltr";
}

// Backend copy blobs use snake_case (matches Python convention);
// components use camelCase (matches this codebase's JS convention).
// One small recursive converter keeps both sides idiomatic instead of
// forcing one language's naming convention onto the other.
function toCamel(value) {
  if (Array.isArray(value)) return value.map(toCamel);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k.replace(/_([a-z])/g, (_, c) => c.toUpperCase()), toCamel(v)])
    );
  }
  return value;
}

// "Work" isn't a content page: it jumps to the homepage "Our work"
// section (see App.jsx navigate), so the portfolio lives in one place.
// Injected into every nav — API-driven or fallback — right after
// Solutions ("services"), or first if that page is missing.
const WORK_NAV_LABEL = { en: "Work", ar: "أعمالنا" };
function withWorkNav(items, lang) {
  const work = { id: "work", label: WORK_NAV_LABEL[lang] ?? WORK_NAV_LABEL.en };
  const rest = items.filter((i) => i.id !== "work");
  const at = rest.findIndex((i) => i.id === "services");
  return at === -1 ? [work, ...rest] : [...rest.slice(0, at + 1), work, ...rest.slice(at + 1)];
}

function fillTemplate(template, vars) {
  return Object.entries(vars).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, v), template ?? "");
}

// ---- Bundled content, in the API's shape -------------------------

const COPY_BLOBS = { home: "copy.home", chat: "copy.chat", common: "copy.common", booking: "copy.booking" };

const BUNDLED_CONFIG = Object.fromEntries(
  Object.entries(COPY_BLOBS).map(([blob, key]) => [key, SITE_COPY[blob]])
);

// Same fields as GET /api/public/content/pages: order from pages.json.
const BUNDLED_PAGES = PAGE_RECORDS.map(({ slug, show_in_nav, ...translations }, order) => ({
  slug,
  order,
  show_in_nav,
  translations: Object.fromEntries(
    Object.entries(translations).map(([lang, fields]) => [
      lang,
      { ...fields, body_markdown: PAGE_CONTENT[lang]?.[slug] ?? "" },
    ])
  ),
}));

const BUNDLED_FAQ = FAQ_ITEMS.map((translations) => ({ translations }));

const BUNDLED_LANGUAGES = Object.keys(SITE_COPY.home);

function buildFromLocalFallback(supportedLanguages) {
  return buildFromApi(BUNDLED_CONFIG, BUNDLED_PAGES, BUNDLED_FAQ, supportedLanguages);
}

// Per-field fallback: an admin-saved copy blob that predates a newer
// key (or leaves one out) still gets the bundled text for that key,
// instead of a blank label or an undefined validation message.
function withBundled(bundled, live) {
  const out = { ...bundled };
  for (const [k, v] of Object.entries(live ?? {})) {
    if (v !== null && v !== undefined) out[k] = v;
  }
  return out;
}

function copyBlob(copyBlobs, key, lang) {
  const bundled = BUNDLED_CONFIG[key] ?? {};
  return withBundled(bundled[lang] ?? bundled.en, copyBlobs[key]?.[lang]);
}

// ---- Building the unified shape from the BACKEND API ----------------

function apiCopyForLang(copyBlobs, lang) {
  const home = toCamel(copyBlob(copyBlobs, "copy.home", lang));
  const chat = toCamel(copyBlob(copyBlobs, "copy.chat", lang));
  const common = toCamel(copyBlob(copyBlobs, "copy.common", lang));
  const bookingBlob = copyBlob(copyBlobs, "copy.booking", lang);
  const bookingRaw = toCamel(bookingBlob);
  // `errors` keys are backend error codes (e.g. "slot_unavailable"),
  // looked up verbatim against booking_service.py's return values —
  // NOT field names, so they must stay snake_case. camelCasing them
  // above (toCamel is recursive) would silently break every lookup,
  // since result.error from the API is always snake_case.
  const bundledErrors = (BUNDLED_CONFIG["copy.booking"][lang] ?? BUNDLED_CONFIG["copy.booking"].en).errors;
  const rawErrors = withBundled(bundledErrors, bookingBlob.errors);

  return {
    home,
    chat,
    common,
    booking: {
      ...bookingRaw,
      errors: rawErrors,
      // Backend stores these as {id}/{date}/{time} template strings
      // (functions aren't JSON-serializable); rehydrate them into the
      // callables every booking component already expects.
      successNew: (id) => fillTemplate(bookingRaw.successNew, { id }),
      successReschedule: (date, time) => fillTemplate(bookingRaw.successReschedule, { date, time }),
      successCancel: bookingRaw.successCancel,
    },
  };
}

function buildFromApi(publicConfig, contentPages, faqItems, supportedLanguages) {
  const visiblePages = [...contentPages].sort((a, b) => a.order - b.order);
  const navPages = visiblePages.filter((p) => p.show_in_nav);

  const copy = {}, nav = {}, sections = {}, faq = {}, pages = {};
  for (const lang of supportedLanguages) {
    copy[lang] = apiCopyForLang(publicConfig, lang);

    nav[lang] = withWorkNav(navPages.map((p) => ({ id: p.slug, label: p.translations[lang]?.nav_label ?? p.slug })), lang);

    sections[lang] = Object.fromEntries(
      navPages.map((p) => [p.slug, {
        title: p.translations[lang]?.section_title ?? "",
        body: p.translations[lang]?.section_body ?? "",
      }])
    );

    pages[lang] = Object.fromEntries(
      visiblePages.map((p) => [p.slug, {
        navLabel: p.translations[lang]?.nav_label ?? p.slug,
        title: p.translations[lang]?.section_title ?? "",
        summary: p.translations[lang]?.section_body ?? "",
        seoTitle: p.translations[lang]?.seo_title ?? "",
        seoDescription: p.translations[lang]?.seo_description ?? "",
        line1: p.translations[lang]?.tagline_line1 ?? "",
        line2: p.translations[lang]?.tagline_line2 ?? "",
        sub: p.translations[lang]?.tagline_sub ?? "",
        body: p.translations[lang]?.body_markdown ?? "",
      }])
    );
    // Privacy/Terms must always resolve (Google's OAuth review links to
    // them) — fall back to the bundled copy until the DB has its own.
    for (const slug of LEGAL_PAGE_IDS) {
      const bundled = BUNDLED_PAGES.find((p) => p.slug === slug)?.translations[lang];
      if (!pages[lang][slug] && bundled) {
        pages[lang][slug] = {
          navLabel: bundled.nav_label, title: bundled.section_title, summary: bundled.section_body,
          seoTitle: bundled.seo_title ?? "", seoDescription: bundled.seo_description ?? "",
          line1: bundled.tagline_line1, line2: bundled.tagline_line2, sub: bundled.tagline_sub, body: bundled.body_markdown,
        };
      }
    }

    faq[lang] = faqItems.map((item) => ({
      q: item.translations[lang]?.q ?? "",
      a: item.translations[lang]?.a ?? "",
    }));
  }

  // Admin-provisioned home hero buttons — shared across languages (only
  // each button's label is per-language); validated again on the way in
  // since this is rendered straight into <a href>.
  const heroButtons = (toCamel(publicConfig["copy.home_hero_buttons"]) ?? [])
    .filter((b) => b && typeof b.url === "string" && isSafeHref(b.url) && b.label && typeof b.label === "object")
    .slice(0, 8);

  return { copy, nav, sections, faq, pages, heroButtons };
}

// Only allow schemes/paths an <a href> can safely carry — blocks
// `javascript:`/`data:` etc. even though the value comes from an
// authenticated admin, since it's still rendered straight into the DOM.
export function isSafeHref(url) {
  return typeof url === "string" && /^(https?:\/\/|\/(?!\/))/.test(url.trim());
}

// Fallback theme — mirrors tokens.css's own literal defaults exactly,
// so there's no visual "pop" if these get overridden a moment later
// once the live backend theme arrives.
// Must equal the backend's theme.* defaults (settings_registry.py), the
// tokens.css literals and the font stylesheet preloaded in index.html:
// this is what the first render applies, so any drift here makes every
// page load swap stylesheets (downloading fonts it never uses) and
// flash the wrong colours before the live theme arrives.
const FALLBACK_THEME = {
  backgroundColor: "#07060a",
  primaryColor: "#c9a84c",
  accentColor: "#e8c96a",
  textColor: "#f5f0e8",
  fontDisplay: '"Cormorant Garamond", Georgia, serif',
  fontBody: '"Syne", system-ui, -apple-system, sans-serif',
  fontAr: '"Noto Kufi Arabic", "Arial Unicode MS", sans-serif',
  googleFontsUrl:
    "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700" +
    "&family=Syne:wght@500;600;700;800&family=Noto+Kufi+Arabic:wght@300;400;500;600;700&display=swap",
  headerHeightPx: 64,
  contentMaxWidthPx: 1180,
  cornerRadiusPx: 10,
  heroAutoAdvanceSeconds: 7,
  // Falls back to "classic"/"ripple-gradient" — the site's original/
  // only homepage layout and headline treatment before these settings
  // existed — so an unset or unrecognized value here can never
  // regress an existing deployment. See Hero.jsx / HeroShared.jsx.
  layoutTemplate: "classic",
  headlineStyle: "ripple-gradient",
  // Homepage headline pacing — see theme.headline_typing_speed_cps /
  // theme.headline_dissolve_ms in backend/app/settings_registry.py.
  // 5 cps matches the site's original (pre-setting) hardcoded speed.
  headlineTypingSpeedCps: 5,
  headlineDissolveMs: 2500,
  surfaceStyle: "glass",
  buttonStyle: "default",
  typeScale: "standard",
  headingCase: "as-is",
  backgroundStyle: "grid",
  backgroundIntensity: "subtle",
  density: "comfortable",
  sectionRhythm: "standard",
};

const FALLBACK_FEATURES = { bookingEnabled: true, chatEnabled: true, whatsappWidgetEnabled: false };

const FALLBACK_BRANDING = {
  siteNameByLang: { en: BRAND.name, ar: BRAND.wordmarkAr },
  logoUrl: "/static/perennia-logo.png",
  logoScale: 1,
  faviconUrl: "/favicon.svg",
  metaDescriptionByLang: {
    en: "Perennia — a technology partner for GCC businesses. Practical AI. Affordable Innovation.",
    ar: "بيرينيا — شريك تقني للشركات في دول الخليج. ذكاء اصطناعي عملي. ابتكار في المتناول.",
  },
  chatAvatarUrl: "",
};

export function buildFallbackSite() {
  return {
    source: "fallback",
    supportedLanguages: BUNDLED_LANGUAGES,
    defaultLanguage: "en",
    theme: FALLBACK_THEME,
    features: FALLBACK_FEATURES,
    contact: FALLBACK_CONTACT,
    branding: FALLBACK_BRANDING,
    ...buildFromLocalFallback(BUNDLED_LANGUAGES),
  };
}

function apiFeatures(publicConfig) {
  return {
    bookingEnabled: publicConfig["features.booking_enabled"],
    chatEnabled: publicConfig["features.chat_enabled"],
    whatsappWidgetEnabled: publicConfig["features.whatsapp_widget_enabled"],
  };
}

// contact.address is i18n ({en, ar}); email/phone/whatsapp_number are
// plain scalars in the settings registry (see settings_registry.py).
function apiContact(publicConfig) {
  return {
    email: publicConfig["contact.email"] ?? "",
    phone: publicConfig["contact.phone"] ?? "",
    whatsappNumber: publicConfig["contact.whatsapp_number"] ?? "",
    addressByLang: publicConfig["contact.address"] ?? { en: "", ar: "" },
  };
}

const FALLBACK_CONTACT = { email: "", phone: "+965 9933 1344", whatsappNumber: "", addressByLang: { en: "", ar: "" } };

function apiTheme(publicConfig) {
  return {
    backgroundColor: publicConfig["theme.background_color"],
    primaryColor: publicConfig["theme.primary_color"],
    accentColor: publicConfig["theme.accent_color"],
    textColor: publicConfig["theme.text_color"],
    fontDisplay: publicConfig["theme.font_display"],
    fontBody: publicConfig["theme.font_body"],
    fontAr: publicConfig["theme.font_ar"],
    googleFontsUrl: publicConfig["theme.google_fonts_url"],
    headerHeightPx: publicConfig["theme.header_height_px"],
    contentMaxWidthPx: publicConfig["theme.content_max_width_px"],
    cornerRadiusPx: publicConfig["theme.corner_radius_px"],
    heroAutoAdvanceSeconds: publicConfig["theme.hero_auto_advance_seconds"],
    // See FALLBACK_THEME above on why these fallbacks are safe.
    layoutTemplate: publicConfig["theme.layout_template"] || "classic",
    headlineStyle: publicConfig["theme.headline_style"] || "ripple-gradient",
    headlineTypingSpeedCps: publicConfig["theme.headline_typing_speed_cps"] || 5,
    headlineDissolveMs: publicConfig["theme.headline_dissolve_ms"] || 2500,
    surfaceStyle: publicConfig["theme.surface_style"] || "glass",
    buttonStyle: publicConfig["theme.button_style"] || "default",
    typeScale: publicConfig["theme.type_scale"] || "standard",
    headingCase: publicConfig["theme.heading_case"] || "as-is",
    backgroundStyle: publicConfig["theme.background_style"] || "grid",
    backgroundIntensity: publicConfig["theme.background_intensity"] || "subtle",
    density: publicConfig["theme.density"] || "comfortable",
    sectionRhythm: publicConfig["theme.section_rhythm"] || "standard",
  };
}

/**
 * Loads everything needed to render the site, preferring the live
 * backend and falling back to bundled content per-piece if the
 * backend (or a specific call) is unreachable — so a partial outage
 * degrades gracefully instead of blanking the whole site.
 */
export async function loadSiteContent() {
  const [publicConfig, contentPages, faqItems] = await Promise.all([
    fetchPublicConfig(),
    fetchContentPages(),
    fetchFaqItems(),
  ]);

  const supportedLanguages = publicConfig?.["locale.supported_languages"] ?? BUNDLED_LANGUAGES;
  const defaultLanguage = publicConfig?.["locale.default_language"] ?? "en";

  const haveFullApiData = publicConfig && contentPages && faqItems;
  const site = haveFullApiData
    ? buildFromApi(publicConfig, contentPages, faqItems, supportedLanguages)
    : buildFromLocalFallback(supportedLanguages);

  return {
    source: haveFullApiData ? "api" : "fallback",
    supportedLanguages,
    defaultLanguage,
    theme: haveFullApiData ? apiTheme(publicConfig) : FALLBACK_THEME,
    features: haveFullApiData ? apiFeatures(publicConfig) : FALLBACK_FEATURES,
    contact: haveFullApiData ? apiContact(publicConfig) : FALLBACK_CONTACT,
    branding: {
      siteNameByLang: publicConfig?.["branding.site_name"] ?? FALLBACK_BRANDING.siteNameByLang,
      logoUrl: publicConfig?.["branding.logo_url"] ?? FALLBACK_BRANDING.logoUrl,
      logoScale: publicConfig?.["branding.logo_scale"] ?? FALLBACK_BRANDING.logoScale,
      faviconUrl: publicConfig?.["branding.favicon_url"] ?? FALLBACK_BRANDING.faviconUrl,
      metaDescriptionByLang: publicConfig?.["branding.meta_description"] ?? { en: "", ar: "" },
      chatAvatarUrl: publicConfig?.["chat.avatar_url"] ?? FALLBACK_BRANDING.chatAvatarUrl,
    },
    ...site,
  };
}

export { dirFor };
