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

import ClientOAuth2 from 'client-oauth2';
import timeout from 'connect-timeout';
import cookieParser from 'cookie-parser';
import { createHmac } from 'crypto';
import dotenv from 'dotenv';
import express from 'express';
import fetch from 'node-fetch';
import path, { dirname } from 'path';
import { fileURLToPath } from 'url';
import { uuid } from 'uuidv4';

dotenv.config();

const app = express();

const __dirname = dirname(fileURLToPath(import.meta.url));

app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');

// Set 30s timeout for all requests.
// Following instructions from
// https://github.com/expressjs/timeout#as-top-level-middleware)
app.use(timeout('30s'));
app.use(express.json());
app.use(haltOnTimedout);
app.use(cookieParser());
app.use(haltOnTimedout);

function haltOnTimedout(req, res, next) {
  if (!req.timedout) next();
}

const {
  LP_SENTINEL_DOMAIN,
  LP_CLIENT_ID,
  LP_ACCOUNT_ID,
  LP_CLIENT_SECRET,
  APPLICATION_SERVER_URL,
  DF_PROXY_SERVER_URL,
  SECRET_PHRASE,
} = process.env;

const LP_AUTHORIZATION_URI = `https://${LP_SENTINEL_DOMAIN}/sentinel/api/account/${LP_ACCOUNT_ID}/authorize?v=1.0`;
const LP_ACCESS_TOKEN_URI = `https://${LP_SENTINEL_DOMAIN}/sentinel/api/account/${LP_ACCOUNT_ID}/token?v=1.0`;

const client = new ClientOAuth2({
  clientId: LP_CLIENT_ID,
  clientSecret: LP_CLIENT_SECRET,
  redirectUri: `${APPLICATION_SERVER_URL}/home`,
  authorizationUri: LP_AUTHORIZATION_URI,
  accessTokenUri: LP_ACCESS_TOKEN_URI,
});

const getHmacHasher = () => createHmac('sha256', SECRET_PHRASE);

const getAuthEntryPoint = state => {
  const entryPointUrl = new URL(APPLICATION_SERVER_URL);
  entryPointUrl.searchParams.set(
    'conversationProfile',
    state.conversationProfile
  );
  entryPointUrl.searchParams.set('features', state.features);

  return entryPointUrl.toString();
};

/**
 * Entry point for the LivePerson OAuth flow.
 *
 * This is the 'entry_uri' specified in the Conversational Cloud app
 * registration.
 */
app.get('/', (req, res) => {
  const { conversationProfile, features } = req.query;

  // A random ID to associate with this request. This will be included
  // in the request as well as cached in the client browser. When the OAuth flow
  // is finished redirecting, we will verify that the two IDs match.
  const requestId = uuid();
  const hashedRequestId = getHmacHasher().update(requestId).digest('hex');

  const state = Buffer.from(
    JSON.stringify({
      conversationProfile,
      features,
      requestId: hashedRequestId,
    })
  ).toString('base64url');

  res.setHeader('Set-Cookie', `requestId=${requestId}; SameSite=None; Secure`);

  const redirectUri = client.code.getUri({ state });

  res.redirect(redirectUri);
});

/**
 * UI Modules application home page.
 *
 * This is the 'redirect_uri' specified in the Conversational Cloud app
 * registration. User will be redirected here once they have been authenticated
 * using their LivePerson credentials.
 */
app.get('/home', async (req, res) => {
  const code = String(req.query.code || '');
  const error = String(req.query.error || '');
  const state = String(req.query.state || '');
  const { requestId } = req.cookies;
  const hashedRequestId = getHmacHasher().update(requestId).digest('hex');
  let decodedState;

  try {
    decodedState = JSON.parse(
      Buffer.from(state, 'base64url').toString('ascii')
    );

    if (!decodedState.conversationProfile || !decodedState.features) {
      throw new Error();
    }
  } catch {
    res
      .status(500)
      .send(
        'Invalid request. Please specify a valid conversation profile and ' +
          "features list in your entrypoint URL's query parameters.\n\n" +
          'Example: https://my-application.com?conversationProfile=projects/foo/locations/global/conversationProfiles/bar&features=SMART_REPLY,ARTICLE_SUGGESTION'
      );
    return;
  }

  if (decodedState.requestId !== hashedRequestId) {
    res
      .status(500)
      .send('Invalid request. Please clear your cookies and try again.');
    return;
  }

  const authEntryPoint = getAuthEntryPoint(decodedState);

  // If no code or error is present, redirect user to the standard auth flow.
  if (!code && !error) {
    res.redirect(authEntryPoint);
    return;
  }

  res.render('home');
});

/**
 * Fetches a LivePerson authentication token using the authorization code from
 * the OAuth redirect.
 */
app.get('/auth', async (req, res) => {
  let authEntryPoint;
  const { referer } = req.headers;

  if (!referer) {
    const errorMessage = 'No referer header in request';
    console.log('[ERROR] [Application server] [/auth]: ', errorMessage);
    res.status(500).json({ error: errorMessage });
    return;
  }

  try {
    const redirectUri = new URL(referer);

    const decodedState = JSON.parse(
      Buffer.from(redirectUri.searchParams.get('state'), 'base64url').toString(
        'ascii'
      )
    );
    authEntryPoint = getAuthEntryPoint(decodedState);

    const tokenResponse = await fetch(`${DF_PROXY_SERVER_URL}/auth/token`, {
      method: 'POST',
      headers: [['Content-Type', 'application/json']],
      body: JSON.stringify({
        redirectUri: `${
          redirectUri.pathname
        }?${redirectUri.searchParams.toString()}`,
      }),
    });

    if (tokenResponse.status === 200) {
      const { accessToken, refreshToken } = await tokenResponse.json();
      res.json({
        state: decodedState,
        proxyServer: DF_PROXY_SERVER_URL,
        accessToken,
        refreshToken,
      });
    } else {
      const { error } = await tokenResponse.json();
      console.log('[ERROR] [Application server] [/auth]: ', error);
      res.status(tokenResponse.status).json({ error, authEntryPoint });
    }
  } catch (error) {
    const errorMessage = error.toString();
    console.log('[ERROR] [Application server] [/auth]: ', errorMessage);
    res.status(500).json({
      error: errorMessage,
      authEntryPoint,
    });
  }
});

const PORT = process.env.PORT || 8080;

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
