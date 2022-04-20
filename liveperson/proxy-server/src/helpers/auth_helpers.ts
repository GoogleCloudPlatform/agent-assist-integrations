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
