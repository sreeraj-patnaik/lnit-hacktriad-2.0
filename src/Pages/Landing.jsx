import { useNavigate } from "react-router-dom";
import risk from '../images/risk.png'
import language from '../images/languages.png'
import trend from '../images/trend.png'
import report from '../images/report.png'
export default function Landing() {
  const navigate = useNavigate();

  return (
    <>
      {/* HERO SECTION */}
      <section className="hero-section">
        <h1>Context-Aware AI Health Trajectory Interpreter</h1>
        <p>
          Understand your medical reports clearly with safe, responsible AI insights.
        </p>

        <button
          className="primary-btn"
          onClick={() => navigate("/analyze")}
        >
          Start Analysis
        </button>
      </section>

      {/* FEATURES SECTION */}
      <section className="features-section">
        <div className="features">

          <div className="feature-card">
            <img className="risk" src={risk} />
            <h3>Risk Highlighting</h3>
            <p>Visual red/yellow/green risk indicators.</p>
          </div>

          <div className="feature-card">
            <img className="risk" src={language} />
            <h3>Multilingual Support</h3>
            <p>Explanations in regional languages.</p>
          </div>

          <div className="feature-card">
            <img className="risk" src={trend} />
            <h3>Trend Analysis</h3>
            <p>Track improvement or worsening over time.</p>
          </div>

          <div className="feature-card">
            <img className="risk" src={report} />
            <h3>Simplified Reports</h3>
            <p>Understand complex medical reports in simple language.</p>
          </div>

        </div>
      </section>
    </>
  );
}