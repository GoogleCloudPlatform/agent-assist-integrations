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

import {createCipheriv, createDecipheriv, createHash} from 'crypto';

const algorithm = 'aes-256-ecb';
const secret = process.env.SECRET_PHRASE;
const key = Buffer.from(
    createHash('sha256').update(String(secret)).digest('base64'), 'base64');

/** Encrypts a given string using the user-provided secret key. */
export function encrypt(text: string) {
  const cipher = createCipheriv(algorithm, key, null);
  const encrypted = Buffer.concat([cipher.update(text), cipher.final()]);

  return encrypted.toString('hex');
}

/** Decrypts an encrypted message using the user-provided secret key. */
export function decrypt(encryptedData: string) {
  const decipher = createDecipheriv(algorithm, key, null);
  const decrypted =
      Buffer.concat([decipher.update(encryptedData, 'hex'), decipher.final()]);

  return decrypted.toString('utf-8');
}
