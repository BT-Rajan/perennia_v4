import { useEffect } from "react";
import GlassPanel from "./GlassPanel.jsx";
import "./Toast.css";

// Booking result messages (confirmation/cancellation/reschedule text)
// were previously only ever shown inline as an "ai" chat bubble inside
// ChatWidget. The Appointments sticky button opens the same BookingPanel
// from outside the chat conversation (any page), so there's no message
// list to drop that text into — this toast is the equivalent surface
// for that context, styled the same as the rest of the theme.
export default function Toast({ message, onDismiss, duration = 6000 }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onDismiss]);

  return (
    <GlassPanel className="toast" as="div" role="status">
      <span className="toast-message">{message}</span>
      <button className="toast-close" onClick={onDismiss} aria-label="Dismiss">✕</button>
    </GlassPanel>
  );
}
