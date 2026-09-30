import { useRef } from "react";
import IconButton from "../ui/IconButton.jsx";
import "./ChatInput.css";

/**
 * `onMicClick` is optional — pass it (plus `micSupported`) to show a
 * mic button before the send button, for voice-capable callers like
 * ChatWidget. Omitting it renders the plain text-only input, same as
 * before.
 */
export default function ChatInput({
  value,
  onChange,
  onSend,
  placeholder,
  sendLabel = "Send",
  disabled,
  onMicClick,
  micSupported = false,
  micActive = false,
  micLabel = "Talk",
}) {
  const areaRef = useRef(null);

  function handleInput(e) {
    onChange(e.target.value);
    const el = areaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) onSend();
    }
  }

  return (
    <div className="chat-input-area">
      <textarea
        ref={areaRef}
        className="chat-input"
        rows={1}
        value={value}
        placeholder={placeholder}
        aria-label={placeholder}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      {micSupported && (
        <IconButton
          title={micLabel}
          onClick={onMicClick}
          size="md"
          className={`chat-input-mic ${micActive ? "chat-input-mic-active" : ""}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
          </svg>
        </IconButton>
      )}
      <IconButton title={sendLabel} disabled={!value.trim() || disabled} onClick={onSend} size="md">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </IconButton>
    </div>
  );
}
