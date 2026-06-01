/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

export interface AgentAssistState {
  status: string;
  authToken: string;
}

const initialState = {
  status: 'disconnected',
  authToken: '',
} as AgentAssistState;

const agentAssistSlice = createSlice({
  name: 'agentAssist',
  initialState,
  reducers: {
    updateAgentAssistState(state, action: PayloadAction<AgentAssistState>) {
      state.status = action.payload.status;
      state.authToken = action.payload.authToken;
    },
  },
});
export const { updateAgentAssistState } = agentAssistSlice.actions;
export const reducerHook = () => ({ agentAssist: agentAssistSlice.reducer });
export default agentAssistSlice.reducer;
