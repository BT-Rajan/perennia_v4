export default function StatCard({ label, value, detail }) {
  return (
    <div className="card stat-card">
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
      {detail && <div className="stat-card-detail">{detail}</div>}
    </div>
  );
}
