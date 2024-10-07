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

// Imports global types
import '@twilio-labs/serverless-runtime-types';
import {
  Context,
  ServerlessCallback,
  ServerlessFunctionSignature,
} from '@twilio-labs/serverless-runtime-types/types';
import ejs from 'ejs';

const TokenValidator = require('twilio-flex-token-validator').functionValidator;

type AgentAssistContext = {
  PROXY_SERVER_URL?: string;
  APPLICATION_SERVER_URL?: string;
  TWILIO_ACCOUNT_SID?: string;
  TWILIO_API_KEY?: string;
  TWILIO_API_SECRET?: string;
  TWILIO_CHAT_SERVICE_SID?: string;
};

interface RequestParameters {
  conversationProfile?: string;
  conversationId?: string;
  features?: string;
  agentIdentity?: string;
  channelType?: string;
  debug?: string;
  Token?: string;
}

const generateChatToken = (
  context: Context<AgentAssistContext>,
  identity: string
): string => {
  // Used when generating any kind of tokens
  // To set up environmental variables, see http://twil.io/secure
  const twilioAccountSid = `${context.TWILIO_ACCOUNT_SID}`;
  const twilioApiKey = `${context.TWILIO_API_KEY}`;
  const twilioApiSecret = `${context.TWILIO_API_SECRET}`;

  // Used specifically for creating Chat tokens
  const serviceSid = context.TWILIO_CHAT_SERVICE_SID;

  // Create a "grant" which enables a client to use Chat as a given user,
  // on a given device
  const AccessToken = Twilio.jwt.AccessToken;
  const ChatGrant = AccessToken.ChatGrant;
  const chatGrant = new ChatGrant({
    serviceSid: serviceSid,
  });

  // Create an access token which we will sign and return to the client,
  // containing the grant we just created
  const token = new AccessToken(
    twilioAccountSid,
    twilioApiKey,
    twilioApiSecret,
    {identity: identity}
  );

  token.addGrant(chatGrant);
  return token.toJwt();
};

export const handler: ServerlessFunctionSignature = TokenValidator(
  async (
    context: Context<AgentAssistContext>,
    event: RequestParameters,
    callback: ServerlessCallback
  ) => {
    const {
      conversationProfile,
      channelType,
      features,
      debug,
      conversationId,
      agentIdentity,
      Token,
    } = event;
    // Create a custom Twilio Response
    // Set the CORS headers to allow Flex to make an HTTP request to the Twilio Function
    const response = new Twilio.Response();
    response.appendHeader('Access-Control-Allow-Origin', '*');
    response.appendHeader('Access-Control-Allow-Methods', 'OPTIONS POST GET');
    response.appendHeader('Access-Control-Allow-Headers', '*');
    response.appendHeader('Content-Type', 'text/html');

    const [, projectLocation] =
      // @ts-ignore
      conversationProfile.match(
        /(^projects\/[^/]+\/locations\/[^/]+)\/conversationProfiles\/[^/]+$/
      ) || [];

    const chatToken = generateChatToken(context, `${agentIdentity}`);
    const conversationName = `${projectLocation}/conversations/${conversationId}`;

    const openFile = Runtime.getAssets()['/main.ejs'].open;
    const htmlTemplate = openFile();
    const html = ejs.render(htmlTemplate, {
      proxyServer: context.PROXY_SERVER_URL,
      applicationServer: context.APPLICATION_SERVER_URL,
      conversationProfile,
      conversationName,
      conversationSid: conversationId,
      agentToken: Token,
      chatToken,
      channelType,
      agentIdentity,
      features,
      debug,
    });


    response.setStatusCode(200);
    response.setBody(html);

    callback(null, response);
  }
);
