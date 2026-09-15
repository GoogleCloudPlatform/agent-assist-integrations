# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for RFC 9421 HMAC signature verification and authentication in auth.py.
"""

import base64
import hashlib
import hmac
import unittest

from auth import (build_signature_base, decode_secret, parse_signature,
                  parse_signature_input, verify_signature)


class TestAuth(unittest.TestCase):
    """Test suite for AudioHook authentication and signature verification."""

    def setUp(self):
        self.raw_secret = b'super-secret-key-32-bytes-length!'
        self.b64_secret = base64.b64encode(self.raw_secret).decode('utf-8')
        self.api_key = 'test-genesys-api-key-12345'
        self.fixed_time = 1700000000.0

    def _generate_valid_signature_headers(
        self,
        method: str = 'GET',
        path: str = '/connect',
        api_key: str = 'test-genesys-api-key-12345',
        secret_bytes: bytes = None,
        created_time: int = 1700000000,
        include_extra_headers: bool = True
    ):
        if secret_bytes is None:
            secret_bytes = self.raw_secret

        headers = {
            'Host': 'audiohook.example.com',
            'X-API-KEY': api_key,
        }
        if include_extra_headers:
            headers['audiohook-organization-id'] = 'org-uuid-111'
            headers['audiohook-session-id'] = 'session-uuid-222'
            headers['audiohook-correlation-id'] = 'correlation-uuid-333'

        components = ['"@request-target"', '"x-api-key"']
        if include_extra_headers:
            components.extend([
                '"audiohook-organization-id"',
                '"audiohook-session-id"',
                '"audiohook-correlation-id"'
            ])

        components_joined = ' '.join(components)
        params_string = f'({components_joined});created={created_time};keyid="my-key-id"'
        sig_input_header = f'sig1={params_string}'

        clean_components = [c.replace('"', '') for c in components]
        sig_base, err = build_signature_base(
            components=clean_components,
            params_string=params_string,
            headers=headers,
            method=method,
            path=path,
            authority='audiohook.example.com'
        )
        self.assertIsNone(err)

        digest = hmac.new(secret_bytes, sig_base.encode('utf-8'), hashlib.sha256).digest()
        sig_b64 = base64.b64encode(digest).decode('utf-8')
        sig_header = f'sig1=:{sig_b64}:'

        headers['Signature-Input'] = sig_input_header
        headers['Signature'] = sig_header
        return headers

    def test_progressive_enhancement_unauthenticated_mode(self):
        """Tests that when neither API_KEY nor CLIENT_SECRET is set, auth succeeds without headers."""
        is_valid, err = verify_signature(
            headers={},
            method='GET',
            path='/connect',
            client_secret=None,
            expected_api_key=None
        )
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_decode_secret_base64_and_raw(self):
        """Tests decoding Base64 encoded and raw string secrets."""
        decoded = decode_secret(self.b64_secret)
        self.assertEqual(decoded, self.raw_secret)

        raw_str = "simple_raw_secret_not_base64"
        decoded_raw = decode_secret(raw_str)
        self.assertEqual(decoded_raw, raw_str.encode('utf-8'))

        self.assertEqual(decode_secret(''), b'')

    def test_parse_signature_input(self):
        """Tests parsing RFC 9421 Signature-Input header."""
        header_val = 'sig1=("@request-target" "x-api-key" "audiohook-session-id");created=1700000000;keyid="cred-1"'
        label, components, params_str, created = parse_signature_input(header_val)

        self.assertEqual(label, 'sig1')
        self.assertEqual(components, ['@request-target', 'x-api-key', 'audiohook-session-id'])
        self.assertEqual(created, 1700000000)
        self.assertIn('created=1700000000', params_str)

    def test_parse_signature(self):
        """Tests extracting Base64 signature from various Signature header styles."""
        self.assertEqual(parse_signature('sig1=:YWJjZGVmZ2hpams=:'), 'YWJjZGVmZ2hpams=')
        self.assertEqual(parse_signature(':YWJjZGVmZ2hpams=:'), 'YWJjZGVmZ2hpams=')
        self.assertEqual(parse_signature('YWJjZGVmZ2hpams='), 'YWJjZGVmZ2hpams=')
        self.assertIsNone(parse_signature(''))

    def test_build_signature_base(self):
        """Tests canonical signature base string reconstruction."""
        headers = {
            'host': 'example.com',
            'x-api-key': 'secret-api-key',
            'audiohook-session-id': 'session-123'
        }
        components = ['@request-target', 'x-api-key', 'audiohook-session-id', '@authority']
        params_str = '("@request-target" "x-api-key" "audiohook-session-id" "@authority");created=1700000000'

        base, err = build_signature_base(
            components=components,
            params_string=params_str,
            headers=headers,
            method='GET',
            path='/connect',
            authority='example.com'
        )
        expected_lines = [
            '"@request-target": /connect',
            '"x-api-key": secret-api-key',
            '"audiohook-session-id": session-123',
            '"@authority": example.com',
            f'"@signature-params": {params_str}'
        ]
        self.assertEqual(base, '\n'.join(expected_lines))

        # Also verify legacy draft-cavage method prefix when explicitly requested
        base_with_method, _ = build_signature_base(
            components=components,
            params_string=params_str,
            headers=headers,
            method='GET',
            path='/connect',
            authority='example.com',
            include_method_in_request_target=True
        )
        self.assertIn('"@request-target": get /connect', base_with_method)

    def test_verify_signature_success(self):
        """Tests successful signature verification with valid credentials and headers."""
        headers = self._generate_valid_signature_headers(
            method='GET', path='/connect', api_key=self.api_key, secret_bytes=self.raw_secret
        )
        is_valid, err = verify_signature(
            headers=headers,
            method='GET',
            path='/connect',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_verify_signature_missing_or_invalid_api_key(self):
        """Tests rejection when API key is missing or wrong."""
        headers = self._generate_valid_signature_headers(
            method='GET', path='/connect', api_key=self.api_key, secret_bytes=self.raw_secret
        )

        headers_missing_key = dict(headers)
        del headers_missing_key['X-API-KEY']
        is_valid, err = verify_signature(
            headers=headers_missing_key,
            method='GET',
            path='/connect',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertFalse(is_valid)
        self.assertIn('Missing X-API-KEY', err)

        headers_wrong_key = dict(headers)
        headers_wrong_key['X-API-KEY'] = 'wrong-key'
        is_valid, err = verify_signature(
            headers=headers_wrong_key,
            method='GET',
            path='/connect',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertFalse(is_valid)
        self.assertIn('Invalid X-API-KEY', err)

    def test_verify_signature_invalid_secret_or_tampered_header(self):
        """Tests rejection when client secret is wrong or signed headers were tampered with."""
        headers = self._generate_valid_signature_headers(
            method='GET', path='/connect', api_key=self.api_key, secret_bytes=self.raw_secret
        )

        wrong_secret = base64.b64encode(b'wrong-secret-key-32-bytes-length!').decode('utf-8')
        is_valid, err = verify_signature(
            headers=headers,
            method='GET',
            path='/connect',
            client_secret=wrong_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertFalse(is_valid)
        self.assertIn('HMAC signature verification failed', err)

        tampered_headers = dict(headers)
        tampered_headers['audiohook-session-id'] = 'tampered-session-id'
        is_valid, err = verify_signature(
            headers=tampered_headers,
            method='GET',
            path='/connect',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertFalse(is_valid)
        self.assertIn('HMAC signature verification failed', err)

    def test_verify_signature_timestamp_expiration(self):
        """Tests rejection when signature timestamp exceeds maximum clock skew."""
        old_time = int(self.fixed_time - 600)
        headers = self._generate_valid_signature_headers(
            method='GET',
            path='/connect',
            api_key=self.api_key,
            secret_bytes=self.raw_secret,
            created_time=old_time
        )

        is_valid, err = verify_signature(
            headers=headers,
            method='GET',
            path='/connect',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            max_clock_skew_seconds=300,
            current_time=self.fixed_time
        )
        self.assertFalse(is_valid)
        self.assertIn('Signature timestamp expired', err)

    def test_reverse_proxy_x_forwarded_host(self):
        """Tests that @authority is correctly resolved from X-Forwarded-Host when Host is rewritten by Cloud Run / ALB."""
        # Genesys dials audiohook.customer.com and signs @authority: audiohook.customer.com
        signed_headers = self._generate_valid_signature_headers(
            method='GET',
            path='/connect',
            api_key=self.api_key,
            secret_bytes=self.raw_secret,
        )
        # Add @authority into signature components
        components = ['"@request-target"', '"@authority"', '"x-api-key"']
        params_string = f'({" ".join(components)});created=1700000000;keyid="my-key-id"'
        signed_headers['Signature-Input'] = f'sig1={params_string}'

        # Reverse proxy rewrites Host header to internal Cloud Run URL, but forwards original in X-Forwarded-Host
        signed_headers['Host'] = 'audiohook-service-xyz-uc.a.run.app'
        signed_headers['X-Forwarded-Host'] = 'audiohook.customer.com'

        clean_components = [c.replace('"', '') for c in components]
        sig_base, err = build_signature_base(
            components=clean_components,
            params_string=params_string,
            headers=signed_headers,
            method='GET',
            path='/connect',
            authority='audiohook.customer.com'
        )
        self.assertIsNone(err)
        digest = hmac.new(self.raw_secret, sig_base.encode('utf-8'), hashlib.sha256).digest()
        signed_headers['Signature'] = f'sig1=:{base64.b64encode(digest).decode("utf-8")}:'

        is_valid, err = verify_signature(
            headers=signed_headers,
            method='GET',
            path='/connect',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertTrue(is_valid, f'Expected signature verification to succeed with X-Forwarded-Host, got error: {err}')

    def test_reverse_proxy_multi_hop_and_non_default_port(self):
        """Tests multi-hop X-Forwarded-Host (comma-separated) and X-Forwarded-Port handling."""
        signed_headers = {
            'Host': 'internal.cluster.local',
            'X-Forwarded-Host': 'external.example.com, proxy1.internal',
            'X-Forwarded-Port': '8443',
            'X-API-KEY': self.api_key
        }
        components = ['"@authority"', '"x-api-key"']
        params_string = f'({" ".join(components)});created=1700000000'
        signed_headers['Signature-Input'] = f'sig1={params_string}'

        clean_components = [c.replace('"', '') for c in components]
        sig_base, err = build_signature_base(
            components=clean_components,
            params_string=params_string,
            headers=signed_headers,
            method='GET',
            path='/connect'
        )
        self.assertIsNone(err)
        self.assertIn('"@authority": external.example.com:8443', sig_base)

    def test_path_normalization_and_query_string(self):
        """Tests @request-target with raw query parameters and @path stripping query parameters."""
        headers = {
            'Host': 'audiohook.example.com',
            'X-API-KEY': self.api_key,
        }
        components = ['"@request-target"', '"@path"', '"x-api-key"']
        params_string = f'({" ".join(components)});created=1700000000'
        headers['Signature-Input'] = f'sig1={params_string}'

        clean_components = [c.replace('"', '') for c in components]
        sig_base, err = build_signature_base(
            components=clean_components,
            params_string=params_string,
            headers=headers,
            method='GET',
            path='/connect',
            request_target='/connect?org=123&env=prod'
        )
        self.assertIsNone(err)
        self.assertIn('"@request-target": /connect?org=123&env=prod', sig_base)
        self.assertIn('"@path": /connect', sig_base)

        digest = hmac.new(self.raw_secret, sig_base.encode('utf-8'), hashlib.sha256).digest()
        headers['Signature'] = f'sig1=:{base64.b64encode(digest).decode("utf-8")}:'

        is_valid, err = verify_signature(
            headers=headers,
            method='GET',
            path='/connect',
            request_target='/connect?org=123&env=prod',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertTrue(is_valid, f'Verification failed: {err}')

    def test_rfc9421_header_whitespace_normalization(self):
        """Tests RFC 9421 Section 2.1 canonical whitespace normalization (stripping and collapsing spaces/tabs)."""
        headers = {
            'Host': 'audiohook.example.com',
            'X-API-KEY': self.api_key,
            'audiohook-session-id': '   session-uuid-123   \t   extra   '
        }
        components = ['"@request-target"', '"audiohook-session-id"']
        params_string = f'({" ".join(components)});created=1700000000'
        headers['Signature-Input'] = f'sig1={params_string}'

        clean_components = [c.replace('"', '') for c in components]
        sig_base, err = build_signature_base(
            components=clean_components,
            params_string=params_string,
            headers=headers,
            method='GET',
            path='/connect'
        )
        self.assertIsNone(err)
        # Leading/trailing whitespace stripped, internal linear whitespace collapsed to single space
        self.assertIn('"audiohook-session-id": session-uuid-123 extra', sig_base)

    def test_genesys_rfc9421_official_test_vector(self):
        """Tests official Genesys Cloud RFC 9421 test vector from PureCloudLabs reference implementation."""
        # Test vector from PureCloudLabs/audiohook-reference-implementation
        path = '/api/v1/voicebiometrics/ws'
        api_key = 'SGVsbG8sIEkgYW0gdGhlIEFQSSBrZXkh'
        client_secret_b64 = 'TXlTdXBlclNlY3JldEtleVRlbGxOby0xITJAMyM0JDU='
        sig_input_header = (
            'sig1=("@request-target" "@authority" "audiohook-organization-id" '
            '"audiohook-session-id" "audiohook-correlation-id" "x-api-key");'
            'keyid="SGVsbG8sIEkgYW0gdGhlIEFQSSBrZXkh";'
            'nonce="VGhpc0lzQVRlc3ROb25jZQ==";'
            'alg="hmac-sha256";created=1641038400;expires=1641038430'
        )
        headers = {
            'Host': 'localhost:8080',
            'X-API-KEY': api_key,
            'audiohook-organization-id': '00000000-0000-0000-0000-000000000000',
            'audiohook-session-id': '11111111-1111-1111-1111-111111111111',
            'audiohook-correlation-id': '22222222-2222-2222-2222-222222222222',
            'Signature-Input': sig_input_header,
        }

        # Build signature base using RFC 9421 (@request-target: /path without method)
        _, components, params_string, _ = parse_signature_input(sig_input_header)
        sig_base, err = build_signature_base(
            components=components,
            params_string=params_string,
            headers=headers,
            method='GET',
            path=path,
            authority='localhost:8080'
        )
        self.assertIsNone(err)
        self.assertIn(f'"@request-target": {path}', sig_base)
        self.assertNotIn(f'"@request-target": get {path}', sig_base)

        secret_bytes = decode_secret(client_secret_b64)
        computed_digest = hmac.new(secret_bytes, sig_base.encode('utf-8'), hashlib.sha256).digest()
        computed_sig_b64 = base64.b64encode(computed_digest).decode('utf-8')
        headers['Signature'] = f'sig1=:{computed_sig_b64}:'

        is_valid, err = verify_signature(
            headers=headers,
            method='GET',
            path=path,
            client_secret=client_secret_b64,
            expected_api_key=api_key,
            current_time=1641038400.0,
            authority='localhost:8080'
        )
        self.assertTrue(is_valid, f'Official RFC 9421 test vector verification failed: {err}')

    def test_genesys_legacy_method_prefixed_fallback(self):
        """Tests that verify_signature gracefully falls back and accepts legacy draft-cavage method-prefixed request-target."""
        headers = self._generate_valid_signature_headers(
            method='GET',
            path='/connect',
            api_key=self.api_key,
            secret_bytes=self.raw_secret
        )
        # Force the signature to be computed with include_method_in_request_target=True
        label, components, params_string, _ = parse_signature_input(headers['Signature-Input'])
        legacy_base, err = build_signature_base(
            components=components,
            params_string=params_string,
            headers=headers,
            method='GET',
            path='/connect',
            authority='audiohook.example.com',
            include_method_in_request_target=True
        )
        self.assertIsNone(err)
        self.assertIn('"@request-target": get /connect', legacy_base)

        legacy_digest = hmac.new(self.raw_secret, legacy_base.encode('utf-8'), hashlib.sha256).digest()
        headers['Signature'] = f'sig1=:{base64.b64encode(legacy_digest).decode("utf-8")}:'

        is_valid, err = verify_signature(
            headers=headers,
            method='GET',
            path='/connect',
            client_secret=self.b64_secret,
            expected_api_key=self.api_key,
            current_time=self.fixed_time
        )
        self.assertTrue(is_valid, f'Fallback verification failed: {err}')


if __name__ == '__main__':
    unittest.main()
