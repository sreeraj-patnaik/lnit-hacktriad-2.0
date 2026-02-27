export default function RiskBadge({ risk }) {
  return (
    <div className={`risk ${risk.color}`}>
      {risk.parameter} - {risk.level}
    </div>
  );
}