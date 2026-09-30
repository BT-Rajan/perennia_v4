import { useEffect, useState } from "react";
import { useLang } from "../../context/LangContext.jsx";
import TopBar from "../layout/TopBar.jsx";
import SiteFooter from "../layout/SiteFooter.jsx";
import GlassPanel from "../ui/GlassPanel.jsx";
import Button from "../ui/Button.jsx";
import Markdown from "../ui/Markdown.jsx";
import PageIllustration, { asideProps } from "../ui/PageIllustration.jsx";
import { PAGE_ILLUSTRATIONS } from "../../data/pageIllustrations.js";
import BookingPanel from "../booking/BookingPanel.jsx";
import "./ContentPage.css";
import "./ContactPage.css";

/**
 * The Contact page: the same shell as ContentPage, plus a "Book a
 * Us" call-to-action that opens the existing booking flow in place —
 * no separate route needed for scheduling a call.
 */
export default function ContactPage({ onBack, onNavigate, onBookingClick }) {
  const { copy, pages, features, contact, lang } = useLang();
  const meta = pages.contact;

  const [bookingOpen, setBookingOpen] = useState(false);
  const [confirmation, setConfirmation] = useState(null);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  function handleBookingResult(text) {
    setBookingOpen(false);
    setConfirmation(text);
  }

  if (!meta) return null;

  const hasContactDetails = contact && (contact.email || contact.phone || contact.whatsappNumber || contact.address);
  const whatsappDigits = (contact?.whatsappNumber || "").replace(/\D/g, "");

  return (
    <div className="content-page">
      <TopBar onNavigate={onNavigate} onLogoClick={onBack} onBook={onBookingClick} />

      <main className="content-main">
        <div className="content-tagline">
          <div className="content-tagline-main">
            <span>{meta.line1}</span>
            <span className="gold">{meta.line2}</span>
          </div>
          <div className="content-tagline-divider" />
          <div className="content-tagline-sub">{meta.sub}</div>
        </div>

        <GlassPanel className="content-shell content-shell--aside contact-shell" as="section">
          <div className="content-shell-text">
            <Markdown source={meta.body} />

            {hasContactDetails && (
              <ul className="contact-details-list">
                {contact.email && (
                  <li><a href={`mailto:${contact.email}`}>{contact.email}</a></li>
                )}
                {contact.phone && (
                  <li>
                    {lang === "ar" ? "الجوال: " : "Mobile: "}
                    <a href={`tel:${contact.phone.replace(/[^\d+]/g, "")}`} dir="ltr">{contact.phone}</a>
                  </li>
                )}
                {whatsappDigits && (
                  <li><a href={`https://wa.me/${whatsappDigits}`} target="_blank" rel="noopener noreferrer">WhatsApp: {contact.whatsappNumber}</a></li>
                )}
                {contact.address && <li>{contact.address}</li>}
              </ul>
            )}

            {confirmation && <p className="contact-confirmation">{confirmation}</p>}

            {features.bookingEnabled && (
              <>
                <div className="contact-cta-row">
                  <Button variant="primary" onClick={() => setBookingOpen(true)}>
                    {copy.chat.bookBtn}
                  </Button>
                </div>

                {bookingOpen && (
                  <BookingPanel onClose={() => setBookingOpen(false)} onResult={handleBookingResult} />
                )}
              </>
            )}
          </div>
          <PageIllustration item={PAGE_ILLUSTRATIONS.contact} lang={lang} {...asideProps(PAGE_ILLUSTRATIONS.contact)} />
        </GlassPanel>
      </main>

      <SiteFooter onNavigate={onNavigate} onBook={onBookingClick} />
    </div>
  );
}
