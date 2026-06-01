/**
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


import timeout from 'connect-timeout';
import cookieParser from 'cookie-parser';
import dotenv from 'dotenv';
import express from 'express';
import path, { dirname } from 'path';
import { fileURLToPath } from 'url';
import logger from 'morgan';



const app = express();

export default app;
// During local testing, enable the
// below line and replace the process.evn
// with the envVariable constant
// const envVaribale = dotenv.config();
const __dirname = dirname(fileURLToPath(import.meta.url));


const {
  APPLICATION_SERVER_URL,
  CHANNEL,
  CONVERSATION_PROFILE,
  GENESYS_CLOUD_REGION,
  OAUTH_CLIENT_ID,
  PROXY_SERVER,
  FEATURES,
} = process.env;


app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');
app.use(logger('dev'));

// Set 30s timeout for all requests.
// Following instructions from
// https://github.com/expressjs/timeout#as-top-level-middleware)
app.use(timeout('30s'));
app.use(express.json());
app.use(haltOnTimedout);
app.use(cookieParser());
app.use(express.static(__dirname));
app.use(haltOnTimedout);
app.use(express.urlencoded({extended: false}));

function haltOnTimedout(req, res, next) {
  if (!req.timedout) next();
}

/**
 * Try directly render the view
 */

// error handler
app.use((err, req, res, next) => {
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? {} : {};
  res.status(err.status || 500);
  res.render('error');
});


app.get('/', (req, res) => {
const conversationProfile = CONVERSATION_PROFILE;
const features = FEATURES;
const clientID = OAUTH_CLIENT_ID;
const proxyServer = PROXY_SERVER;
const applicationServer = APPLICATION_SERVER_URL;
const genesysCloudRegion = GENESYS_CLOUD_REGION;
const channel = CHANNEL;
res.render("main", {conversationProfile,clientID,features,proxyServer,applicationServer,genesysCloudRegion,channel});
})


app.get('/ping', (req, res) => {
    res.send("pong");
})


const PORT = process.env.PORT || 8080;


app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});