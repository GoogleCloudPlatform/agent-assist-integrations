/**
 * Copyright 2024 Google LLC
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

import React, {useEffect} from 'react';
import * as Flex from '@twilio/flex-ui'; // eslint-disable-line node/no-unpublished-import
const config = {
  CONVERSATION_PROFILE: `${process.env.TWILIO_CONVERSATION_PROFILE}`,
  FEATURES: `${process.env.TWILIO_FEATURES}`,
  DEBUG: `${process.env.TWILIO_DEBUG}`,
  FUNCTIONS_URL: `${process.env.TWILIO_FUNCTIONS_URL}`,
};

const AgentAssistContainer = (): JSX.Element | null => {
  const identity =
    Flex.Manager.getInstance().store.getState().flex.session.identity;
  const conversationSid =
    Flex.Manager.getInstance().store.getState().flex.chat.messageList
      .activeConversation;
  const userToken =
    Flex.Manager.getInstance().store.getState().flex.session.ssoTokenPayload
      .token;

  const populateIframe = (
    iframe: HTMLIFrameElement,
    url: string,
    headers: string[][]
  ) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = handler;
    xhr.responseType = 'blob';
    headers.forEach((header: string[]) => {
      xhr.setRequestHeader(header[0], header[1]);
    });
    const body = JSON.stringify({Token: userToken});
    xhr.send(body);

    function handler() {
      if (xhr.readyState === XMLHttpRequest.DONE) {
        if (xhr.status === 200) {
          iframe.src = URL.createObjectURL(xhr.response);
        } else {
          console.error(xhr.response);
        }
      }
    }
  };

  useEffect(() => {
    const myIframe = document.querySelector(
      '#agentAssist'
    ) as HTMLIFrameElement | null;
    if (conversationSid !== '' && myIframe) {
      populateIframe(
        myIframe,
        `${config.FUNCTIONS_URL}/agent-assist?conversationProfile=${config.CONVERSATION_PROFILE}&conversationSid=${conversationSid}&features=${config.FEATURES}&agentIdentity=${identity}&channelType=chat&debug=${config.DEBUG}`,
        [['x-api-version', 'v1.2']]
      );
    }
  }, [conversationSid]);

  if (!conversationSid) {
    return <></>;
  }

  return <iframe id="agentAssist" src=""></iframe>;
};

AgentAssistContainer.displayName = 'AgentAssistContainer';

export default AgentAssistContainer;
