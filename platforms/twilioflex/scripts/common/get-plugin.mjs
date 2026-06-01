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

import shell from "shelljs";

import { defaultPluginDir } from "./constants.mjs";

const getDirectoryName = (originalName, regex) => {
  var tempPluginDir = "";

  if (originalName && shell.test('-d', originalName)) {
    return originalName;
  }
  
  shell.ls('./').forEach((dir) => {
    if (shell.test('-d', dir)) {
      if (dir.match(regex)) {
        tempPluginDir  = dir;
      }
    }
  });
  
  if (!tempPluginDir) {
    console.log("Unable to detect plugin folder name");
    return;
  }
  
  return tempPluginDir;
}

export default () => {
  // The plugin can be renamed via the rename-template script,
  // so we must do some searching before relying on constants.
  const pluginDir = getDirectoryName(defaultPluginDir, /flex-template-.*/);
  const templateDirectory = `${pluginDir}/template-files`;
  const featureDirectory = `${pluginDir}/src/feature-library`;
  const pluginSrc = `${pluginDir}/src`;

  return { pluginDir, templateDirectory, featureDirectory, pluginSrc }
}