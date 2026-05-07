/**
 * Copyright 2026 Google LLC
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

// Dialogflow API Configuration
export const DIALOGFLOW_API_VERSION = "v2beta1";

// Token Refresh & Auth Configuration
export const TOKEN_REFRESH_CHECK_INTERVAL_MS = 60000;
export const TOKEN_EXPIRATION_THRESHOLD_SEC = 60;
export const TOKEN_WAIT_INTERVAL_MS = 100;
export const TOKEN_HEALTHY_LOG_INTERVAL_MS = 300000;

// Conversation Polling Configuration
export const POLL_MAX_RETRIES = 15;
export const POLL_INITIAL_DELAY_MS = 100;
export const POLL_DELAY_INCREMENT_MS = 100;

// Demo & Testing Configuration
export const CONTEXT_INJECTION_DELAY_MS = 1000;
