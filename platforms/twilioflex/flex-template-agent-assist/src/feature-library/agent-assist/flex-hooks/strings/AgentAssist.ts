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

// Export the template names as an enum for better maintainability when accessing them elsewhere
export enum StringTemplates {
  AgentAssist = 'CCAIAgentAssist',
  ErrorFetching = 'CCAIAgentAssistErrorFetching',
  AgentAssistConnected = 'CCAIAgentAssistConnected',
  AgentAssistDisconnected = 'CCAIAgentAssistDisconnected',
  ConversationSummarization = 'CCAIConversationSummarizationTab',
  KnowledgeAssist = 'CCAIKnowledgeAssist',
  Transcription = 'CCAITranscription',
  LiveTranscription = 'CCAILiveTranscription',
  IntermediateTranscription = 'CCAIIntermediateTranscription',
  AgentCoaching = 'CCAIAgentCoaching',
  SmartReply = 'CCAISmartReply',
  ConversationProfile = 'CCAIConversationProfile',
  CustomApiEndpoint = 'CCAICustomApiEndpoint',
  NotiferServerEnpoint = 'CCAINotifierServerEndpoint',
  Debug = 'CCAIDebug',
}

export const stringHook = () => ({
  'en-US': {
    [StringTemplates.AgentAssist]: 'Google CES Agent Assist',
    [StringTemplates.ErrorFetching]: 'There was an error starting Agent Assist. Please reload the page.',
    [StringTemplates.AgentAssistConnected]: 'Google CES Agent Assist connected',
    [StringTemplates.AgentAssistDisconnected]: 'Google CES Agent Assist disconnected',
    [StringTemplates.ConversationSummarization]: 'Conversation Summarization',
    [StringTemplates.KnowledgeAssist]: 'Knowledge Assist',
    [StringTemplates.Transcription]: 'Transcription',
    [StringTemplates.LiveTranscription]: 'Live Transcription',
    [StringTemplates.IntermediateTranscription]: 'Intermediate Transcription',
    [StringTemplates.AgentCoaching]: 'Agent Coaching',
    [StringTemplates.ConversationProfile]: 'Conversation Profile',
    [StringTemplates.SmartReply]: 'Smart Reply',
    [StringTemplates.CustomApiEndpoint]: 'Custom API Endpoint',
    [StringTemplates.NotiferServerEnpoint]: 'Notifier Server Endpoint',
    [StringTemplates.Debug]: 'Debug',
  },
});
