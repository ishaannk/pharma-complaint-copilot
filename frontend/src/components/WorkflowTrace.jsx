import React from 'react'
import { useSelector } from 'react-redux'

/** Shows which LangGraph nodes ran on the last turn, and how long each took.
 *  Makes the agent workflow visible instead of something you take on trust. */
export default function WorkflowTrace() {
  const trace = useSelector((s) => s.complaint.trace)
  if (!trace.length) return null

  return (
    <div className="trace">
      <div className="trace-title">LangGraph run - last turn</div>
      {trace.map((step, i) => {
        const meta = Object.entries(step)
          .filter(([k, v]) => !['node', 'ms'].includes(k) && v !== null && v !== undefined)
          .map(([k, v]) => k + ': ' + (Array.isArray(v) ? v.join(', ') : v))
          .join('  |  ')
        return (
          <div className="trace-step" key={step.node + i}>
            <span className="trace-node">{step.node}</span>
            <span className="trace-meta">{meta}</span>
            <span className="trace-ms">{step.ms} ms</span>
          </div>
        )
      })}
    </div>
  )
}
