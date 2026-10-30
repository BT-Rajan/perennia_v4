// ──────────────────────────────────────────────────────────
// Bundled site content — what renders before (or without) the backend.
//
// The copy, page records and FAQ live as JSON under src/content/ so the
// frontend and backend share one source: the backend's copy.* setting
// defaults (app/settings_registry.py) and the content seed
// (scripts/seed_content.py) read the same files. Keys are snake_case,
// the API's shape; siteContent.js converts them for components.
// ──────────────────────────────────────────────────────────
import SITE_COPY from "../content/site-copy.json";
import PAGE_RECORDS from "../content/pages.json";
import FAQ_ITEMS from "../content/faq.json";

export { SITE_COPY, PAGE_RECORDS, FAQ_ITEMS };

export const BRAND = {
  name: "Perennia",
  wordmarkAr: "بيرينيا",
};
