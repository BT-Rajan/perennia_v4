// ──────────────────────────────────────────────────────────
// URL ↔ page mapping and per-page <head> tags for search engines and
// link previews. Presentation is untouched: the app still switches
// pages in-place (App.jsx); this only gives each page its own address
// and its own title/description/canonical — the same URLs
// backend/app/routers/public_seo.py lists in /sitemap.xml and
// backend/app/seo_render.py renders on the server.
//
// English (the default language) is at /<slug>, home at /; every other
// language is prefixed: /ar/<slug>, home at /ar/.
// ──────────────────────────────────────────────────────────

export const DEFAULT_LANG = "en";
const PREFIXED_LANGS = ["ar"];

function splitPath(pathname) {
  const parts = decodeURIComponent((pathname || "/").replace(/^\/+|\/+$/g, "")).split("/").filter(Boolean);
  const lang = PREFIXED_LANGS.includes(parts[0]) ? parts.shift() : null;
  return { lang, rest: parts };
}

export function pathForPage(id, lang = DEFAULT_LANG) {
  const prefix = lang && lang !== DEFAULT_LANG ? `/${lang}` : "";
  if (!id || id === "home" || id === "work") return prefix ? `${prefix}/` : "/";
  return `${prefix}/${encodeURIComponent(id)}`;
}

export function pageFromPath(pathname) {
  const { rest } = splitPath(pathname);
  return rest.length === 1 ? rest[0] : "home";
}

// The language a URL names: "ar" for /ar/…, the default for an
// unprefixed path.
export function langFromPath(pathname) {
  return splitPath(pathname).lang || DEFAULT_LANG;
}

// True when the path itself picks a language (/ar/…).
export function pathHasLang(pathname) {
  return splitPath(pathname).lang !== null;
}

// First real paragraph of a page's Markdown body, as plain text, for
// the meta description (headings, quotes, images, lists and the
// [[workflow]]/[[cta]] blocks are skipped).
export function describeMarkdown(markdown, max = 160) {
  const block = (markdown || "")
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .find((b) => b && !/^(#|>|!\[|\[\[|[-*]\s|\d+\.\s|-{3,})/.test(b));
  if (!block) return "";
  const text = block
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
  return text.length <= max ? text : `${text.slice(0, max - 1).replace(/\s+\S*$/, "")}…`;
}

function setMeta(selector, attr, value) {
  if (!value) return;
  const el = document.head.querySelector(selector);
  if (el) el.setAttribute(attr, value);
}

export function applyPageMeta({ title, description, path, alternates }) {
  const url = `${window.location.origin}${path}`;
  if (title) document.title = title;
  setMeta("#meta-description", "content", description);
  setMeta("link[rel='canonical']", "href", url);
  setMeta("meta[property='og:title']", "content", title);
  setMeta("meta[property='og:description']", "content", description);
  setMeta("meta[property='og:url']", "content", url);
  setMeta("meta[name='twitter:title']", "content", title);
  setMeta("meta[name='twitter:description']", "content", description);
  // Normally already absolute (the backend fills __SITE_URL__); this
  // covers `npm run dev`, where index.html is served unprocessed.
  const image = `${window.location.origin}/static/og-image.png`;
  setMeta("meta[property='og:image']", "content", image);
  setMeta("meta[name='twitter:image']", "content", image);
  // hreflang alternates: { en: "/about", ar: "/ar/about" }
  for (const [code, altPath] of Object.entries(alternates || {})) {
    setMeta(`link[rel='alternate'][hreflang='${code}']`, "href", `${window.location.origin}${altPath}`);
  }
}
