import React from 'react'
import { useSelector } from 'react-redux'

/** Completeness Checker + Duplicate Detection, surfaced above the form so a
 *  reviewer sees the gaps before scrolling through thirteen fields. */
export default function Insights() {
  const { completeness, duplicates } = useSelector((s) => s.complaint)
  if (!completeness.score && duplicates.length === 0) return null

  return (
    <div className="insight-row">
      <div className="meter">
        <div className="meter-top">
          <span>Complaint completeness</span>
          <span>{completeness.score}%</span>
        </div>
        <div
          className="meter-track"
          role="progressbar"
          aria-valuenow={completeness.score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Complaint completeness"
        >
          <div className="meter-fill" style={{ width: completeness.score + '%' }} />
        </div>
        {completeness.missing_fields.length > 0 && (
          <div className="chips">
            {completeness.missing_fields.map((f) => (
              <span className="chip" key={f}>
                {f}
              </span>
            ))}
          </div>
        )}
      </div>

      {duplicates.map((d) => (
        <div className="dupe" key={d.complaint_no}>
          Possible duplicate of <b>{d.complaint_no}</b> ({d.product_name}, batch {d.batch_number}) -{' '}
          {d.reason}. Confidence {d.score}%.
        </div>
      ))}
    </div>
  )
}
