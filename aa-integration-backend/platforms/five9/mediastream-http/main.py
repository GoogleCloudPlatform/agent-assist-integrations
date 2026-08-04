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

"""HTTP Server entry point for Five9 MediaStream."""

import hashlib
import hmac
import logging
import os
import requests

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

logging.basicConfig(level=logging.INFO)
load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Retrieve Five9 API Key and Trust Token from environment
FIVE9_TRUST_TOKEN = os.getenv("FIVE9_TRUST_TOKEN")
if not FIVE9_TRUST_TOKEN:
    raise ValueError("FIVE9_TRUST_TOKEN is not set in environment variables")
FIVE9_API_KEY = os.getenv("FIVE9_API_KEY")
if not FIVE9_API_KEY:
    raise ValueError("FIVE9_API_KEY is not set in environment variables")


@app.route("/", methods=["GET"])
def root():
    """Health check endpoint."""
    return "Five9 MediaStream HTTP Service Available", 200


@app.route("/agent-assist-ui-modules/", methods=["GET"])
def agent_assist_ui_modules():
    """Agent Assist UI Modules page."""
    conversation_profile = os.getenv("CONVERSATION_PROFILE_NAME", "")
    features = os.getenv("FEATURES", "")
    ui_connector_url = os.getenv("UI_CONNECTOR_URL", "")
    token = ""

    try:
        url = f"{ui_connector_url}/register"
        headers = {
            "Authorization": f"Bearer {FIVE9_TRUST_TOKEN}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            url, headers=headers, timeout=10
        )

        if not response.ok:
            logging.error(f"Error Body: {response.text}")

        response.raise_for_status()
        data = response.json()
        token = data.get("token")

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logging.error(f"An unexpected error occurred: {type(err).__name__} - {err}")

    return render_template(
        "agent-assist-ui-modules.html",
        conversation_profile=conversation_profile,
        features=features,
        ui_connector_url=ui_connector_url,
        auth_token=token,
    )


@app.route("/cti-call-event-destination/", methods=["GET", "POST"])
def cti_event_destination():
    """CTI event validation and event reception endpoint."""

    provided_key = request.headers.get("x-api-key")
    if provided_key and not hmac.compare_digest(provided_key, FIVE9_API_KEY):
        logging.warning("Unauthorized request: Invalid or missing API Key")
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "GET":
        # Validation Request
        if not FIVE9_TRUST_TOKEN:
            logging.error(
                "TRUST_TOKEN not set in environment. Cannot validate subscription."
            )
            return "Server Configuration Error: TRUST_TOKEN not set", 500

        # Calculate SHA256 hash of the trust token
        # Five9 requires the response to be a JSON string of the hash
        sha_token = hashlib.sha256(FIVE9_TRUST_TOKEN.encode("utf-8")).hexdigest()
        logging.info("Validating subscription with token hash: %s", sha_token)
        return jsonify(sha_token)

    if request.method == "POST":
        # CTI Event
        payload = request.get_json(silent=True)
        logging.info("Received CTI Event: %s", payload)
        
        if payload and "payload" in payload:
            attached_vars = payload["payload"].get("attached_variables", {})
            session_id = attached_vars.get("Call.session_id")
            call_id = attached_vars.get("Call.call_id")
            
            if session_id and call_id:
                ui_connector_url = os.getenv("UI_CONNECTOR_URL", "")
                if ui_connector_url:
                    try:
                        # Get JWT token
                        register_url = f"{ui_connector_url}/register"
                        reg_headers = {
                            "Authorization": f"Bearer {FIVE9_TRUST_TOKEN}",
                            "Content-Type": "application/json",
                        }
                        reg_resp = requests.post(register_url, headers=reg_headers, timeout=5)
                        reg_resp.raise_for_status()
                        token = reg_resp.json().get("token")
                        
                        # Store mapping
                        mapping_url = f"{ui_connector_url}/conversation-name"
                        map_headers = {
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        }
                        
                        project = os.getenv("PROJECT_ID")
                        location = os.getenv("REGION")
                        
                        if not project or not location:
                            cp = os.getenv("CONVERSATION_PROFILE_NAME", "")
                            parts = cp.split('/')
                            if len(parts) >= 4 and parts[0] == 'projects' and parts[2] == 'locations':
                                project = parts[1]
                                location = parts[3]
                                
                        if project and location:
                            conversation_name = f"projects/{project}/locations/{location}/conversations/five9-{call_id.zfill(10)}"
                            mapping_body = {
                                "conversationIntegrationKey": session_id,
                                "conversationName": conversation_name
                            }
                            map_resp = requests.post(mapping_url, headers=map_headers, json=mapping_body, timeout=5)
                            map_resp.raise_for_status()
                            logging.info("Successfully stored mapping: %s -> %s", session_id, conversation_name)
                        else:
                            logging.error("Could not determine project or location for mapping.")
                    except Exception as e:
                        logging.error("Failed to store mapping in UI Connector: %s", e)
                else:
                    logging.error("UI_CONNECTOR_URL not set. Cannot store mapping.")
            else:
                logging.warning("Missing Call.session_id or Call.call_id in attached_variables.")
        else:
            logging.warning("Payload missing 'payload' object.")
            
        return "", 200
    return "Method Not Allowed", 405


@app.route(
    "/mediastream-event-destination/subscriptions/<string:subscription_id>",
    methods=["POST"],
)
def mediastream_event_destination(subscription_id):
    logging.info(
        "Received Stream Event for subscription %s: %s",
        subscription_id,
        request.get_json(silent=True),
    )
    return "", 200


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080
    app.run(host="0.0.0.0", port=PORT, debug=False)
