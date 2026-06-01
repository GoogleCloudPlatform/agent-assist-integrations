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

const fs = require("fs");
const twilio = require("twilio");

// .
exports.handler = async (context, event, callback) => {
  const response = new Twilio.Response();

  const { apiKey, apiSecret, assetKey } = event;

  try {
    const client = twilio(apiKey, apiSecret, {
      accountSid: context.ACCOUNT_SID,
    });
    await client.serverless.v1.services(context.SERVICE_SID).fetch();
  } catch (error) {
    response.setBody("Unauthorized");
    response.setStatusCode(401);
    return callback(null, response);
  }

  const path = Runtime.getAssets()[`/${assetKey}`].path;

  const data = fs.readFileSync(path);

  response.appendHeader("Content-Type", "application/gzip");
  response.appendHeader(
    "Content-Disposition",
    `attachment; filename="${assetKey}"`
  );

  response.setBody(data);

  return callback(null, response);
};
