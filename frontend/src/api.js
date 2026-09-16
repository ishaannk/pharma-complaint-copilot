/** All network access lives here so components stay declarative. */

const BASE = '/api'

async function unwrap(res) {
  if (!res.ok) {
    let detail = res.status + ' ' + res.statusText
    try {
      const body = await res.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body -- the status line is all we have */
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function sendToCopilot({ sessionId, message, file, form, risk }) {
  // Multipart, so a typed correction and an uploaded PDF can arrive in one turn.
  const body = new FormData()
  body.append('session_id', sessionId)
  body.append('message', message || '')
  body.append('form', JSON.stringify(form))
  body.append('risk', JSON.stringify(risk))
  if (file) body.append('document', file)
  return unwrap(await fetch(BASE + '/chat', { method: 'POST', body }))
}

export async function commitComplaint({ sessionId, form, risk }) {
  return unwrap(
    await fetch(BASE + '/commit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, form, risk }),
    }),
  )
}

export async function fetchLedger() {
  return unwrap(await fetch(BASE + '/complaints'))
}

export async function fetchHealth() {
  return unwrap(await fetch(BASE + '/health'))
}
