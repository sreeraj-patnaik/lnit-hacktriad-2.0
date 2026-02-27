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
        <h1>AI Report Analyser & Health Trajectory Interpreter</h1>
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
            <p>Visual red/yellow/green risk indicators.

            </p>
          </div>

          <div className="feature-card">
            <img className="risk" src={language} />
            <h3>Multilingual Support</h3>
            <p>Receive explanations in your preferred language for better understanding and accessibility.</p>
          </div>

          <div className="feature-card">
            <img className="risk" src={trend} />
            <h3>Trend Analysis</h3>
            <p>Compare reports over time to understand how your health markers are improving or changing.</p>
          </div>

          <div className="feature-card">
            <img className="risk" src={report} />
            <h3>Simplified Reports</h3>
            <p>Understand complex medical reports in simple language.</p>
          </div>

        </div>
      </section>
            {/* DESIGNED FOR SECTION */}
      <section className="designed-section">
        <h2 className="designed-title">Designed For</h2>

        <div className="designed-tags">
          <div className="tag">Patients with recurring lab tests</div>
          <div className="tag">Individuals with low health literacy</div>
          <div className="tag">Elderly users seeking clarity</div>
          <div className="tag">Regional language speakers</div>
        </div>
      </section>

      {/* DISCLAIMER SECTION */}
      {/* FOOTER SECTION */}
<footer className="footer-section">
  <div className="footer-container">

    <div className="footer-about">
      <h3>About This Project</h3>
      <p>
        Context-Aware AI Health Trajectory Interpreter is a responsible AI
        healthcare prototype designed to simplify complex medical reports,
        highlight potential risks, and provide multilingual health insights.
      </p>
    </div>

    <div className="footer-mission">
      <h3>Our Mission</h3>
      <p>
        To make medical information understandable, accessible,
        and actionable for everyone — without replacing professional care.
      </p>
    </div>

  </div>

  <div className="footer-bottom">
    © 2026 AI Health Interpreter • Educational Prototype
  </div>
</footer>
    </>
  );
}