import React, { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import { askCopilot } from '../store/complaintSlice'
import WorkflowTrace from './WorkflowTrace'

// Inline so they inherit currentColor and stay crisp in both themes; emoji glyphs
// render thin and inconsistently across platforms.
const Icon = ({ d, size = 17 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d={d} />
  </svg>
)

const CLIP = 'M21.44 11.05 12.25 20.24a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48'
const CHECK = 'M20 6 9 17l-5-5'

const STARTERS = [
  'Apollo Pharmacy reported discolored capsules in Amoxicillin Capsules 500 mg. Batch number AMX240602. Manufacturing date March 2026. Expiry date February 2028. Please log this complaint',
  'Sorry, the batch number is BMX240602 and the affected quantity is 48 capsules',
  'Why did you classify this as Major?',
]

export default function Copilot() {
  const dispatch = useDispatch()
  const { messages, status, form } = useSelector((s) => s.complaint)
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const threadRef = useRef(null)
  const fileRef = useRef(null)

  const busy = status === 'loading'
  const hasComplaint = Object.values(form).some(Boolean)

  useEffect(() => {
    const el = threadRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, busy])

  const submit = (override) => {
    const message = (override ?? text).trim()
    if ((!message && !file) || busy) return
    dispatch(askCopilot({ message, file }))
    setText('')
    setFile(null)
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }

  return (
    <section className="pane">
      <header className="copilot-head">
        <span aria-hidden="true">&#9889;</span>
        <div>
          <h2>AIVOA Copilot</h2>
          <p>Drop complaint files or paste text below.</p>
        </div>
        <span
          className={'live-dot' + (busy ? ' busy' : '')}
          title={busy ? 'Running the workflow' : 'Ready'}
        />
      </header>

      <div className="thread" ref={threadRef} aria-live="polite">
        {messages.map((m, i) => (
          <div className={'msg ' + m.role + (m.intent === 'error' ? ' error' : '')} key={i}>
            <div className="avatar" aria-hidden="true">
              {m.role === 'user' ? String.fromCodePoint(0x1f9d1) : String.fromCodePoint(0x1f9ea)}
            </div>
            <div>
              {m.file && (
                <div className="file-chip">
                  <span aria-hidden="true">&#128196;</span>
                  <span>{m.file}</span>
                </div>
              )}
              {m.text && <div className="bubble">{m.text}</div>}
            </div>
          </div>
        ))}
        {busy && (
          <div className="msg assistant">
            <div className="avatar" aria-hidden="true">
              {String.fromCodePoint(0x1f9ea)}
            </div>
            <div className="bubble typing" aria-label="Copilot is working">
              <i />
              <i />
              <i />
            </div>
          </div>
        )}
      </div>

      <WorkflowTrace />

      <div
        className={'composer' + (dragging ? ' drag' : '')}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        {messages.length <= 1 && (
          <div className="suggestions">
            {STARTERS.slice(0, hasComplaint ? 3 : 1).map((s) => (
              <button className="suggestion" key={s} onClick={() => submit(s)}>
                {s.length > 74 ? s.slice(0, 74) + '...' : s}
              </button>
            ))}
          </div>
        )}

        {file && (
          <div className="file-chip">
            <span aria-hidden="true">&#128196;</span>
            <span>{file.name}</span>
            <button
              className="attach"
              style={{ width: 22, height: 22 }}
              onClick={() => setFile(null)}
              aria-label={'Remove ' + file.name}
            >
              &times;
            </button>
          </div>
        )}

        <div className="composer-row">
          <input
            ref={fileRef}
            type="file"
            hidden
            accept=".pdf,.docx,.txt,.eml"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <button
            className="attach"
            onClick={() => fileRef.current?.click()}
            aria-label="Attach a complaint document"
            title="Attach PDF, DOCX, TXT or EML"
          >
            <Icon d={CLIP} />
          </button>
          <textarea
            rows={1}
            value={text}
            placeholder="Type a message or paste a complaint..."
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            aria-label="Message the Copilot"
          />
          <button
            className="send"
            onClick={() => submit()}
            disabled={busy || (!text.trim() && !file)}
            aria-label="Send"
          >
            <Icon d={CHECK} size={16} />
          </button>
        </div>
        <div className="powered">Powered by LangGraph</div>
      </div>
    </section>
  )
}
