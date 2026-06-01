/**
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Request, Response } from 'express';
import { GoogleAuth } from 'google-auth-library';

/** Gets the target location from a URL path. */
function getTargetLocation(path: string) {
  const [, location] =
    path.match(/\/projects\/[^/]+\/locations\/([^/]+)/) || [];

  return location || 'global';
}

/** Gets the Dialogflow API endpoint for a given location. */
function getRegionalDialogflowApiEndpoint(location: string | null | undefined) {
  const prefix = (!location || location === 'global') ? '' : `${location}-`;

  return `https://${prefix}dialogflow.googleapis.com`;
}

function getTargetUrl(path: string) {
  const location = getTargetLocation(path);
  const apiEndpoint = getRegionalDialogflowApiEndpoint(location);

  return `${apiEndpoint}${path}`;
}

const auth = new GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/dialogflow'],
});

/** Default handler for all GET requests. */
export const getHandler = async (req: Request, res: Response) => {
  try {
    const client = await auth.getClient();
    const url = getTargetUrl(req.originalUrl);
    const response = await client.request({ url });
    res.status(response.status).json(response.data);
  } catch (err) {
    res.status(err.response.status).json(err.response.data);
  }
};

/** Default handler for all POST requests. */
export const postHandler = async (req: Request, res: Response) => {
  try {
    const client = await auth.getClient();
    const url = getTargetUrl(req.originalUrl);
    const response = await client.request({
      url,
      method: 'POST',
      body: req.body,
    });
    res.status(response.status).json(response.data);
  } catch (err) {
    res.status(err.response.status).json(err.response.data);
  }
};

/** Default handler for all PATCH requests. */
export const patchHandler = async (req: Request, res: Response) => {
  try {
    const client = await auth.getClient();
    const url = getTargetUrl(req.originalUrl);
    const response = await client.request({
      url,
      method: 'PATCH',
      body: req.body,
    });
    res.status(response.status).json(response.data);
  } catch (err) {
    res.status(err.response.status).json(err.response.data);
  }
};
