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

import dotenv from 'dotenv';
import {Router} from 'express';
import jwt from 'jsonwebtoken';
import fetch from 'node-fetch';
import path from 'path';

dotenv.config({path: path.resolve(__dirname, '../../../.env')});

const router = Router();

const {
  LP_SENTINEL_DOMAIN,
  LP_ACCOUNT_CONFIG_READONLY_DOMAIN,
  LP_CLIENT_ID,
  LP_ACCOUNT_ID,
  LP_CLIENT_SECRET
} = process.env;

const LP_ACCESS_TOKEN_URI = `https://${
    LP_SENTINEL_DOMAIN}/sentinel/api/account/${LP_ACCOUNT_ID}/token?v=1.0`;

router.get('/token', async (req, res) => {
  const accessToken = req.headers.authorization;

  try {
    // Call LP API with credentials
    const response = await fetch(
        `https://${LP_ACCOUNT_CONFIG_READONLY_DOMAIN}/api/account/${
            LP_ACCOUNT_ID}/configuration/le-agents/status-reasons`,
        {
          headers: [['Authorization', `Bearer ${accessToken}`]],
        });

    const {status} = response;

    if (status === 200) {
      // Generate custom JWT to authenticate client in proxy server.
      const token = generateJwt();

      res.json({token});
      return;
    }

    if (status === 401 || status === 403) {
      res.status(response.status).json({error: 'Could not authenticate user'});
    } else {
      console.log('[DF Proxy Server error] [auth /token] ', response.status);
      res.status(response.status).json({error: 'Server error'});
    }
  } catch (err) {
    console.log('[DF Proxy Server error] [auth /token] ', err);
    res.status(500).json({error: 'Server error'});
  }
});

router.post('/refresh', async (req, res) => {
  const refreshToken = JSON.parse(req.body).refresh_token;

  try {
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
            ]).toString()
    });

    if (response.status === 200) {
      const token = generateJwt();
      res.status(200).json(
          {access_token: token, auth_response: await response.json()});
    } else {
      console.log('[DF Proxy Server error] [auth /refresh] ', response.status);
      res.status(response.status).json({error: 'Could not refresh token'});
    }
  } catch (err) {
    console.log('[DF Proxy Server error] [auth /refresh]', err);
    res.status(500).json({error: 'Could not refresh token'});
  }
});

function generateJwt() {
  return jwt.sign(
      {},
      process.env.JWT_SECRET,
      {expiresIn: '1h'},
  );
}

export {router as authRouter};
