import { useState } from "react";
import { useLang } from "../../context/LangContext.jsx";
import "./NavMenu.css";

const HOME_ICON = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M3 11.5 12 4l9 7.5" />
    <path d="M5.5 10v9a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1v-9" />
  </svg>
);

/**
 * Persistent header nav, styled after the reference site's layout:
 * logo — nav menu — actions. `onNavigate(id)` is called with the
 * section id ("home" | "about" | "products" | "services" | "contact")
 * when a link is clicked; the caller decides what that means on its
 * page. A Home icon always leads the menu, ahead of the
 * admin-configured page links, so there's a way back to Home from the
 * nav itself (independent of the logo, which also does this).
 *
 * Below 1024px the inline nav-menu is hidden (see NavMenu.css) and a
 * hamburger toggle + slide-down drawer take over, rendering the exact
 * same Home + page links instead of dropping navigation entirely on
 * small screens.
 */
export default function NavMenu({ onNavigate }) {
  const { nav, copy } = useLang();
  const [open, setOpen] = useState(false);

  function handleClick(id) {
    setOpen(false);
    onNavigate?.(id);
  }

  return (
    <>
      <nav className="nav-menu" aria-label={copy.common.primaryNav}>
        <button
          key="home"
          className="nav-menu-link nav-menu-home"
          onClick={() => onNavigate?.("home")}
          title={copy.common.goHome}
          aria-label={copy.common.goHome}
        >
          {HOME_ICON}
        </button>
        {nav.map((item) => (
          <button key={item.id} className="nav-menu-link" onClick={() => onNavigate?.(item.id)}>
            {item.label}
          </button>
        ))}
      </nav>

      <button
        type="button"
        className={`nav-mobile-toggle ${open ? "is-open" : ""}`}
        aria-expanded={open}
        aria-controls="nav-mobile-drawer"
        aria-label={open ? copy.common.close : copy.common.quickMenu}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="nav-mobile-toggle-bar" aria-hidden="true" />
        <span className="nav-mobile-toggle-bar" aria-hidden="true" />
        <span className="nav-mobile-toggle-bar" aria-hidden="true" />
      </button>

      {/* Dismiss-on-outside-tap layer; the drawer itself stays reachable
          by keyboard regardless (Escape isn't wired, but tabbing off
          the last link naturally leaves the (offscreen) drawer). */}
      <div
        className={`nav-mobile-backdrop ${open ? "is-open" : ""}`}
        onClick={() => setOpen(false)}
        aria-hidden="true"
      />

      <nav
        id="nav-mobile-drawer"
        className={`nav-mobile-drawer ${open ? "is-open" : ""}`}
        aria-label={copy.common.primaryNav}
      >
        <button className="nav-mobile-link nav-mobile-home" onClick={() => handleClick("home")}>
          {HOME_ICON}
          <span>{copy.common.goHome}</span>
        </button>
        {nav.map((item) => (
          <button key={item.id} className="nav-mobile-link" onClick={() => handleClick(item.id)}>
            {item.label}
          </button>
        ))}
      </nav>
    </>
  );
}
