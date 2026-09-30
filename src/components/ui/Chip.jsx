import "./Chip.css";

export default function Chip({ children, onClick, icon, active = false }) {
  return (
    <button className={`chip${active ? " chip-active" : ""}`} onClick={onClick}>
      {icon && <span className="chip-icon">{icon}</span>}
      <span>{children}</span>
    </button>
  );
}
