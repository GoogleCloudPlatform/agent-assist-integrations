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

"""Module used for managing all environmental variables
"""
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# # Comment out for local dev
# from dotenv import load_dotenv
# load_dotenv()  # Load environment variables from .env file

# Queue / DNIS to Business Unit (LOB) & ConversationProfile Mapping.
# Set the QUEUE_CONFIG_JSON environment variable to map queueIds, LOB keys, or
# trailing 8-digit DNIS suffixes to {"lob": "...", "conversation_profile": "..."}.
DEFAULT_QUEUE_CONFIG = {
    "default": {
        "lob": os.environ.get("DEFAULT_LOB", "default"),
        "conversation_profile": os.environ.get("CONVERSATION_PROFILE_NAME"),
    },
}


def parse_queue_config() -> Dict[str, Any]:
    """Parses QUEUE_CONFIG_JSON from environment or returns DEFAULT_QUEUE_CONFIG.
    If QUEUE_CONFIG_JSON does not define a "default" entry, the "default" entry
    from DEFAULT_QUEUE_CONFIG (DEFAULT_LOB / CONVERSATION_PROFILE_NAME) is added.
    """
    raw_json = os.environ.get("QUEUE_CONFIG_JSON")
    if raw_json:
        try:
            parsed = json.loads(raw_json)
            if not isinstance(parsed, dict):
                raise ValueError("QUEUE_CONFIG_JSON must be a JSON object")
            parsed = {str(k).strip(): v for k, v in parsed.items()}
            parsed.setdefault("default", DEFAULT_QUEUE_CONFIG["default"])
            logger.info("Loaded QUEUE_CONFIG_JSON keys: %s", list(parsed.keys()))
            return parsed
        except Exception as e:
            logger.error(
                "Failed to parse QUEUE_CONFIG_JSON, falling back to defaults: %s", e
            )
    return DEFAULT_QUEUE_CONFIG


@dataclass
class AudiohookConfig:
    """Loading the environmental variables
    """
    conversation_profile_name: str
    project_id: str
    ui_connector_endpoint: str
    redis_host: str
    redis_port: Optional[int]
    datastore_id: Optional[str] = field(default=None)
    datastore_location: Optional[str] = field(default=None)
    language_code: str = field(default="ja")
    api_key: Optional[str] = field(default=None)
    client_secret: Optional[str] = field(default=None)
    log_level: str = field(default='INFO')
    timeout: int = field(default=2)
    rate: int = field(default=8000)
    chunk_size: int = field(default=1600)
    max_lookback: int = field(default=3)
    queue_config: Dict[str, Any] = field(default_factory=parse_queue_config)

    def __post_init__(self):
        """The os.environ can possibly return NONE value, need a post process to handle missing values"""
        if self.conversation_profile_name is None:
            raise ValueError(
                "Environment Variable CONVERSATION_PROFILE_NAME for Audiohook monitor is missing")
        if self.project_id is None:
            raise ValueError(
                "Environment Variable GCP_PROJECT_ID for Audiohook monitor is missing")
        if self.ui_connector_endpoint is None:
            raise ValueError(
                "Environment Variable UI_CONNECTOR for Audiohook monitor is missing")
        if self.redis_host is None:
            raise ValueError(
                "Environment Variable REDISHOST for Audiohook monitor is missing")
        if self.redis_port is None:
            raise ValueError(
                "Environment Variable REDISPORT for Audiohook monitor is missing")

        if not self.api_key and not self.client_secret:
            logger.warning(
                "Neither API_KEY nor CLIENT_SECRET is set. AudioHook WebSocket endpoint will run in unauthenticated mode."
            )
        elif self.api_key and not self.client_secret:
            logger.info(
                "API_KEY is configured for header validation. CLIENT_SECRET is unconfigured (RFC 9421 HMAC signatures will not be verified)."
            )
        elif self.client_secret:
            logger.info(
                "CLIENT_SECRET is configured. AudioHook will enforce RFC 9421 HMAC-SHA256 signature verification on incoming handshakes."
            )


redis_port_env = os.environ.get('REDISPORT')
config = AudiohookConfig(
    api_key=os.environ.get("API_KEY") or os.environ.get("AUDIOHOOK_API_KEY"),
    client_secret=os.environ.get("CLIENT_SECRET") or os.environ.get("AUDIOHOOK_CLIENT_SECRET"),
    conversation_profile_name=os.environ.get("CONVERSATION_PROFILE_NAME"),
    project_id=os.environ.get("GCP_PROJECT_ID"),
    ui_connector_endpoint=os.environ.get("UI_CONNECTOR"),
    redis_host=os.environ.get('REDISHOST'),
    redis_port=int(redis_port_env) if redis_port_env is not None else None,
    log_level=os.environ.get('LOG_LEVEL', 'INFO'),
    datastore_id=os.environ.get("DATASTORE_ID"),
    datastore_location=os.environ.get("DATASTORE_LOCATION"),
    language_code=os.environ.get("LANGUAGE_CODE", "ja"),
)
