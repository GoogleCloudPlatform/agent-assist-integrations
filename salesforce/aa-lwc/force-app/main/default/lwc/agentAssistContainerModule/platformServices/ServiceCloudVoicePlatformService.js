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

import TwilioFlexPlatformService from './TwilioFlexPlatformService';

import scvEventNames from "../data/scvEventNames";
import BasePlatformService from "./BasePlatformService";
const SCV_EVENTS_TO_SUBSCRIBE = [
  scvEventNames.callconnected,
  scvEventNames.callended
];

// SCV telephony config
const CONFIG = {
  // For this.platform = "servicecloudvoice-nice", the Nice Business Unit Number
  // https://help.nicecxone.com/content/acd/businessunits/managebusinessunit.htm
  niceBusNo: 1234567 // TODO: make sure this matches your Nice CXone Business Unit Number.
};

export default class ServiceCloudVoicePlatformService extends BasePlatformService {
  constructor(lwc, refs) {
    super(lwc, refs);
    this.telephonyEventListener = this.onTelephonyEvent.bind(this);
  }

  ////////////////////////////////////////////////////////////////////////////
  // Init & Teardown
  ////////////////////////////////////////////////////////////////////////////

  init() {
    // Set up Agent Assist UIM to work with Service Cloud Voice.
    this.lwc.debugLog("initServiceCloudVoice called");
    this.lwc.debugLog(`this.lwc.vendorCallKey: ${this.lwc.vendorCallKey}`);
    const toolkitApi = this.refs.serviceCloudVoiceToolkitApi;
    if (!toolkitApi) return;
    this.unsubscribeFromVoiceToolkit(toolkitApi, this.telephonyEventListener);
    this.subscribeToVoiceToolkit(toolkitApi, this.telephonyEventListener);
  }

  teardown() {
    super.teardown();
    // Teardown Agent Assist UIM Service Cloud Voice.
  }

  ////////////////////////////////////////////////////////////////////////////
  // Setup Event Listeners and Subscriptions
  ////////////////////////////////////////////////////////////////////////////

  subscribeToVoiceToolkit(toolkitApi, telephonyEventListener) {
    this.lwc.debugLog(`subscribeToVoiceToolkit: ${SCV_EVENTS_TO_SUBSCRIBE}`);
    for (const eventName of SCV_EVENTS_TO_SUBSCRIBE) {
      toolkitApi.addEventListener(eventName, telephonyEventListener);
    }
  }

  unsubscribeFromVoiceToolkit(toolkitApi, telephonyEventListener) {
    this.lwc.debugLog(
      `unsubscribeFromVoiceToolkit: ${SCV_EVENTS_TO_SUBSCRIBE}`
    );
    for (const eventName of SCV_EVENTS_TO_SUBSCRIBE) {
      toolkitApi.removeEventListener(eventName, telephonyEventListener);
    }
  }

  ////////////////////////////////////////////////////////////////////////////
  // Handle Events
  ////////////////////////////////////////////////////////////////////////////

  onTelephonyEvent(event) {
    this.lwc.debugLog(
      `[onTelephonyEvent ${event.type}]: ${JSON.stringify(event)}`
    );

    // If the event has a callId and it doesn't match the current vendorCallKey,
    // ignore the event as it's for a different call instance.
    if (
      event.detail &&
      event.detail.callId &&
      this.lwc.vendorCallKey !== event.detail.callId
    ) {
      this.lwc.debugLog(
        `Ignoring event for different callId. Current: ${this.lwc.vendorCallKey}, Event: ${event.detail.callId}`
      );
      return;
    }

    switch (event.type) {
      case scvEventNames.callconnected:
        this.handleCallConnected(event);
        break;
      case scvEventNames.callended:
        this.handleCallEnded(event);
        break;
      default:
        this.lwc.debugLog(`Unhandled SCV event type: ${event.type}`);
    }
  }

  handleCallConnected(event) {
    // Compare the SCV telephony event's callId to SF VoiceCall record's VendorCallKey.
    // This is most likely also the BYOT telephony platform's external unique call id,
    // which can be used to construct telephony platform specific DF conversationName.
    if (this.lwc.platform.includes("nice")) {
      this._handleNiceCallConnected(event);
    } else {
      this.lwc.debugLog("Unsupported SCV telephony platform.");
    }
  }

  handleCallEnded(event) {
    this.lwc.debugLog("handleConversationEndedForServiceCloudVoice called");
    if (this.lwc.features.includes("CONVERSATION_SUMMARIZATION")) {
      this.lwc.triggerSummarization();
    }
  }

  _handleNiceCallConnected(event) {
    // Generate Nice CXone (Agent Assist Hub) formatted conversationName.
    const prefix = this.lwc.projectLocationName;
    this.lwc.conversationId = `BusNo-${CONFIG.niceBusNo}_ContactId-${event.detail.callId}`;
    this.lwc.conversationName = `${prefix}/conversations/${this.lwc.conversationId}`;
  }
}
