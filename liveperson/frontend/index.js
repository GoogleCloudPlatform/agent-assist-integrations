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
import dotenv from 'dotenv';
import express from 'express';
import fetch from 'node-fetch';
import path, {dirname} from 'path';
import {fileURLToPath} from 'url';

dotenv.config();

const app = express();

const __dirname = dirname(fileURLToPath(import.meta.url));

app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');

app.use(express.json());

const {
  LP_SENTINEL_DOMAIN,
  LP_CLIENT_ID,
  LP_ACCOUNT_ID,
  LP_CLIENT_SECRET,
  APPLICATION_SERVER_URL,
  DF_PROXY_SERVER_URL,
} = process.env;

const LP_AUTHORIZATION_URI = `https://${
    LP_SENTINEL_DOMAIN}/sentinel/api/account/${LP_ACCOUNT_ID}/authorize?v=1.0`;
const LP_ACCESS_TOKEN_URI = `https://${
    LP_SENTINEL_DOMAIN}/sentinel/api/account/${LP_ACCOUNT_ID}/token?v=1.0`;

const client = new ClientOAuth2({
  clientId: LP_CLIENT_ID,
  clientSecret: LP_CLIENT_SECRET,
  redirectUri: `${APPLICATION_SERVER_URL}/home`,
  authorizationUri: LP_AUTHORIZATION_URI,
  accessTokenUri: LP_ACCESS_TOKEN_URI,
});

/**
 * Entry point for the LivePerson OAuth flow.
 *
 * This is the 'entry_uri' specified in the Conversational Cloud app
 * registration.
 */
app.get('/', (req, res) => {
  const {conversationProfile, features} = req.query;

  const state = Buffer.from(JSON.stringify({conversationProfile, features}))
                    .toString('base64url');

  const redirectUri = client.code.getUri({state});

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

  const decodedState =
      JSON.parse(Buffer.from(state, 'base64url').toString('ascii'));

  const authEntryPointUrl = new URL(APPLICATION_SERVER_URL);
  authEntryPointUrl.searchParams.set(
      'conversationProfile', decodedState.conversationProfile);
  authEntryPointUrl.searchParams.set('features', decodedState.features);

  const authEntryPoint = authEntryPointUrl.toString();

  // If no code or error is present, redirect user to the standard auth flow.
  if (!code && !error) {
    res.redirect(authEntryPoint);
    return;
  }

  try {
    const response = await client.code.getToken(req.originalUrl, {
      body: {
        client_id: LP_CLIENT_ID,
        client_secret: LP_CLIENT_SECRET,
      },
    });

    const jwtResponse = await fetch(`${DF_PROXY_SERVER_URL}/auth/token`, {
      headers: [['Authorization', response.accessToken]],
    });

    if (jwtResponse.status === 200) {
      res.render('home', {
        state: decodedState,
        proxyServer: DF_PROXY_SERVER_URL,
        accessToken: (await jwtResponse.json()).token,
        authResponse: response.data,
        authEntryPoint,
      });
    } else {
      res.render('home', {authResponse: null});
    }
  } catch (error) {
    if (error.toString().includes('Client authentication failed')) {
      res.redirect(authEntryPoint);
    } else {
      console.log('[ERROR] [LivePerson token] ', error);
      res.render('home', {authResponse: null});
    }
  }
});

const PORT = process.env.PORT || 8080;

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
