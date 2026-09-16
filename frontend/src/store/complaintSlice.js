import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'

import { commitComplaint, sendToCopilot } from '../api'

export const EMPTY_FORM = {
  complaint_source: '',
  customer_name: '',
  complaint_date: '',
  product_name: '',
  product_strength: '',
  batch_number: '',
  affected_quantity: '',
  manufacturing_date: '',
  expiry_date: '',
  originating_site_block: '',
  impacted_npm: '',
  complaint_category: '',
  complaint_description: '',
}

export const EMPTY_RISK = {
  severity_suggested: '',
  suggested_next_action: '',
  initial_risk_assessment: '',
  probable_root_cause: '',
  capa_recommendation: '',
  regulatory_reportable: '',
  summary: '',
  confidence: 0,
}

const GREETING = {
  role: 'assistant',
  text:
    'Ready to process new complaints. Paste the raw email from the customer, or upload a PDF of ' +
    'the complaint report. I will extract the data and run the initial risk assessment.',
}

/** One thunk for all three tools -- the backend router decides which one runs. */
export const askCopilot = createAsyncThunk(
  'complaint/askCopilot',
  async ({ message, file }, { getState, rejectWithValue }) => {
    const { complaint, ui } = getState()
    try {
      return await sendToCopilot({
        sessionId: ui.sessionId,
        message,
        file,
        form: complaint.form,
        risk: complaint.risk,
      })
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

export const commit = createAsyncThunk(
  'complaint/commit',
  async (_, { getState, rejectWithValue }) => {
    const { complaint, ui } = getState()
    try {
      return await commitComplaint({
        sessionId: ui.sessionId,
        form: complaint.form,
        risk: complaint.risk,
      })
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

const complaintSlice = createSlice({
  name: 'complaint',
  initialState: {
    form: { ...EMPTY_FORM },
    risk: { ...EMPTY_RISK },
    messages: [GREETING],
    changedFields: [],
    provenance: {},
    completeness: { score: 0, missing_fields: [], blocking: [], ready_to_commit: false },
    duplicates: [],
    trace: [],
    status: 'idle',
    committedAs: null,
    error: null,
  },
  reducers: {
    resetAll(state) {
      state.form = { ...EMPTY_FORM }
      state.risk = { ...EMPTY_RISK }
      state.messages = [GREETING]
      state.changedFields = []
      state.provenance = {}
      state.completeness = { score: 0, missing_fields: [], blocking: [], ready_to_commit: false }
      state.duplicates = []
      state.trace = []
      state.committedAs = null
      state.error = null
    },
    // The form is AI-driven per the brief, but a QA reviewer must still be able to
    // correct a field by hand before signing off -- that is a real QMS requirement.
    editField(state, action) {
      const { field, value } = action.payload
      state.form[field] = value
      state.provenance[field] = 'manual'
    },
    clearHighlights(state) {
      state.changedFields = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(askCopilot.pending, (state, action) => {
        state.status = 'loading'
        state.error = null
        const { message, file } = action.meta.arg
        state.messages.push({ role: 'user', text: message, file: file ? file.name : null })
      })
      .addCase(askCopilot.fulfilled, (state, action) => {
        const r = action.payload
        state.status = 'idle'
        state.form = r.form
        state.risk = r.risk
        state.changedFields = r.changed_fields || []
        state.provenance = { ...state.provenance, ...(r.provenance || {}) }
        state.completeness = r.completeness || state.completeness
        state.duplicates = r.duplicates || []
        state.trace = r.trace || []
        state.messages.push({ role: 'assistant', text: r.reply, intent: r.intent })
      })
      .addCase(askCopilot.rejected, (state, action) => {
        state.status = 'idle'
        state.error = action.payload || 'Request failed'
        state.messages.push({
          role: 'assistant',
          intent: 'error',
          text: 'I could not reach the AI service: ' + state.error,
        })
      })
      .addCase(commit.fulfilled, (state, action) => {
        state.committedAs = action.payload.complaint_no
      })
      .addCase(commit.rejected, (state, action) => {
        state.error = action.payload || 'Commit failed'
      })
  },
})

export const { resetAll, editField, clearHighlights } = complaintSlice.actions
export default complaintSlice.reducer
