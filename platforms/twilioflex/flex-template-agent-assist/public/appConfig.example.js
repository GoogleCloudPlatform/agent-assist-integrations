/**
 * Copyright 2025 Google LLC
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

var appConfig = {
  pluginService: {
    enabled: true,
    url: '/plugins',
  },
  insights: {
    analyticsUrl: 'http://localhost:8081',
  },
  ytica: false,
  logLevel: 'info',
  showSupervisorDesktopView: true,
  custom_data: {
    serverless_functions_protocol: 'http',
    serverless_functions_port: '3001',
    serverless_functions_domain_agent_assist: 'localhost',
    common: {},
    features: {},
  },
};
