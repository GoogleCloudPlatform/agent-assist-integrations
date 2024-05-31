/**
 * Copyright 2024 Google LLC
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

const DotEnvWebpack = require('dotenv-webpack');
module.exports = (config, { isProd, isDev, isTest }) => {
    // We dynamically change the path to the .env that contains the file corresponding to our profile
    let envPath;
    switch (process.env.TWILIO_PROFILE) {
        case 'dev':
            envPath = '.env.dev';
            break;
        case 'stage':
            envPath = '.env.stage';
            break;
        case 'production':
            envPath = '.env.prod';
            break;
    }
    // If path was set, use the dotenv-webpack to inject the variables
    if (envPath) {
        config.plugins.push(new DotEnvWebpack({
            path: envPath,
            ignoreStub:true,
        }));
    }
    return config;
}
