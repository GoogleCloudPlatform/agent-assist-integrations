# Copyright 2024 Google LLC
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

import os
import requests
import logging

def check_salesforce_token(token):
    """Verifies the access token using Salesforce OpenID Connect.
    Reference: https://help.salesforce.com/s/articleView?id=sf.remoteaccess_using_userinfo_endpoint.htm
    """
    request_headers = {
        'Authorization': 'Bearer ' + token
    }
    # Get the user info.
    # For sandbox environment, please replace login.salesforce.com with test.salesforce.com.
    user_info_url = 'https://login.salesforce.com/services/oauth2/userinfo'
    user_info_resp = requests.get(user_info_url, headers=request_headers)
    # Check response.
    if user_info_resp.status_code == 200:
        user_info = user_info_resp.json()
        logging.info('Verifying user {}.'.format(user_info['user_id']))
        # Check the user's organization.
        if user_info['organization_id'] == os.environ.get('SALESFORCE_ORGANIZATION_ID', ''):
            return True
        else:
            logging.warning('The organization of user {} is not allowed.'.format(user_info['user_id']))
    else:
        logging.warning('Failed to verify the access token, {0}, {1}.'.format(user_info_resp.status_code, user_info_resp.reason))
    
    return False