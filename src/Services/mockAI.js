export const processReport = (data) => {
  const { report, language } = data;

  let risks = [];

  if (report.toLowerCase().includes("cholesterol")) {
    risks.push({ parameter: "Cholesterol", level: "High", color: "red" });
  }

  if (report.toLowerCase().includes("hemoglobin")) {
    risks.push({ parameter: "Hemoglobin", level: "Borderline", color: "yellow" });
  }

  const explanationEnglish =
    "Some parameters are outside optimal range. Consider lifestyle improvements and consult a doctor.";

  const explanationHindi =
    "कुछ मान सामान्य सीमा से बाहर हैं। कृपया डॉक्टर से सलाह लें।";

  return {
    key_observations: [
      "Elevated cholesterol detected.",
      "Mild hemoglobin variation."
    ],
    risk_highlights: risks,
    simplified_explanation:
      language === "Hindi" ? explanationHindi : explanationEnglish,
    doctor_summary:
      "Discuss lipid profile and dietary habits with healthcare provider.",
    trend_analysis: "stable"
  };
};