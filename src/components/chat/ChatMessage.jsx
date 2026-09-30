import "./ChatMessage.css";

// The assistant's replies sometimes come back with lightweight markdown
// (mainly **bold**) from the LLM. We previously rendered `text` as a raw
// string, so the literal ** markers showed up in the bubble instead of
// being turned into formatting. This does a minimal, safe (no HTML
// injection) pass over **bold** and *italic* spans and returns React nodes;
// line breaks keep working via the existing `white-space: pre-wrap` on
// .msg-bubble, so we don't need to touch those here.
function formatText(text) {
  const boldSplit = text.split(/(\*\*[^*\n]+\*\*)/g);
  return boldSplit.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    const italicSplit = part.split(/(\*[^*\n]+\*)/g);
    if (italicSplit.length === 1) return part;
    return italicSplit.map((chunk, j) =>
      chunk.startsWith("*") && chunk.endsWith("*") && chunk.length > 2 ? (
        <em key={`${i}-${j}`}>{chunk.slice(1, -1)}</em>
      ) : (
        chunk
      )
    );
  });
}

export default function ChatMessage({ from, text }) {
  return (
    <div className={`msg msg-${from}`}>
      <div className="msg-bubble">{formatText(text)}</div>
    </div>
  );
}
