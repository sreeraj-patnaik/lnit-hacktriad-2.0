export default function TrendIndicator({ trend }) {
  if (trend === "improving") return <p className="green">↑ Improving</p>;
  if (trend === "worsening") return <p className="red">↓ Worsening</p>;
  return <p className="yellow">→ Stable</p>;
}