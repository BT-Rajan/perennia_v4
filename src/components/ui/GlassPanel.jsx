import "./GlassPanel.css";

/**
 * The single glass-morphism surface used everywhere a "card" is needed:
 * chat shell, booking panel, FAQ sidebar, nav preview. Keeping one
 * component means the blur/border/shadow treatment never drifts
 * between screens.
 */
export default function GlassPanel({ as: Tag = "div", className = "", children, ...rest }) {
  return (
    <Tag className={`glass-panel ${className}`.trim()} {...rest}>
      {children}
    </Tag>
  );
}
