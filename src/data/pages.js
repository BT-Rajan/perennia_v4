// ──────────────────────────────────────────────────────────
// Content for the four standalone pages (About / Products /
// Services / Contact). Each page's body copy lives in its own
// Markdown file under src/content/<lang>/<page>.md — edit those
// files to change what's on the page; no component changes
// needed. `?raw` tells Vite to import the file as a plain string
// instead of trying to process it as a module.
// ──────────────────────────────────────────────────────────
import aboutEn from "../content/en/about.md?raw";
import productsEn from "../content/en/products.md?raw";
import servicesEn from "../content/en/services.md?raw";
import contactEn from "../content/en/contact.md?raw";
import aboutAr from "../content/ar/about.md?raw";
import productsAr from "../content/ar/products.md?raw";
import servicesAr from "../content/ar/services.md?raw";
import contactAr from "../content/ar/contact.md?raw";
import jdkErpEn from "../content/en/jdk-factory-erp.md?raw";
import jdkErpAr from "../content/ar/jdk-factory-erp.md?raw";

export const PAGE_CONTENT = {
  en: { about: aboutEn, products: productsEn, services: servicesEn, contact: contactEn, "jdk-factory-erp": jdkErpEn },
  ar: { about: aboutAr, products: productsAr, services: servicesAr, contact: contactAr, "jdk-factory-erp": jdkErpAr },
};

// Header tagline shown above each page's content shell — mirrors the
// chat page's taglineLine1 / taglineLine2 / sub treatment so every
// page in the app reads as part of the same family.
export const PAGE_META = {
  en: {
    about: { line1: "Who We ", line2: "Are", sub: "AI-POWERED TECHNOLOGY & INNOVATION" },
    products: { line1: "What We ", line2: "Build", sub: "PRODUCTS & PLATFORMS" },
    services: { line1: "How We ", line2: "Work", sub: "CONSULTING & ENGINEERING" },
    contact: { line1: "Let's ", line2: "Talk", sub: "GET IN TOUCH" },
    // Case study — reached from the homepage teaser, not the top nav.
    "jdk-factory-erp": { line1: "JDK Factory ", line2: "ERP", sub: "CASE STUDY · MANUFACTURING" },
  },
  ar: {
    about: { line1: "من ", line2: "نحن", sub: "تقنية وابتكار مدعومان بالذكاء الاصطناعي" },
    products: { line1: "ماذا ", line2: "نبني", sub: "المنتجات والمنصات" },
    services: { line1: "كيف ", line2: "نعمل", sub: "استشارات وهندسة" },
    contact: { line1: "لنتحدث", line2: "", sub: "تواصل معنا" },
    "jdk-factory-erp": { line1: "نظام ERP ", line2: "لمصنع JDK", sub: "دراسة حالة · التصنيع" },
  },
};
