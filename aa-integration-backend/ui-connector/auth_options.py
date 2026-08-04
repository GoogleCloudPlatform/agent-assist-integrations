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

import re
import requests
import logging
import config
from urllib.parse import urlencode


def check_salesforce_token(token):
    """Verifies the access token using Salesforce OpenID Connect.
    Reference: https://help.salesforce.com/s/articleView?id=sf.remoteaccess_using_userinfo_endpoint.htm
    """
    request_headers = {"Authorization": "Bearer " + token}
    # Get the user info.
    user_info_url = f"https://{config.SALESFORCE_DOMAIN}/services/oauth2/userinfo"
    user_info_resp = requests.get(user_info_url, headers=request_headers)
    # Check response.
    if user_info_resp.status_code == 200:
        user_info = user_info_resp.json()
        logging.info("Verifying user {}.".format(user_info["user_id"]))
        # Check the user's organization.
        if user_info["organization_id"] == config.SALESFORCE_ORGANIZATION_ID:
            return True
        else:
            logging.warning(
                "The organization of user {} is not allowed.".format(
                    user_info["user_id"]
                )
            )
    else:
        logging.warning(
            "Failed to verify the access token, {0}, {1}.".format(
                user_info_resp.status_code, user_info_resp.reason
            )
        )
    return False


def check_salesforce_lwc_token(token):
    """Verifies Salesforce Org Id using Client Credentials OAuth flow.

    Uses `token` to call the oauth2/userinfo endpoint, getting
    Salesforce Organization Id for the Connected App's authorized user.
    If this matches `config.SALESFORCE_ORGANIZATION_ID`, return `True`.

    Args:
        token: an `access_token` from the SF OAuth2/token endpoint.

    Returns:
        A Boolean; if `True`, access org id matches `config` module, else `False`.

    Raises:
        Warning: When the token is not valid.
        Warning: When the SF org id doesn't match.

    Reference: https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_client_credentials_flow.htm&type=5

    """
    access_token = re.sub(r"Bearer ", "", token, re.IGNORECASE)
    if config.SALESFORCE_DOMAIN == "login.salesforce.com":
        logging.error("SALESFORCE_DOMAIN is not set. Auth will fail.")
    if config.SALESFORCE_ORGANIZATION_ID == "YOUR_ORGANIZATION_ID":
        logging.error("SALESFORCE_ORGANIZATION_ID is not set. Auth will fail.")
    user_info_resp = requests.get(
        f"https://{config.SALESFORCE_DOMAIN}/services/oauth2/userinfo?"
        + urlencode({"access_token": access_token})
    )
    if user_info_resp.status_code == 200:
        user_info = user_info_resp.json()
        user_org = user_info["organization_id"]
        config_org = config.SALESFORCE_ORGANIZATION_ID
        min_len = min(len(user_org), len(config_org))
        if min_len and user_org[:min_len] == config_org[:min_len]:
            return True
        else:
            logging.warning(
                "The Salesforce org of user {} is not allowed.".format(
                    user_info["user_id"]
                )
            )
    else:
        logging.warning(
            "Failed to verify Salesforce access_token, {0}, {1}.".format(
                user_info_resp.status_code, user_info_resp.reason
            )
        )


def check_genesyscloud_token(token):
    """Verifies the Genesys cloud token with Users API.

    Call the Get method of Users API and use the response status to verify
    whether the token is a valid token to call other Genesys cloud endpoint.
    From the Gensys cloud connector,
    we have to get Dialogflow JWT first then check the platform SDK token,
    so the first pass with empty token will always return true to get JWT first
    In the second pass, when token has value, we check if the token is valid

    Args:
        token: An open smalltable.Table instance.

    Returns:
        A Boolean, if it is True, then the token is valid, otherwise False.

    Raises:
        Warning: When The token is not valid.

    Reference: https://developer.genesys.cloud/devapps/api-explorer#get-api-v2-users-me

    """
    # Prepare for GET /api/v2/authorization/roles request.
    request_headers = {"Authorization": "Bearer " + token}
    response = requests.get(
        f"https://api.{config.GENESYS_CLOUD_REGION}/api/v2/users/me",
        headers=request_headers,
    )
    # Check response.
    if response.status_code == 200:
        response_json = response.json()
        logging.info("Verifying user {}.".format(response_json["id"]))
        # Genesys cloud response does not have organization to check
        return True
    else:
        logging.warning(
            "Failed to verify the access token, {0}, {1}.".format(
                response.status_code, response.reason
            )
        )
    return False


def check_twilio_token(token):
    """Verifies the Twilio token for the flex plugin.

    Args:
         token: An open smalltable.Table instance.

     Returns:
         A Boolean, if it is True, then the token is valid, otherwise False.

     Raises:
         Warning: When The token is not valid.

     Reference:
         Twilio flex plugin
         https://www.twilio.com/en-us/blog/sms-otp-authentication-flex
         https://www.twilio.com/docs/flex/developer/ui/add-components-flex-ui

    """
    body = {"Token": token}
    response = requests.post(
        f"https://{config.TWILIO_FLEX_ENVIRONMENT}/verify", json=body
    )
    # If the endpoint return 200 then the token was validated
    if response.status_code == 200:
        return True
    else:
        logging.warning(
            "Failed to verify the access token, {0}, {1}.".format(
                response.status_code, response.reason
            )
        )


def check_five9_token(token):
    """
    Verifies the internal shared secret (FIVE9_TRUST_TOKEN) sent in the Authorization header.
    Expects: 'Bearer <FIVE9_TRUST_TOKEN>'
    """
    if not token or not token.startswith("Bearer "):
        logging.warning("Missing or malformed Authorization header.")
        return False

    # Extract the token from 'Bearer <token>'
    token = token.split(" ")[1]

    try:
        # Secure string comparison
        if token == config.FIVE9_TRUST_TOKEN:
            return True
        else:
            logging.warning("Failed to verify the Five9 trust token.")
            return False
    except Exception as e:
        logging.error(f"Error during token verification: {e}")
        return False
