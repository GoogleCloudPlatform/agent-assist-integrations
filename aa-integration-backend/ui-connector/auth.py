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
"""Authentication helper functions and middleware for UI connector."""

from datetime import datetime, timezone, timedelta
from functools import wraps
import os

from flask import jsonify, request
import jwt
import requests

import auth_options
import config

jwt_secret_key = ''  # To be loaded from config.JWT_SECRET_KEY_PATH


def load_jwt_secret_key():
    """Loads and returns JWT secret key from configured file path or env."""
    global jwt_secret_key
    if jwt_secret_key:
        return jwt_secret_key

    if os.path.exists(config.JWT_SECRET_KEY_PATH):
        with open(config.JWT_SECRET_KEY_PATH, 'r',
                  encoding='utf-8') as key_file:
            content = key_file.read().strip()
            if content:
                jwt_secret_key = content
    if not jwt_secret_key:
        jwt_secret_key = os.environ.get('JWT_SECRET_KEY')
    if not jwt_secret_key:
        raise ValueError('Server JWT secret key is not configured.')
    return jwt_secret_key


def check_auth(token):
    """Checks authentication token based on configured auth option."""
    if config.AUTH_OPTION == 'SalesforceLWC':
        return auth_options.check_salesforce_lwc_token(token)
    elif config.AUTH_OPTION == 'Salesforce':
        return auth_options.check_salesforce_token(token)
    elif config.AUTH_OPTION == 'GenesysCloud':
        return auth_options.check_genesyscloud_token(token)
    elif config.AUTH_OPTION == 'Twilio':
        return auth_options.check_twilio_token(token)
    elif config.AUTH_OPTION == 'Five9':
        return auth_options.check_five9_token(token)
    elif config.AUTH_OPTION == 'Skip':
        return True
    # Customize your authentication method here.
    # elif config.AUTH_OPTION == 'Your Auth Option':
    #     return auth_options.check_my_token(token)
    return False


def check_jwt(token):
    """Validates and decodes a JWT token."""
    if not isinstance(token, str) or not token:
        return False, 'Failed to parse your token.'
    try:
        load_jwt_secret_key()
        if token.startswith('Bearer '):
            token = token[7:].strip()
        # Decode the payload to fetch the stored details.
        data = jwt.decode(token, jwt_secret_key, algorithms=['HS256'])
        if 'gcp_agent_assist_project' not in data:
            return False, 'The target project in your token is missing.'
        if data['gcp_agent_assist_project'] != config.GCP_PROJECT_ID:
            return False, 'The target project in your token is invalid.'
        if 'exp' not in data:
            return False, 'The expiration time in your token is missing.'
        if data['exp'] < datetime.now().timestamp():
            return False, 'Your token has expired.'
        return True, 'Your token is valid.'
    except ValueError as e:
        return False, str(e)
    except (jwt.PyJWTError, KeyError, IndexError, TypeError):
        return False, 'Failed to parse your token.'


def generate_jwt(user_info=None):
    """Generates a signed JWT token for the authenticated user."""
    load_jwt_secret_key()
    gcp_agent_assist_user = ''
    if user_info:
        gcp_agent_assist_user = user_info.get('gcp_agent_assist_user')
    return jwt.encode(
        {
            'exp':
                datetime.now(timezone.utc) +
                timedelta(minutes=config.JWT_TOKEN_LIFETIME),
            'gcp_agent_assist_project':
                config.GCP_PROJECT_ID,
            'gcp_agent_assist_user':
                gcp_agent_assist_user
        }, jwt_secret_key, 'HS256')


def check_app_auth(auth):
    """Validates application-level authentication (e.g. Twilio)."""
    if not isinstance(auth, dict):
        return False
    if config.APP_AUTH_OPTION == 'Twilio':
        response = requests.get(config.TWILIO_ACCOUNTS_API_URL,
                                auth=(auth.get('accountSid'),
                                      auth.get('authToken')),
                                timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('sid') == config.TWILIO_ACCOUNT_SID:
                return True
    return False


def token_required(f):
    """Verifies JWT as a function decorator."""

    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing.'}), 401
        result, message = check_jwt(token)
        if result:
            return f(*args, **kwargs)
        else:
            return jsonify({'message': message}), 401

    return decorator
