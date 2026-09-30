// ──────────────────────────────────────────────────────────
// Single place that knows how to turn (a) the backend's public config
// + content API responses, or (b) the bundled fallback data, into the
// exact shape LangContext hands to every component: { copy, nav,
// sections, faq, pages }, each keyed by language.
//
// Components never import COPY/FAQ/NAV/SECTIONS or PAGE_META/
// PAGE_CONTENT directly anymore — only useLang() — so swapping how
// content is sourced never touches component code again.
// ──────────────────────────────────────────────────────────
import { BRAND, COPY, FAQ, NAV, SECTIONS } from "./content.js";
import { PAGE_CONTENT, PAGE_META } from "./pages.js";
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

// ---- Building the unified shape from the BUNDLED FALLBACK ----------

function localCopyForLang(lang) {
  const c = COPY[lang];
  return {
    home: c.home,
    chat: c.chat,
    common: c.common,
    booking: {
      ...c.booking,
      // already functions in the local fallback — used as-is.
    },
  };
}

function buildFromLocalFallback(supportedLanguages) {
  const copy = {}, nav = {}, sections = {}, faq = {}, pages = {};
  for (const lang of supportedLanguages) {
    copy[lang] = localCopyForLang(lang);
    nav[lang] = withWorkNav(NAV[lang], lang);
    sections[lang] = SECTIONS[lang];
    faq[lang] = FAQ[lang];
    pages[lang] = Object.fromEntries(
      Object.keys(PAGE_META[lang]).map((slug) => [
        slug,
        { ...PAGE_META[lang][slug], body: PAGE_CONTENT[lang][slug] },
      ])
    );
  }
  // No bundled fallback buttons — the fallback tagline string covers
  // that spot until the admin configures real buttons via the API.
  return { copy, nav, sections, faq, pages, heroButtons: [] };
}

// ---- Building the unified shape from the BACKEND API ----------------

function apiCopyForLang(copyBlobs, lang) {
  const home = toCamel(copyBlobs["copy.home"]?.[lang] ?? {});
  const chat = toCamel(copyBlobs["copy.chat"]?.[lang] ?? {});
  const common = toCamel(copyBlobs["copy.common"]?.[lang] ?? {});
  const bookingRaw = toCamel(copyBlobs["copy.booking"]?.[lang] ?? {});
  // `errors` keys are backend error codes (e.g. "slot_unavailable"),
  // looked up verbatim against booking_service.py's return values —
  // NOT field names, so they must stay snake_case. camelCasing them
  // above (toCamel is recursive) would silently break every lookup,
  // since result.error from the API is always snake_case.
  const rawErrors = copyBlobs["copy.booking"]?.[lang]?.errors ?? {};

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
        line1: p.translations[lang]?.tagline_line1 ?? "",
        line2: p.translations[lang]?.tagline_line2 ?? "",
        sub: p.translations[lang]?.tagline_sub ?? "",
        body: p.translations[lang]?.body_markdown ?? "",
      }])
    );

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

export function buildFallbackSite() {
  const supportedLanguages = Object.keys(COPY);
  return {
    source: "fallback",
    supportedLanguages,
    defaultLanguage: "en",
    theme: FALLBACK_THEME,
    features: { bookingEnabled: true, chatEnabled: true, whatsappWidgetEnabled: false },
    contact: FALLBACK_CONTACT,
    branding: {
      siteNameByLang: { en: BRAND.name, ar: BRAND.wordmarkAr },
      logoUrl: "/static/logo.svg",
      logoScale: 1,
      faviconUrl: "/favicon.svg",
      metaDescriptionByLang: {
        en: "Perennia — a technology partner for GCC businesses. Practical AI. Affordable Innovation.",
        ar: "بيرينيا — شريك تقني للشركات في دول الخليج. ذكاء اصطناعي عملي. ابتكار في المتناول.",
      },
      chatAvatarUrl: "",
    },
    ...buildFromLocalFallback(supportedLanguages),
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

const FALLBACK_CONTACT = { email: "", phone: "", whatsappNumber: "", addressByLang: { en: "", ar: "" } };

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

  const supportedLanguages = publicConfig?.["locale.supported_languages"] ?? Object.keys(COPY);
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
    features: haveFullApiData
      ? apiFeatures(publicConfig)
      : { bookingEnabled: true, chatEnabled: true, whatsappWidgetEnabled: false },
    contact: haveFullApiData ? apiContact(publicConfig) : FALLBACK_CONTACT,
    branding: {
      siteNameByLang: publicConfig?.["branding.site_name"] ?? { en: BRAND.name, ar: BRAND.wordmarkAr },
      logoUrl: publicConfig?.["branding.logo_url"] ?? "/static/logo.svg",
      logoScale: publicConfig?.["branding.logo_scale"] ?? 1,
      faviconUrl: publicConfig?.["branding.favicon_url"] ?? "/favicon.svg",
      metaDescriptionByLang: publicConfig?.["branding.meta_description"] ?? { en: "", ar: "" },
      chatAvatarUrl: publicConfig?.["chat.avatar_url"] ?? "",
    },
    ...site,
  };
}

export { dirFor };
