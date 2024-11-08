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

import { sign, SignOptions } from 'jsonwebtoken';

import { encrypt } from './crypto_helpers';

/** Generates a one-hour access token for the proxy server. */
export function generateProxyAccessToken() {
  return generateJwt({ expiresIn: '1h' }, { type: 'access' });
}

/**
 * Generates a one-hour refresh token for the proxy server.
 *
 * Stores the encrypted OAuth refresh token in it's payload, which the proxy
 * server uses to authenticate the user and generate additional access tokens.
 **/
export function generateProxyRefreshToken(refreshToken: string) {
  return generateJwt(
    { expiresIn: '1h' },
    {
      type: 'refresh',
      token: encrypt(refreshToken),
    }
  );
}

/** Generates a JWT using the given options and payload data. */
function generateJwt<T extends object>(
  options: SignOptions,
  data: Partial<T> | undefined = {}
) {
  return sign(data, process.env.JWT_SECRET, options);
}
