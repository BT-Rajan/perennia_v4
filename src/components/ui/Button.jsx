import "./Button.css";

/**
 * One Button to cover every call-to-action in the app: primary (gold),
 * ghost (outline), and text-only, in normal or full-width form.
 * Every screen reuses this instead of hand-rolling button CSS.
 */
export default function Button({
  variant = "primary", // "primary" | "ghost" | "text"
  fullWidth = false,
  disabled = false,
  onClick,
  children,
  type = "button",
  ...rest
}) {
  return (
    <button
      type={type}
      className={`btn btn-${variant}${fullWidth ? " btn-full" : ""}`}
      disabled={disabled}
      onClick={onClick}
      {...rest}
    >
      {children}
    </button>
  );
}
