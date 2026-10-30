import { useLang } from "../../context/LangContext.jsx";
import { pageLinkProps } from "../../seo/pageLink.js";
import "./SiteFooter.css";

/**
 * The one footer every page renders (Home, content pages, Contact):
 * the brand line, the service pages and case studies, the same
 * destinations as the header nav, configured contact details and the
 * legal links. All are real links (crawlable; a click still switches
 * pages in place) — the same footer the server renders for crawlers in
 * backend/app/seo_render.py.
 * No booking button here — the header and the page above already carry
 * it. `onNavigate` is the same handler the page passes to TopBar.
 */
// Keyword service pages, as in backend/app/seo_render.py SERVICE_PAGES.
const SERVICE_PAGES = ["software-development", "ai-implementation", "it-strategy"];
const CASE_STUDIES_URL = { en: "https://apps.perennia.org/", ar: "https://apps.perennia.org/ar/" };

export default function SiteFooter({ onNavigate }) {
  const { nav, copy, branding, contact, pages, lang } = useLang();
  const services = SERVICE_PAGES.filter((id) => pages?.[id]);
  const common = copy.common;
  const tagline = copy.home.eyebrow;
  const whatsappDigits = (contact?.whatsappNumber || "").replace(/\D/g, "");

  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-brand">
          <p className="site-footer-name">{branding.siteName}</p>
          {tagline && <p className="site-footer-tagline">{tagline}</p>}
        </div>

        <nav className="site-footer-col" aria-label={common.footerServices}>
          <h2>{common.footerServices}</h2>
          <ul>
            {services.map((id) => (
              <li key={id}><a {...pageLinkProps(id, lang, onNavigate)}>{pages[id].navLabel}</a></li>
            ))}
            <li><a href={CASE_STUDIES_URL[lang] ?? CASE_STUDIES_URL.en}>{common.footerCaseStudies}</a></li>
          </ul>
        </nav>

        <nav className="site-footer-col" aria-label={common.footerExplore}>
          <h2>{common.footerExplore}</h2>
          <ul className="site-footer-explore">
            {nav.map((item) => (
              <li key={item.id}><a {...pageLinkProps(item.id, lang, onNavigate)}>{item.label}</a></li>
            ))}
          </ul>
        </nav>

        <div className="site-footer-col">
          <h2>{common.footerContact}</h2>
          <ul>
            {contact?.email && <li><a href={`mailto:${contact.email}`}>{contact.email}</a></li>}
            {contact?.phone && <li><a href={`tel:${contact.phone.replace(/[^\d+]/g, "")}`} dir="ltr">{contact.phone}</a></li>}
            {whatsappDigits && (
              <li><a href={`https://wa.me/${whatsappDigits}`} target="_blank" rel="noopener noreferrer">WhatsApp</a></li>
            )}
          </ul>
        </div>
      </div>
      <p className="site-footer-legal">
        © {new Date().getFullYear()} {branding.siteName}. {common.footerRights}
        {[["privacy", common.footerPrivacy], ["terms", common.footerTerms]].map(([id, label]) => (
          <a key={id} className="site-footer-legal-link" {...pageLinkProps(id, lang, onNavigate)}>{label}</a>
        ))}
      </p>
    </footer>
  );
}
