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
