import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { processReport } from "../services/mockAI";
import Loader from "../Components/Loader";

export default function Analyze() {
  const [report, setReport] = useState("");
  const [language, setLanguage] = useState("English");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleAnalyze = () => {
    setLoading(true);

    setTimeout(() => {
      const result = processReport({ report, language });
      setLoading(false);
      navigate("/results", { state: result });
    }, 1500);
  };

  return (
    <div className="container">
      <h2>Analyze Medical Report</h2>

      <textarea
        placeholder="Paste medical report..."
        value={report}
        onChange={(e) => setReport(e.target.value)}
      />

      <select value={language} onChange={(e) => setLanguage(e.target.value)}>
        <option>English</option>
        <option>Hindi</option>
        <option>Tamil</option>
        <option>Kannada</option>
        <option>Malayalam</option>

      </select>

      <button onClick={handleAnalyze}>Analyze Report</button>

      {loading && <Loader />}
    </div>
  );
}