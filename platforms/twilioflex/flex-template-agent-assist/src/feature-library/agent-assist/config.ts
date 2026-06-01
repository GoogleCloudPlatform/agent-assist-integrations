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

import { object } from 'prop-types';

import { getFeatureFlags } from '../../utils/configuration';
import AgentAssistConfig from './types/ServiceConfiguration';

const {
  enabled = false,
  custom_api_endpoint = '',
  conversation_profile = '',
  conversation_summary = true,
  agent_coaching = true,
  knowledge_assist = true,
  smart_reply = true,
  enable_voice = false,
  notifier_server_endpoint = '',
  transcription = {
    enabled: false,
    version: {
      live_transcription: true,
      intermediate_transcription: false,
    },
  },
  script_sources = {
    prod: {
      common: 'https://www.gstatic.com/agent-assist-ui-modules/v1.9/common.js',
      container: 'https://www.gstatic.com/agent-assist-ui-modules/v2.0/container.js',
      summarization: 'https://www.gstatic.com/agent-assist-ui-modules/v1.3/summarization.js',
      knowledge_assist_v2: 'https://www.gstatic.com/agent-assist-ui-modules/v2.9/knowledge_assist.js',
      transcript: 'https://www.gstatic.com/agent-assist-ui-modules/v1.3/transcript.js',
      agent_coaching: 'https://www.gstatic.com/agent-assist-ui-modules/v1.1/agent_coaching.js',
      smart_reply: 'https://www.gstatic.com/agent-assist-ui-modules/v1.4/smart_reply.js',
      live_translation: 'https://www.gstatic.com/agent-assist-ui-modules/v1.3/live_translation.js',
    },
  },
  debug = false,
} = (getFeatureFlags()?.features?.agent_assist as AgentAssistConfig) || {};

export const isFeatureEnabled = () => {
  return enabled;
};

export const getCustomApiEndpoint = () => {
  return custom_api_endpoint;
};

export const getConversationProfile = () => {
  return conversation_profile;
};

export const isConversationSummaryEnabled = () => {
  return isFeatureEnabled() && conversation_summary;
};

export const isAgentCoachingEnabled = () => {
  return isFeatureEnabled() && agent_coaching;
};

export const isKnowledgeAssistEnabled = () => {
  return isFeatureEnabled() && knowledge_assist;
};

export const isSmartReplyEnabled = () => {
  return isFeatureEnabled() && smart_reply;
};

export const isVoiceEnabled = () => {
  return isFeatureEnabled() && enable_voice;
};

export const getNotifierServerEndpoint = () => {
  return notifier_server_endpoint;
};

export const isTranscriptionEnabled = () => {
  return isVoiceEnabled() && transcription.enabled;
};

export const isLiveTranscriptionEnabled = () => {
  return isTranscriptionEnabled() && transcription.version.live_transcription;
};

export const isIntermediateTranscriptionEnabled = () => {
  return isTranscriptionEnabled() && transcription.version.intermediate_transcription;
};

export const getScriptSources = () => {
  return script_sources.prod;
};

export const getEnabledFeatureList = () => {
  const features = {
    CONVERSATION_SUMMARIZATION: conversation_summary,
    SMART_REPLY: smart_reply,
    KNOWLEDGE_ASSIST_V2: knowledge_assist,
    AGENT_COACHING: agent_coaching,
  };
  const filteredFeatures = Object.fromEntries(Object.entries(features).filter(([key, value]) => value === true));
  return Object.keys(filteredFeatures).join(',');
};

export const isDebugEnabled = () => {
  return debug;
};
