import "./TopBar.css";
import { useLang } from "../../context/LangContext.jsx";
import { COPY } from "../../data/content.js";
import Button from "../ui/Button.jsx";
import LangToggle from "../ui/LangToggle.jsx";
import Logo from "../ui/Logo.jsx";
import NavMenu from "./NavMenu.jsx";

/**
 * `leading` renders next to the logo at the start edge (e.g. the chat
 * page's back button). `children` renders in the action cluster at the
 * end edge (e.g. the "Talk to Us" chip), followed by the language toggle.
 * `onNavigate` wires up the About/Products/Services/Contact Us menu,
 * centered in the header on desktop (matches the reference site's
 * logo — nav — actions layout). `onLogoClick`, when provided, makes the
 * logo itself a shortcut back to Home — used on every page except Home.
 * `onBook`, when provided, adds the primary "Book a 30-Minute Discovery
 * Meeting" CTA — in the header on desktop, inside the mobile drawer
 * below 1024px — so booking is always one tap away from the nav.
 */
export default function TopBar({ leading, children, onNavigate, onLogoClick, onBook }) {
  const { copy, lang } = useLang();
  const bookLabel = copy.home?.ctaPrimary ?? (COPY[lang] ?? COPY.en).home.ctaPrimary;
  return (
    <header className="top-bar-header">
      <div className="top-bar-start">
        {onLogoClick ? (
          <button className="logo-btn" onClick={onLogoClick} aria-label={copy.common.goHome}>
            <Logo />
          </button>
        ) : (
          <Logo />
        )}
        {leading}
      </div>
      <div className="top-bar-center">
        <NavMenu onNavigate={onNavigate} onBook={onBook} bookLabel={bookLabel} />
      </div>
      <div className="top-bar-end">
        {children}
        {onBook && (
          <Button variant="primary" className="top-bar-cta" onClick={onBook}>{bookLabel}</Button>
        )}
        <LangToggle />
      </div>
    </header>
  );
}
