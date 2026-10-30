// ──────────────────────────────────────────────────────────
// Body copy for every content page. Each lives in its own Markdown
// file, src/content/<lang>/<slug>.md; the page's nav label, section
// summary and tagline live in src/content/pages.json. Adding a page
// is a new .md file per language plus a pages.json record — nothing
// here needs editing.
// ──────────────────────────────────────────────────────────
const MARKDOWN = import.meta.glob("../content/*/*.md", { query: "?raw", import: "default", eager: true });

// { en: { about: "…", … }, ar: { … } }
export const PAGE_CONTENT = {};
for (const [path, body] of Object.entries(MARKDOWN)) {
  const [, lang, slug] = path.match(/\/content\/([^/]+)\/([^/]+)\.md$/);
  (PAGE_CONTENT[lang] ??= {})[slug] = body;
}

// Footer-only legal pages. Always routable: if the live content API
// doesn't have them yet (seed_content.py not re-run), the bundled
// copies are used — see buildFromApi in siteContent.js.
export const LEGAL_PAGE_IDS = ["privacy", "terms"];
