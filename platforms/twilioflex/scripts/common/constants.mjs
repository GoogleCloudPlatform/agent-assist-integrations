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

import fs from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

export const placeholderPrefix = 'YOUR';
export const serverlessDir = 'serverless-functions';
export const serverlessSrc = `${serverlessDir}/src`;
export const flexConfigDir = 'flex-config';
export const defaultPluginDir = 'plugin-flex-ts-template-v2';
export const addonsDir = 'addons';
export const cliConfigPath = path.resolve(os.homedir(), '.twilio-cli/config.json');
export const infraAsCodeDir = 'infra-as-code';
export const terraformDir = `${infraAsCodeDir}/terraform`

const mappingDefinitionPath = '../config/mappings.json';
export const varNameMapping = JSON.parse(fs.readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), mappingDefinitionPath)));