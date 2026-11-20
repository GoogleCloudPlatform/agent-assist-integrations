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

const path = require('path');

module.exports = (config, { isProd, isDev, isTest }) => {
  /**
   * Customize the webpack by modifying the config object.
   * Consult https://webpack.js.org/configuration for more information
   */

  for (const plugin of config.plugins) {
    // Change tsconfig for ForkTsCheckerWebpackPlugin to version which excludes test files
    if (plugin.tsconfig && plugin.options?.tsconfig) {
      const tsconfig = plugin.tsconfig.replace('.json', '.build.json');
      plugin.options.tsconfig = tsconfig;
      plugin.tsconfig = tsconfig;
    }
  }

  return {
    ...config,
    performance: {
      ...config.performance,
      hints: false,
    },
    module: {
      ...config.module,
      rules: [
        ...config.module.rules,
        {
          test: /index\.ts$/,
          include: [path.join(__dirname, 'src/feature-library/')],
          use: 'import-glob',
        },
        {
          test: /\.ts$/,
          include: [path.join(__dirname, 'src/utils/feature-loader/')],
          use: 'import-glob',
        },
        {
          test: /\.tsx$/,
          include: [path.join(__dirname, 'src/utils/feature-loader/')],
          use: 'import-glob',
        },
      ],
    },
  };
};
