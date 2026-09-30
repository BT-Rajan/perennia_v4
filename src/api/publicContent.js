// ──────────────────────────────────────────────────────────
// Public, unauthenticated reads from the new backend (see
// ../../backend/app/routers/public_config.py and public_content.py).
// Same tryFetch-with-graceful-fallback pattern as the rest of this
// file: if the backend isn't running (e.g. plain `npm run dev` with no
// backend started), every call here resolves to null and callers fall
// back to bundled defaults — see src/data/siteContent.js.
// ──────────────────────────────────────────────────────────
import { tryFetch } from "./client.js";

export async function fetchPublicConfig() {
  return await tryFetch("config/public");
}

export async function fetchContentPages() {
  return await tryFetch("content/pages");
}

export async function fetchFaqItems() {
  return await tryFetch("content/faq");
}
