export default function StatCard({ label, value, note, icon: Icon, trend, warning = false }) {
  return (
    <article className="stat-card">
      <div className="stat-card-top">
        <span>{label}</span>
        <Icon size={17} aria-hidden="true" />
      </div>
      <strong className="stat-value">{value}</strong>
      <div className="stat-card-foot">
        <span>{note}</span>
        <small className={warning ? 'warning' : ''}>{trend}</small>
      </div>
    </article>
  );
}
