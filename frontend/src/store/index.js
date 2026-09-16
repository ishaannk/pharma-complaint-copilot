import { configureStore } from '@reduxjs/toolkit'

import complaintReducer from './complaintSlice'
import uiReducer from './uiSlice'

export const store = configureStore({
  reducer: { complaint: complaintReducer, ui: uiReducer },
})
