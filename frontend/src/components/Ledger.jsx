import React, { useEffect, useState } from 'react'
import { useDispatch } from 'react-redux'

import { fetchLedger } from '../api'
import { setLedger } from '../store/uiSlice'

/** The committed complaints. Proves the workflow persists to a real database
 *  and gives duplicate detection something to match against. */
export default function Ledger() {
  const dispatch = useDispatch()
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchLedger().then(setRows).catch((e) => setError(e.message))
  }, [])

  return (
    <div className="modal-backdrop" onClick={() => dispatch(setLedger(false))}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="QMS ledger">
        <div className="modal-head">
          <h2>QMS Complaint Ledger</h2>
          <button
            className="ghost-btn icon-btn"
            style={{ marginLeft: 'auto' }}
            onClick={() => dispatch(setLedger(false))}
            aria-label="Close"
          >
            &times;
          </button>
        </div>
        <div className="modal-body">
          {error && <div className="empty-state">Could not load the ledger: {error}</div>}
          {!error && rows === null && <div className="empty-state">Loading...</div>}
          {rows?.length === 0 && (
            <div className="empty-state">
              No complaints committed yet. Log one with the Copilot, then commit it.
            </div>
          )}
          {rows?.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Complaint No.</th>
                  <th>Product</th>
                  <th>Batch</th>
                  <th>Customer</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.complaint_no}</td>
                    <td>{r.product_name}</td>
                    <td>{r.batch_number}</td>
                    <td>{r.customer_name}</td>
                    <td>{r.severity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
