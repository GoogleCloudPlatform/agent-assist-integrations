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

const { isString, isObject } = require('lodash');
const axios = require('axios');

const { executeWithRetry, twilioExecute } = require(Runtime.getFunctions()['common/helpers/function-helper'].path);

/**
 * @param {object} parameters the parameters for the function
 * @param {object} parameters.context the context from calling lambda function
 * @param {string} parameters.callSid the unique call SID to fetch
 * @param {string} parameters.to the phone number to transfer to
 * @param {string} parameters.from optional, the phone number to use as caller id
 * @returns {object} generic response object
 * @description cold transfers the given call SID to the given phone number
 */
exports.coldTransfer = async function coldTransfer(parameters) {
  const { context, callSid, to, from } = parameters;

  if (!isObject(context)) throw new Error('Invalid parameters object passed. Parameters must contain context object');
  if (!isString(callSid)) throw new Error('Invalid parameters object passed. Parameters must contain callSid string');
  if (!isString(to)) throw new Error('Invalid parameters object passed. Parameters must contain to string');

  let callerIdStr = '';

  if (from) {
    callerIdStr = ` callerId="${from}"`;
  }

  return twilioExecute(context, (client) => {
    if (to.startsWith('sip')) {
      return client.calls(callSid).update({
        twiml: `<Response><Dial${callerIdStr}><Sip>${to}</Sip></Dial></Response>`,
      });
    }
    return client.calls(callSid).update({
      twiml: `<Response><Dial${callerIdStr}>${to}</Dial></Response>`,
    });
  });
};

/**
 * @param {object} parameters the parameters for the function
 * @param {object} parameters.context the context from calling lambda function
 * @param {string} parameters.recordingSid the recording sid to fetch
 * @returns {object} the recording audio file encoded as base64
 * @description fetches recording by sid
 */
exports.fetchRecordingMedia = async (parameters) => {
  const { recordingSid } = parameters;

  if (!isString(recordingSid))
    throw new Error('Invalid parameters object passed. Parameters must contain recordingSid string');

  const config = {
    auth: {
      username: process.env.ACCOUNT_SID,
      password: process.env.AUTH_TOKEN,
    },
    responseType: 'arraybuffer',
  };

  return executeWithRetry(parameters.context, async () => {
    const getResponse = await axios.get(
      `https://api.twilio.com/2010-04-01/Accounts/${process.env.ACCOUNT_SID}/Recordings/${recordingSid}.mp3`,
      config,
    );

    return {
      recording: getResponse?.data.toString('base64' ?? ''),
      type: getResponse?.headers['content-type'],
    };
  });
};
