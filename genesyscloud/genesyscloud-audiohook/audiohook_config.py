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

"""Module used for managing all environmental variables
"""
import os
from dataclasses import dataclass, field

# # Comment out for local dev
# from dotenv import load_dotenv
# load_dotenv()  # Load environment variables from .env file


@dataclass
class AudiohookConfig:
    """Loading the environmental variables
    """
    api_key: str
    conversation_profile_name: str
    project_id: str
    ui_connector_endpoint: str
    redis_host: str
    redis_port: int
    log_level: str = field(default='INFO')
    timeout: int = field(default=2)
    rate: int = field(default=8000)
    chunk_size: int = field(default=1600)
    max_lookback: int = field(default=3)

    def __post_init__(self):
        """The os.environ can possible return NONE value, need a post process to handel missing values"""
        if self.api_key is None:
            raise ValueError(
                "Environment Variable API_KEY for Audiohook monitor is missing")
        if self.conversation_profile_name is None:
            raise ValueError(
                "Environment Variable CONVERSATION_PROFILE_NAME for Audiohook monitor is missing")
        if self.project_id is None:
            raise ValueError(
                "Environment Variable GCP_PROJECT_ID for Audiohook monitor is missing")
        if self.ui_connector_endpoint is None:
            raise ValueError(
                "Environment Variable UI_CONNECTOR for Audiohook monitor is missing")
        if self.ui_connector_endpoint is None:
            raise ValueError(
                "Environment Variable UI_CONNECTOR for Audiohook monitor is missing")
        if self.redis_host is None:
            raise ValueError(
                "Environment Variable REDISHOST for Audiohook monitor is missing")
        if self.redis_host is None:
            raise ValueError(
                "Environment Variable REDISPORT for Audiohook monitor is missing")


config = AudiohookConfig(
    api_key=os.environ.get("API_KEY"),
    conversation_profile_name=os.environ.get(
        "CONVERSATION_PROFILE_NAME"),
    project_id=os.environ.get("GCP_PROJECT_ID"),
    ui_connector_endpoint=os.environ.get(
        "UI_CONNECTOR"),
    redis_host=os.environ.get('REDISHOST'),
    redis_port=int(os.environ.get('REDISPORT'))
)
