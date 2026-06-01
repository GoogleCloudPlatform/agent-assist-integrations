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
import { Router } from 'express';
import jwt from 'jsonwebtoken';
import fetch from 'node-fetch';
import path from 'path';

import {
  generateProxyAccessToken,
  generateProxyRefreshToken,
} from '../../helpers/auth_helpers';
import { decrypt } from '../../helpers/crypto_helpers';

dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

const {
  APPLICATION_SERVER_URL,
  LP_ACCOUNT_CONFIG_READONLY_DOMAIN,
  LP_ACCOUNT_ID,
  LP_CLIENT_ID,
  LP_CLIENT_SECRET,
  LP_SENTINEL_DOMAIN,
} = process.env;

const LP_AUTHORIZATION_URI = `https://${LP_SENTINEL_DOMAIN}/sentinel/api/account/${LP_ACCOUNT_ID}/authorize?v=1.0`;
const LP_ACCESS_TOKEN_URI = `https://${LP_SENTINEL_DOMAIN}/sentinel/api/account/${LP_ACCOUNT_ID}/token?v=1.0`;

const client = new ClientOAuth2({
  clientId: LP_CLIENT_ID,
  clientSecret: LP_CLIENT_SECRET,
  authorizationUri: LP_AUTHORIZATION_URI,
  accessTokenUri: LP_ACCESS_TOKEN_URI,
  redirectUri: `${APPLICATION_SERVER_URL}/home`,
});

const router = Router();

/**
 * Uses the client's LivePerson OAuth token to generate a proxy server-specific
 * access token and refresh token.
 */
router.post('/token', async (req, res) => {
  try {
    const redirectUri = JSON.parse(req.body).redirectUri;

    const { accessToken, refreshToken } = await client.code.getToken(
      redirectUri,
      {
        body: {
          client_id: LP_CLIENT_ID,
          client_secret: LP_CLIENT_SECRET,
        },
      }
    );

    // Call LP API with credentials
    const statusReasonsResponse = await fetch(
      `https://${LP_ACCOUNT_CONFIG_READONLY_DOMAIN}/api/account/${LP_ACCOUNT_ID}/configuration/le-agents/status-reasons`,
      {
        headers: [['Authorization', `Bearer ${accessToken}`]],
      }
    );

    const { status } = statusReasonsResponse;

    if (status === 200) {
      const proxyAccessToken = generateProxyAccessToken();
      const proxyRefreshToken = generateProxyRefreshToken(refreshToken);

      res.json({
        accessToken: proxyAccessToken,
        refreshToken: proxyRefreshToken,
      });
      return;
    }

    console.error(
      `[ERROR] [Proxy server] [/auth/token]: status reasons ${status}`
    );

    if (status === 401 || status === 403) {
      res.status(statusReasonsResponse.status).json({
        error: 'Could not authenticate user',
      });
    } else {
      res
        .status(status)
        .json({ error: 'Error verifying LivePerson authentication token' });
    }
  } catch (error) {
    const errorMessage = error.toString();
    console.error('[ERROR] [Proxy server] [/auth/token]: ', errorMessage);
    if (errorMessage.includes('Client authentication failed')) {
      res.status(401).json({ error: 'Client authentication failed' });
    } else {
      res.status(500).json({ error: errorMessage });
    }
  }
});

/**
 * Refreshes the client's proxy server access token using a refresh token
 * returned to the client.
 */
router.post('/refresh', async (req, res) => {
  const proxyRefreshToken = JSON.parse(req.body).refreshToken;

  try {
    const jwtPayload = jwt.verify(proxyRefreshToken, process.env.JWT_SECRET);

    if (typeof jwtPayload !== 'object' || jwtPayload.type !== 'refresh') {
      throw new Error('Invalid refresh token payload.');
    }

    const refreshToken = decrypt(jwtPayload.token);

    const response = await fetch(LP_ACCESS_TOKEN_URI, {
      method: 'POST',
      headers: [
        ['Content-Type', 'application/x-www-form-urlencoded;charset=UTF-8'],
      ],
      body: new URLSearchParams([
        ['grant_type', 'refresh_token'],
        ['refresh_token', refreshToken],
        ['client_id', LP_CLIENT_ID],
        ['client_secret', LP_CLIENT_SECRET],
      ]).toString(),
    });

    if (response.status === 200) {
      const newProxyAccessToken = generateProxyAccessToken();
      const newProxyRefreshToken = generateProxyRefreshToken(refreshToken);
      res.status(200).json({
        accessToken: newProxyAccessToken,
        refreshToken: newProxyRefreshToken,
      });
    } else {
      console.error(
        `[ERROR] [Proxy server] [/auth/refresh]: LP refresh ${response.status}`
      );
      res.status(response.status).json({ error: 'Could not refresh token' });
    }
  } catch (err) {
    console.error('[ERROR] [Proxy server] [/auth/refresh]: ', err);
    res.status(500).json({ error: 'Could not refresh token' });
  }
});

export { router as authRouter };
