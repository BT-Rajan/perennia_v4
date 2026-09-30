import { useLang } from "../../context/LangContext.jsx";
import { COPY } from "../../data/content.js";
import Button from "../ui/Button.jsx";
import "./SiteFooter.css";

/**
 * The one footer every page renders (Home, content pages, Contact):
 * the brand line, the same destinations as the header nav (so Solutions,
 * Work, Products, Labs, About and Contact are always reachable from the
 * bottom of a page), configured contact details, and the discovery
 * meeting — as a quiet ghost button, since the page above already
 * carries the primary CTA. `onNavigate`/`onBook` are the same handlers
 * the page passes to TopBar.
 */
export default function SiteFooter({ onNavigate, onBook }) {
  const { nav, copy, lang, branding, contact } = useLang();
  const fallback = COPY[lang] ?? COPY.en;
  const common = { ...fallback.common, ...copy.common };
  const bookLabel = copy.home?.ctaPrimary ?? fallback.home.ctaPrimary;
  const tagline = copy.home?.eyebrow ?? fallback.home.eyebrow;
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
          <ul>
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
          {onBook && (
            <Button variant="ghost" className="site-footer-cta" onClick={onBook}>{bookLabel}</Button>
          )}
        </div>
      </div>
      <p className="site-footer-legal">© {new Date().getFullYear()} {branding.siteName}. {common.footerRights}</p>
    </footer>
  );
}
