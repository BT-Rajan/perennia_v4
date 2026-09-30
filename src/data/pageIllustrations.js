// ──────────────────────────────────────────────────────────
// Optional illustration banner shown between a content page's heading
// and its text (ContentPage.jsx), keyed by page slug. Kept out of the
// page's Markdown so it shows on existing installs without touching the
// admin-edited page text. Images are pre-flattened onto the card colour
// (see .content-illustration in ContentPage.css).
// ──────────────────────────────────────────────────────────

export const PAGE_ILLUSTRATIONS = {
  services: {
    src: "/static/illustrations/what-we-do.webp",
    srcSet: "/static/illustrations/what-we-do-992.webp 992w, /static/illustrations/what-we-do.webp 1983w",
    width: 1983,
    height: 620,
    alt: {
      en: "A team in Kuwait working together on a business dashboard connected to cloud, AI, data and automation.",
      ar: "فريق في الكويت يعمل معًا على لوحة معلومات أعمال متصلة بالسحابة والذكاء الاصطناعي والبيانات والأتمتة.",
    },
  },
};
