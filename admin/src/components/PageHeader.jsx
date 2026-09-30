export default function PageHeader({ title, subtitle, actions }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 22 }}>{title}</h1>
        {subtitle && <p style={{ margin: "4px 0 0", color: "var(--text-muted)", fontSize: 14 }}>{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}
