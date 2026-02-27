export default function ResultCard({ title, children }) {
  return (
    <div className="result-card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}