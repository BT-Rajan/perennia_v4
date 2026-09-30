import "./TypingIndicator.css";

export default function TypingIndicator({ label = "Assistant is typing" }) {
  return (
    <div className="msg msg-ai">
      <div className="msg-bubble typing-bubble" aria-label={label}>
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}
