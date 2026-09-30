import { useState } from "react";
import { useLang } from "../context/LangContext.jsx";
import styles from "./StickyChat.module.css";

function StickyButton({ label, icon, onClick, variant }) {
  const [isHovered, setIsHovered] = useState(false);
  return (
    <button
      className={`sticky-cta-btn ${styles.chatButton} ${variant ? styles[variant] : ""} ${isHovered ? styles.hovered : ""}`}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      aria-label={label}
      title={label}
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.icon}
      >
        {icon}
      </svg>
      <span className={styles.label}>{label}</span>
    </button>
  );
}

/**
 * Sticky action buttons that float at bottom-right, stacked vertically
 * and stay visible across all pages: Appointments above AI Assistant.
 * The AI Assistant button always shows its label (not hover-only) and
 * swaps to a close icon while the ChatWidget popover is open — the
 * same persistent "Talk to Sulaiman <-> X" pattern as k-g-i.com's widget
 * toggle, rather than the previous full-page chat navigation.
 * @param {function} onChatClick - Toggles the ChatWidget popover open/closed
 * @param {function} onBookingClick - Callback when the Appointments button is clicked
 * @param {boolean} showBooking - Whether the Appointments button renders at all
 * @param {boolean} chatOpen - Whether the ChatWidget popover is currently open
 * @param {boolean} isHome - True on the home page, where Hero already renders
 *   its own in-flow quick-chat box. On mobile that box sits close enough to
 *   this fixed button to collide, so the AI Assistant button (only — the
 *   Appointments button has no such duplicate) is hidden there below 768px;
 *   see .homeMobileHidden in StickyChat.module.css. Desktop is unaffected,
 *   and every other page keeps the sticky button exactly as before.
 */
export default function StickyChat({ onChatClick, onBookingClick, showBooking = true, chatOpen = false, isHome = false }) {
  const { copy } = useLang();

  return (
    <div className={styles.stickyContainer}>
      {showBooking && (
        <StickyButton
          label="Appointments"
          variant="booking"
          onClick={() => onBookingClick?.()}
          icon={
            <>
              <rect x="3" y="4" width="18" height="18" rx="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </>
          }
        />
      )}
      <div className={`${styles.chatButtonWrap} ${isHome ? styles.homeMobileHidden : ""}`}>
        <StickyButton
          label={chatOpen ? copy.common.close : copy.chat.header}
          onClick={() => onChatClick?.()}
          icon={
            chatOpen ? (
              <>
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </>
            ) : (
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            )
          }
        />
        {!chatOpen && <div className={styles.pulse} />}
        {!chatOpen && <span className={styles.onlineDot} aria-hidden="true" />}
      </div>
    </div>
  );
}
