import React from 'react'
import { useSelector } from 'react-redux'

// Order matters: severity and next action are what a QA reviewer triages on, so
// they lead. Root cause and CAPA are proposals for the investigation that follows.
const ROWS = [
  ['suggested_next_action', 'Suggested Next Action'],
  ['initial_risk_assessment', 'Initial Risk Assessment'],
  ['probable_root_cause', 'Probable Root Cause'],
  ['capa_recommendation', 'CAPA Recommendation'],
  ['regulatory_reportable', 'Regulatory Reportability'],
  ['summary', 'Complaint Summary'],
]

export default function RiskPanel() {
  const risk = useSelector((s) => s.complaint.risk)
  const severity = (risk.severity_suggested || '').toLowerCase()
  const filled = ROWS.filter(([key]) => risk[key])

  return (
    <div className="risk-card">
      <div className="risk-head">
        <span aria-hidden="true">&#128737;</span>
        AI Copilot Risk Assessment
        {risk.severity_suggested && (
          <span className={'sev ' + severity}>{risk.severity_suggested}</span>
        )}
        {risk.confidence > 0 && (
          <span className="conf">{Math.round(risk.confidence * 100)}% confidence</span>
        )}
      </div>

      {filled.length === 0 ? (
        <p className="risk-empty">
          The Copilot fills this in once a complaint is logged. Severity, root cause and CAPA are
          proposals for a QA reviewer, not decisions.
        </p>
      ) : (
        <dl style={{ margin: 0 }}>
          {filled.map(([key, label]) => (
            <div className="risk-item" key={key}>
              <dt>{label}</dt>
              <dd>{risk[key]}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  )
}
