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

import AgentAssistConfig from '../../../types/ServiceConfiguration';

export interface AgentAssistAdminState extends Omit<AgentAssistConfig, 'enabled'> {
  hasError: boolean;
}

const initialState = {
  conversation_profile: '',
  custom_api_endpoint: '',
  agent_coaching: false,
  conversation_summary: false,
  knowledge_assist: false,
  smart_reply: false,
  enable_voice: false,
  notifier_server_endpoint: '',
  transcription: {
    enabled: false,
    version: {
      live_transcription: true,
      intermediate_transcription: false,
    },
  },
  debug: false,
  hasError: false,
} as AgentAssistAdminState;

const agentAssistAdminSlice = createSlice({
  name: 'agentAssistAdmin',
  initialState,
  reducers: {
    updateAgentAssistAdminState(state, action: PayloadAction<Partial<AgentAssistAdminState>>) {
      return { ...state, ...action.payload };
    },
  },
});
export const { updateAgentAssistAdminState } = agentAssistAdminSlice.actions;
export const reducerHook = () => ({ agentAssistAdmin: agentAssistAdminSlice.reducer });
export default agentAssistAdminSlice.reducer;
