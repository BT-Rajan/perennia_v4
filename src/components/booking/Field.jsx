import "./Field.css";

export default function Field({ label, children }) {
  return (
    <div className="bk-field">
      <label>{label}</label>
      {children}
    </div>
  );
}
