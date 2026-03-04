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

export interface Transcription {
  enabled: boolean;
  version: {
    live_transcription: boolean;
    intermediate_transcription: boolean;
  };
}

type env_options = 'prod';

interface AgentAssistScripts {
  common: string;
  container: string;
  summarization: string;
  knowledge_assist: string;
  transcript: string;
  agent_coaching: string;
  smart_reply: string;
  live_translation: string;
}

export default interface AgentAssistConfig {
  enabled: boolean;
  custom_api_endpoint: string;
  conversation_profile: string;
  conversation_summary: boolean;
  agent_coaching: boolean;
  knowledge_assist: boolean;
  smart_reply: boolean;
  enable_voice: boolean;
  notifier_server_endpoint: string;
  transcription: Transcription;
  script_sources: {
    staging: AgentAssistScripts;
    prod: AgentAssistScripts;
  };
  ui_module_version: env_options;
  debug: boolean;
}
