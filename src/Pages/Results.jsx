import { useLocation } from "react-router-dom";
import RiskBadge from "../components/RiskBadge";
import ResultCard from "../components/ResultCard";
import TrendIndicator from "../components/TrendIndicator";

export default function Results() {
  const { state } = useLocation();

  const handleCopy = () => {
    navigator.clipboard.writeText(
      state.simplified_explanation + "\n\n" + state.doctor_summary
    );
    alert("Copied!");
  };

  const handleDownload = () => {
    const blob = new Blob(
      [state.simplified_explanation + "\n\n" + state.doctor_summary],
      { type: "text/plain" }
    );
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "health-summary.txt";
    link.click();
  };

  return (
    <div className="container">
      <h2>Results Dashboard</h2>

      <ResultCard title="Key Observations">
        <ul>
          {state.key_observations.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </ResultCard>

      <ResultCard title="Risk Highlights">
        {state.risk_highlights.map((risk, i) => (
          <RiskBadge key={i} risk={risk} />
        ))}
      </ResultCard>

      <ResultCard title="Simplified Explanation">
        <p>{state.simplified_explanation}</p>
      </ResultCard>

      <ResultCard title="Doctor Summary">
        <p>{state.doctor_summary}</p>
      </ResultCard>

      <ResultCard title="Trend Analysis">
        <TrendIndicator trend={state.trend_analysis} />
      </ResultCard>

      <div className="actions">
        <button onClick={handleCopy}>Copy Summary</button>
        <button onClick={handleDownload}>Download</button>
      </div>

      <div className="disclaimer">
        ⚠️ This tool does not provide medical diagnosis. 
        Please consult a licensed healthcare professional.
      </div>
    </div>
  );
}