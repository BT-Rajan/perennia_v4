import { useLang } from "../../context/LangContext.jsx";
import { pathForPage } from "../../seo/pageMeta.js";
import "./SiteFooter.css";

/**
 * The one footer every page renders (Home, content pages, Contact):
 * the brand line, the same destinations as the header nav (so Solutions,
 * Work, Products, Labs, About and Contact are always reachable from the
 * bottom of a page), configured contact details and the legal links.
 * No booking button here — the header and the page above already carry
 * it. `onNavigate` is the same handler the page passes to TopBar.
 */
export default function SiteFooter({ onNavigate }) {
  const { nav, copy, branding, contact } = useLang();
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

        <nav className="site-footer-col" aria-label={common.footerExplore}>
          <h2>{common.footerExplore}</h2>
          <ul className="site-footer-explore">
            {nav.map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => onNavigate?.(item.id)}>{item.label}</button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="site-footer-col">
          <h2>{common.footerContact}</h2>
          <ul>
            {contact?.email && <li><a href={`mailto:${contact.email}`}>{contact.email}</a></li>}
            {contact?.phone && <li><a href={`tel:${contact.phone}`}>{contact.phone}</a></li>}
            {whatsappDigits && (
              <li><a href={`https://wa.me/${whatsappDigits}`} target="_blank" rel="noopener noreferrer">WhatsApp</a></li>
            )}
          </ul>
        </div>
      </div>
      <p className="site-footer-legal">
        © {new Date().getFullYear()} {branding.siteName}. {common.footerRights}
        {[["privacy", common.footerPrivacy], ["terms", common.footerTerms]].map(([id, label]) => (
          // Real hrefs so the pages are crawlable and openable in a new
          // tab; a plain click still switches pages in place.
          <a
            key={id}
            className="site-footer-legal-link"
            href={pathForPage(id)}
            onClick={(e) => {
              if (!onNavigate || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
              e.preventDefault();
              onNavigate(id);
            }}
          >
            {label}
          </a>
        ))}
      </p>
    </footer>
  );
}
