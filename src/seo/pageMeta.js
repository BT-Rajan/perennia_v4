// ──────────────────────────────────────────────────────────
// URL ↔ page mapping and per-page <head> tags for search engines and
// link previews. Presentation is untouched: the app still switches
// pages in-place (App.jsx); this only gives each page its own address
// (/<slug>, home at /) and its own title/description/canonical — the
// same URLs backend/app/routers/public_seo.py lists in /sitemap.xml.
// ──────────────────────────────────────────────────────────

export function pathForPage(id) {
  return !id || id === "home" || id === "work" ? "/" : `/${encodeURIComponent(id)}`;
}

export function pageFromPath(pathname) {
  const slug = decodeURIComponent((pathname || "/").replace(/^\/+|\/+$/g, ""));
  return slug && !slug.includes("/") ? slug : "home";
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

export function applyPageMeta({ title, description, path }) {
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
}
