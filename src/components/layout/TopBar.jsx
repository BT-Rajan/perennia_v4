import "./TopBar.css";
import { useLang } from "../../context/LangContext.jsx";
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
 */
export default function TopBar({ leading, children, onNavigate, onLogoClick }) {
  const { copy } = useLang();
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
        <NavMenu onNavigate={onNavigate} />
      </div>
      <div className="top-bar-end">
        {children}
        <LangToggle />
      </div>
    </header>
  );
}
