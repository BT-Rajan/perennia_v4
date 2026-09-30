import { useEffect } from "react";
import { useLang } from "../../context/LangContext.jsx";
import TopBar from "../layout/TopBar.jsx";
import GlassPanel from "../ui/GlassPanel.jsx";
import Markdown from "../ui/Markdown.jsx";
import { COPY } from "../../data/content.js";
import "./ContentPage.css";

/**
 * Standalone page for any page an admin has configured (About /
 * Products / Services / anything added later) — same header, tagline,
 * glass-panel shell, and footer treatment as the chat page, so every
 * page in the app feels like one family. `pageId` selects which
 * content record (fetched from the backend, see src/data/siteContent.js)
 * renders inside the shell.
 */
export default function ContentPage({ pageId, onBack, onNavigate, onBookingClick }) {
  const { pages, branding, copy, lang, features } = useLang();
  const meta = pages[pageId];
  // For a `[[cta]]` block in the page body (e.g. a case study): the same
  // label and booking panel as the homepage's primary CTA, falling back
  // to the Contact page when booking is switched off.
  const cta = {
    label: copy.home?.ctaPrimary ?? (COPY[lang] ?? COPY.en).home.ctaPrimary,
    onClick: features?.bookingEnabled && onBookingClick ? onBookingClick : () => onNavigate("contact"),
  };

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pageId]);

  if (!meta) return null; // an admin-removed or not-yet-loaded page id; nothing to render

  return (
    <div className="content-page">
      <TopBar onNavigate={onNavigate} onLogoClick={onBack} />

      <main className="content-main">
        <div className="content-tagline">
          <div className="content-tagline-main">
            <span>{meta.line1}</span>
            <span className="gold">{meta.line2}</span>
          </div>
          <div className="content-tagline-divider" />
          <div className="content-tagline-sub">{meta.sub}</div>
        </div>


        <GlassPanel className="content-shell" as="section">
          <Markdown source={meta.body} cta={cta} />
        </GlassPanel>
      </main>

      <footer className="content-footer">© {new Date().getFullYear()} {branding.siteName}. All rights reserved.</footer>
    </div>
  );
}
