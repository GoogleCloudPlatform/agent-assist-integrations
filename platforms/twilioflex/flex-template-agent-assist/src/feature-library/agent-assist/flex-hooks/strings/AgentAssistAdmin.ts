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
  ConnectingToCustomApiEndpointError = 'CCAIConnectingToCustomApiEndpointError',
  ConnectingToCustomApiEndpointSuccess = 'CCAIConnectingToCustomApiEndpointSuccess',
  ConnectingToNotifierServerEndpointError = 'CCAIConnectingToNotifierServerEndpointError',
  ConnectingToNotifierServerEndpointSuccess = 'CCAIConnectingToNotifierServerEndpointSuccess',
  ConversationProfileErrorText = 'CCAIConversationProfileErrorText',
  TestConnectionCTA = 'CCAITestConnectionCTA',
  AgentCoachingHelperText = 'CCAIAgentCoachingHelperText',
  ConversationSummarizationHelperText = 'CCAIConversationSummarizationHelperText',
  KnowledgeAssistHelperText = 'CCAIKnowledgeAssistHelperText',
  SmartReplyHelperText = 'CCAISmartReplyHelperText',
  LiveTranscriptionHelperText = 'CCAILiveTranscriptionHelperText',
  IntermediateTranscriptionHelperText = 'CCAIIntermediateTranscriptionHelperText',
  TestConversationProfileCTA = 'CCAITestConversationProfileCTA',
  ValidateConversationProfileError = 'CCAIValidateConversationProfileError',
  ValidateConfigSuccess = 'CCAIValidateConversationProfileSuccess',
}

export const stringHook = () => ({
  'en-US': {
    [StringTemplates.ConnectingToCustomApiEndpointError]: 'Error establishing connection to the custom api endpoint.',
    [StringTemplates.ConnectingToCustomApiEndpointSuccess]: 'Connection to the custom api endpoint successful.',
    [StringTemplates.ConnectingToNotifierServerEndpointError]:
      'Error establishing connection to the notifier server endpoint.',
    [StringTemplates.ConnectingToNotifierServerEndpointSuccess]:
      'Connection to the notifier server endpoint successful.',
    [StringTemplates.ConversationProfileErrorText]:
      'Enter a conversation profile with the format projects/PROJECT_ID/locations/LOCATION/conversationProfiles/PROFILE_ID',
    [StringTemplates.TestConnectionCTA]: 'Test Connection',
    [StringTemplates.AgentCoachingHelperText]:
      'Provide agents with suggestions for how they should respond during a customer service conversation.',
    [StringTemplates.ConversationSummarizationHelperText]: "Provide summaries to your agents during a conversation.",
    [StringTemplates.KnowledgeAssistHelperText]:
      "Provide answers to your agent's questions based on information in documents you provide.",
    [StringTemplates.SmartReplyHelperText]:
      'Provide agents with suggested responses are calculated by a custom model that has been trained on your own conversation data.',
    [StringTemplates.LiveTranscriptionHelperText]: 'Support transcription after a user is done speaking.',
    [StringTemplates.IntermediateTranscriptionHelperText]: 'Supports transcription as a user is speaking.',
    [StringTemplates.TestConversationProfileCTA]: 'Validate Conversation Profile.',
    [StringTemplates.ValidateConversationProfileError]: 'Conversation Profile Error.',
    [StringTemplates.ValidateConfigSuccess]: 'Configuration values validated.',
  },
});
