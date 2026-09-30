import "./IconButton.css";

export default function IconButton({ children, onClick, title, disabled = false, size = "md", className = "" }) {
  return (
    <button
      className={`icon-btn icon-btn-${size} ${className}`.trim()}
      onClick={onClick}
      title={title}
      aria-label={title}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
