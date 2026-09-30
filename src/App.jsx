import { useState } from "react";
import { LangProvider, useLang } from "./context/LangContext.jsx";
import Hero from "./components/hero/Hero.jsx";
import ChatWidget from "./components/chat/ChatWidget.jsx";
import ContentPage from "./components/pages/ContentPage.jsx";
import ContactPage from "./components/pages/ContactPage.jsx";
import StickyChat from "./components/StickyChat.jsx";
import BookingPanel from "./components/booking/BookingPanel.jsx";
import Toast from "./components/ui/Toast.jsx";

// Pages with dedicated components — every other page id routes through
// the generic, Markdown-driven ContentPage, so an admin can add a new
// page (any slug) with zero code changes on this end.
const SPECIAL_PAGE_IDS = new Set(["home", "contact"]);

// Needs useLang() (for features.bookingEnabled), which only works
// inside LangProvider — see the default export below.
function AppShell() {
  const { features } = useLang();
  const [page, setPage] = useState("home"); // "home" | "contact" | any configured page slug
  // Chat floats as a popover (see ChatWidget) instead of a routed
  // page, mirroring k-g-i.com's "Talk to Sulaiman" widget — it stays
  // mounted over whatever page is behind it rather than replacing it.
  // Both the hero's quick-start box and the sticky button open this
  // same widget (voice + text, see ChatWidget) — the one chat surface
  // on the whole site.
  const [chatOpen, setChatOpen] = useState(false);
  // Message typed into the hero's quick-start chat box, carried across
  // into ChatWidget so hitting Enter there feels like continuing the
  // same conversation rather than starting over.
  const [pendingMessage, setPendingMessage] = useState("");
  // The Appointments sticky button opens booking from any page, not
  // just from inside a chat conversation — this is that panel's state.
  const [bookingOpen, setBookingOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  const handleStickyChat = () => setChatOpen((o) => !o);

  const handleHeroEnter = (initialMessage) => {
    if (initialMessage) setPendingMessage(initialMessage);
    setChatOpen(true);
  };

  function handleBookingResult(text) {
    setBookingOpen(false);
    setToastMessage(text);
  }

  return (
    <>
      {/* Desktop has no in-flow "page vs widget" scroll separation like
          mobile does, so the fixed-position ChatWidget popover (bottom-
          right, up to 380x600) can sit directly over the home page's
          own centered hero content at ordinary laptop widths — two
          chat inputs, and often headline text, visibly overlapping.
          Dimming + disabling the page behind it while open (rather
          than only suppressing StickyChat, which is mobile-home-
          specific — see below) removes the collision on any page, any
          width, without having to chase every viewport where the
          fixed popover's box happens to land on top of in-flow
          content. */}
      <div className={`app-page-content ${chatOpen ? "app-page-content-dimmed" : ""}`.trim()}>
        {page === "home" && <Hero onEnter={handleHeroEnter} onNavigate={setPage} onBookingClick={() => setBookingOpen(true)} />}
        {page === "contact" && <ContactPage onBack={() => setPage("home")} onNavigate={setPage} />}
        {!SPECIAL_PAGE_IDS.has(page) && (
          <ContentPage pageId={page} onBack={() => setPage("home")} onNavigate={setPage} onBookingClick={() => setBookingOpen(true)} />
        )}
      </div>

      {/* Sticky action buttons — visible on all pages. The AI Assistant
          button is additionally suppressed on mobile on the home page
          specifically (isHome), since Hero already renders its own
          in-flow quick-chat box there — on a small screen the two sat
          close enough to collide. Desktop keeps both; every other page
          keeps the sticky button as-is (it's the only chat entry point
          there). */}
      <StickyChat
        onChatClick={handleStickyChat}
        onBookingClick={() => setBookingOpen(true)}
        showBooking={features.bookingEnabled}
        chatOpen={chatOpen}
        isHome={page === "home"}
      />

      <ChatWidget
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        initialMessage={pendingMessage}
        onConsumeInitialMessage={() => setPendingMessage("")}
        onBookingClick={() => setBookingOpen(true)}
      />

      {bookingOpen && features.bookingEnabled && (
        <BookingPanel onClose={() => setBookingOpen(false)} onResult={handleBookingResult} />
      )}

      {toastMessage && <Toast message={toastMessage} onDismiss={() => setToastMessage("")} />}
    </>
  );
}

export default function App() {
  return (
    <LangProvider>
      <AppShell />
    </LangProvider>
  );
}
