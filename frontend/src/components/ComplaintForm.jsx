import React from 'react'
import { useDispatch, useSelector } from 'react-redux'

import { commit, editField, resetAll } from '../store/complaintSlice'
import { setToast } from '../store/uiSlice'
import Insights from './Insights'
import RiskPanel from './RiskPanel'

// Sections mirror the demo form. The numbering is kept because a QMS intake form
// really is a sequence -- the reviewer works top to bottom before sign-off.
const SECTIONS = [
  {
    label: '1. Origin & Customer Details',
    fields: [
      ['complaint_source', 'Complaint Source'],
      ['customer_name', 'Customer Name'],
      ['complaint_date', 'Complaint Date'],
    ],
  },
  {
    label: '2. Product & Batch Identification',
    fields: [
      ['product_name', 'Product Name'],
      ['product_strength', 'Product Strength / Grade'],
      ['batch_number', 'Batch / Lot Number'],
      ['affected_quantity', 'Affected Quantity'],
      ['manufacturing_date', 'Manufacturing Date'],
      ['expiry_date', 'Expiry Date'],
    ],
  },
  {
    label: '3. Facility & Material Impact',
    fields: [
      ['originating_site_block', 'Originating Site Block'],
      ['impacted_npm', 'Impacted Non-Product Materials (NPM)'],
    ],
  },
  {
    label: '4. Defect Analysis',
    fields: [
      ['complaint_category', 'Complaint Category'],
      ['complaint_description', 'Complaint Description', 'textarea'],
    ],
  },
]

function StatusPill({ committedAs, ready }) {
  if (committedAs) {
    return (
      <span className="pill committed">
        <i className="pill-dot" />
        {committedAs}
      </span>
    )
  }
  return (
    <span className={'pill ' + (ready ? 'ready' : 'pending')}>
      <i className="pill-dot" />
      {ready ? 'Ready to Commit' : 'Pending Triage'}
    </span>
  )
}

export default function ComplaintForm() {
  const dispatch = useDispatch()
  const { form, changedFields, provenance, completeness, committedAs, status } = useSelector(
    (s) => s.complaint,
  )

  const onCommit = async () => {
    const result = await dispatch(commit())
    if (result.meta.requestStatus === 'fulfilled') {
      dispatch(setToast('Committed to the QMS ledger as ' + result.payload.complaint_no))
    } else {
      dispatch(setToast(result.payload || 'Commit failed'))
    }
  }

  return (
    <section className="pane">
      <div className="pane-scroll">
        <header className="form-head">
          <div>
            <h1>Log Customer Complaint</h1>
            <p>API &amp; FDF Quality Assurance Module</p>
          </div>
          <StatusPill committedAs={committedAs} ready={completeness.ready_to_commit} />
        </header>

        <Insights />

        {SECTIONS.map((section) => (
          <div className="section" key={section.label}>
            <div className="section-label">{section.label}</div>
            <div className="grid2">
              {section.fields.map(([key, label, kind]) => {
                const changed = changedFields.includes(key)
                const origin = provenance[key]
                const Tag = kind === 'textarea' ? 'textarea' : 'input'
                return (
                  <div
                    className={
                      'field' + (kind === 'textarea' ? ' wide' : '') + (changed ? ' changed' : '')
                    }
                    key={key}
                  >
                    <label htmlFor={key}>
                      {label}
                      {origin === 'manual' && <span className="origin-tag manual">edited</span>}
                      {origin && origin.startsWith('document:') && (
                        <span className="origin-tag">from file</span>
                      )}
                    </label>
                    <Tag
                      id={key}
                      value={form[key] || ''}
                      placeholder="Awaiting AI extraction..."
                      onChange={(e) =>
                        dispatch(editField({ field: key, value: e.target.value }))
                      }
                    />
                  </div>
                )
              })}
            </div>
          </div>
        ))}

        <RiskPanel />

        <button
          className="primary-btn"
          onClick={onCommit}
          disabled={!completeness.ready_to_commit || status === 'loading' || !!committedAs}
        >
          {committedAs ? 'Committed as ' + committedAs : 'Commit to QMS Ledger'}
        </button>
        <p className="commit-note">
          {committedAs
            ? 'This complaint is now on the ledger and locked.'
            : completeness.ready_to_commit
              ? 'A QA reviewer signs off. The AI only proposes.'
              : 'Fill the blocking fields above before committing.'}
        </p>

        <div style={{ marginTop: 14, textAlign: 'center' }}>
          <button className="ghost-btn" onClick={() => dispatch(resetAll())}>
            Start a new complaint
          </button>
        </div>
      </div>
    </section>
  )
}
