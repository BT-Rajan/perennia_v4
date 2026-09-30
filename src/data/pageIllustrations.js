// ──────────────────────────────────────────────────────────
// Optional illustration per content page (ContentPage.jsx), keyed by
// page slug. Kept out of the page's Markdown so it shows on existing
// installs without touching the admin-edited page text. Images are
// cropped to their subject and flattened onto the light card colour
// (see .content-illustration in ContentPage.css).
//
// placement:
//   "banner" — full content width, between the heading and the text
//              (wide artwork)
//   "aside"  — beside the text on desktop, filling the column the
//              readable-width text leaves free; above the text on
//              phones. `portrait` keeps a tall image small on phones.
// ──────────────────────────────────────────────────────────

export const PAGE_ILLUSTRATIONS = {
  services: {
    placement: "banner",
    src: "/static/illustrations/what-we-do.webp",
    srcSet: "/static/illustrations/what-we-do-992.webp 992w, /static/illustrations/what-we-do.webp 1983w",
    width: 1983,
    height: 620,
    alt: {
      en: "A team in Kuwait working together on a business dashboard connected to cloud, AI, data and automation.",
      ar: "فريق في الكويت يعمل معًا على لوحة معلومات أعمال متصلة بالسحابة والذكاء الاصطناعي والبيانات والأتمتة.",
    },
  },
  products: {
    placement: "aside",
    portrait: true,
    src: "/static/illustrations/products.webp",
    srcSet: "/static/illustrations/products-301.webp 301w, /static/illustrations/products.webp 603w",
    width: 603,
    height: 793,
    alt: {
      en: "Building blocks labelled Cloud, Database, CRM, Software, ERP, AI, Security and Integration.",
      ar: "مكعبات بناء تحمل أسماء السحابة وقاعدة البيانات وإدارة علاقات العملاء والبرمجيات وتخطيط موارد المؤسسات والذكاء الاصطناعي والأمن والتكامل.",
    },
  },
  labs: {
    placement: "aside",
    src: "/static/illustrations/labs.webp",
    srcSet: "/static/illustrations/labs-581.webp 581w, /static/illustrations/labs.webp 1163w",
    width: 1163,
    height: 725,
    alt: {
      en: "A research team exploring ideas around a glowing light bulb, with data, AI and lab equipment.",
      ar: "فريق بحثي يستكشف الأفكار حول مصباح مضيء، مع البيانات والذكاء الاصطناعي ومعدات المختبر.",
    },
  },
};
