import { useEffect, useRef, useState } from "react";
import { useLang } from "../../context/LangContext.jsx";
import { api } from "../../api/client.js";
import GlassPanel from "../ui/GlassPanel.jsx";
import { ChatAvatar } from "../hero/HeroShared.jsx";
import ChatMessage from "./ChatMessage.jsx";
import TypingIndicator from "./TypingIndicator.jsx";
import ChatInput from "./ChatInput.jsx";
import "./ChatWidget.css";

// Maps our two-letter site language to a BCP-47 tag the browser's
// SpeechRecognition/speechSynthesis APIs expect. Voice is a browser
// capability, not an LLM one — none of the configured providers
// (Anthropic/OpenAI/DeepSeek, see llm_client.py) expose a speech
// endpoint of any kind; they're all plain text chat-completions. So
// the mic turns speech into text client-side, that text goes through
// the exact same api.chat() call as typed messages (works unchanged
// against whichever provider is configured, DeepSeek included), and
// the reply is read back client-side too — no backend changes.
const SPEECH_LOCALE = { en: "en-US", ar: "ar-SA" };

function getSpeechRecognitionCtor() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

/**
 * Floating chat popover, docked bottom-right and layered above
 * StickyChat's toggle pill. Mirrors k-g-i.com's "Talk to Sulaiman"
 * widget: named persona + online status in the header, a starter
 * screen of tappable quick questions plus a standalone "Book a call"
 * row before the first message, and a small "Powered by" credit line
 * in the footer. The one chat surface on the site — text by default,
 * with an optional mic (browsers that support SpeechRecognition) for
 * voice in and spoken replies out.
 */
export default function ChatWidget({ open, onClose, onBookingClick, initialMessage, onConsumeInitialMessage }) {
  const { copy, lang, nav, branding, features } = useLang();
  const t = copy.chat;

  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [typing, setTyping] = useState(false);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [muted, setMuted] = useState(false);
  const [micNotice, setMicNotice] = useState("");
  const scrollRef = useRef(null);
  const leadCapturedRef = useRef(false);
  const recognitionRef = useRef(null);

  const speechSupported = !!getSpeechRecognitionCtor();
  const ttsSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  // Resets the welcome message on mount and on every language switch.
  // Deliberately does NOT depend on `initialMessage`/`open` — that's
  // handled by the effect below — so a language change never re-sends
  // whatever quick-start message has already been consumed.
  useEffect(() => {
    setMessages([{ from: "ai", text: t.welcomeMsg }]);
    leadCapturedRef.current = false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  // Sends the hero's quick-start message (from the quick-chat box, a
  // topic card, or an example prompt — see Hero.jsx handleTopicClick /
  // handleExamplePick) once the widget is actually open and a message
  // is waiting. This has to be its own effect: the hero handoff only
  // flips `open` and `initialMessage`, it never touches `lang`, so
  // folding this into the effect above (which only watched `lang`)
  // meant clicking a topic card opened the widget but never sent
  // anything. The parent clears `initialMessage` back to "" right
  // after consuming it (see App.jsx onConsumeInitialMessage), so the
  // `initialMessage` check below is enough to prevent double-sends.
  useEffect(() => {
    if (open && initialMessage) {
      sendMessage(initialMessage);
      onConsumeInitialMessage?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialMessage]);

  useEffect(() => {
    if (open) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, typing, open]);

  // Stop listening and cancel any in-flight speech the moment the
  // widget closes, so a background tab doesn't keep the mic hot or
  // talk over the next page.
  useEffect(() => {
    if (!open) {
      recognitionRef.current?.stop();
      if (ttsSupported) window.speechSynthesis.cancel();
      setListening(false);
      setSpeaking(false);
    }
    return () => {
      recognitionRef.current?.stop();
      if (ttsSupported) window.speechSynthesis.cancel();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function speak(text) {
    if (muted || !ttsSupported) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = SPEECH_LOCALE[lang] || SPEECH_LOCALE.en;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }

  async function sendMessage(text, historyOverride) {
    const outgoing = text.trim();
    if (!outgoing) return;
    setMicNotice("");
    setMessages((m) => [...m, { from: "user", text: outgoing }]);
    setDraft("");
    setTyping(true);
    const history = historyOverride ?? messages.map(({ from, text }) => ({ from, text }));
    const { reply, leadCaptured } = await api.chat(outgoing, lang, history, leadCapturedRef.current);
    leadCapturedRef.current = leadCaptured;
    setTyping(false);
    setMessages((m) => [...m, { from: "ai", text: reply }]);
    speak(reply);
  }

  function toggleMic() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setMicNotice(t.micUnsupported);
      return;
    }
    if (ttsSupported) window.speechSynthesis.cancel();
    setSpeaking(false);
    setMicNotice("");

    const recognition = new Ctor();
    recognition.lang = SPEECH_LOCALE[lang] || SPEECH_LOCALE.en;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setListening(true);
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      if (transcript.trim()) sendMessage(transcript);
    };
    recognition.onerror = (event) => {
      setMicNotice(event.error === "not-allowed" || event.error === "permission-denied" ? t.micDenied : t.micUnsupported);
    };
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
  }

  // Starter screen only shows before the visitor has sent anything —
  // same moment k-g-i.com shows theirs. "Book a call" rides in the
  // same chip row as the quick questions (not a separate highlighted
  // row) — that's how their suggestions list actually works.
  const showStarter = messages.length <= 1 && !typing;
  const starterChips = features.bookingEnabled ? [...nav.slice(0, 3), { id: "book", label: t.bookBtn }] : nav.slice(0, 4);

  function handleChipClick(item) {
    if (item.id === "book") onBookingClick?.();
    else sendMessage(item.label);
  }

  const statusLabel = listening ? t.micLabelListening : speaking ? t.micLabelSpeaking : t.onlineStatus;

  if (!open) return null;

  return (
    <GlassPanel className="chat-widget" as="section" role="dialog" aria-modal="true" aria-label={t.header}>
      <div className="chat-widget-header">
        <div className="chat-widget-persona">
          <ChatAvatar avatarUrl={branding.chatAvatarUrl} initial={branding.siteName?.[0]} className="chat-widget-avatar" />
          <div className="chat-widget-persona-text">
            <p className="chat-widget-name">{t.header}</p>
            <p className="chat-widget-status">
              <span className={`status-dot ${listening ? "voice-status-listening" : ""} ${speaking ? "voice-status-speaking" : ""}`} />
              {statusLabel}
            </p>
          </div>
        </div>
        <div className="chat-widget-header-actions">
          {ttsSupported && (
            <button
              className="chat-widget-close"
              onClick={() => setMuted((m) => !m)}
              aria-label={muted ? t.unmuteTts : t.muteTts}
              title={muted ? t.unmuteTts : t.muteTts}
            >
              {muted ? (
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <line x1="23" y1="9" x2="17" y2="15" />
                  <line x1="17" y1="9" x2="23" y2="15" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.5 8.5a5 5 0 0 1 0 7" />
                  <path d="M18.5 5.5a9 9 0 0 1 0 13" />
                </svg>
              )}
            </button>
          )}
          <button className="chat-widget-close" onClick={onClose} aria-label={copy.common.close}>✕</button>
        </div>
      </div>

      <div className="chat-widget-conversation" ref={scrollRef}>
        <div className="chat-messages">
          {messages.map((m, i) => (
            <ChatMessage key={i} from={m.from} text={m.text} />
          ))}
          {typing && <TypingIndicator label={copy.common.assistantTyping} />}
        </div>

        {showStarter && (
          <div className="chat-widget-starter">
            {starterChips.map((item) => (
              <button key={item.id} className="chat-widget-chip" onClick={() => handleChipClick(item)}>
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {micNotice && <p className="chat-widget-mic-notice">{micNotice}</p>}

      <ChatInput
        value={draft}
        onChange={setDraft}
        onSend={() => sendMessage(draft)}
        placeholder={t.inputPlaceholder}
        sendLabel={copy.common.send}
        disabled={typing}
        onMicClick={toggleMic}
        micSupported={speechSupported}
        micActive={listening}
        micLabel={listening ? t.micLabelListening : t.micLabel}
      />

      <footer className="chat-widget-footer">{t.poweredBy} <span>{branding.siteName}</span></footer>
    </GlassPanel>
  );
}
