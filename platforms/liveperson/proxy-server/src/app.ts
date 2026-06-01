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
import cors from 'cors';
import dotenv from 'dotenv';
import express, {
  NextFunction,
  Request,
  RequestHandler,
  Response,
} from 'express';
import jwt from 'jsonwebtoken';
import path from 'path';

import { authRouter } from './routers/auth/auth.router';
import { dialogflowv2beta1Router } from './routers/v2beta1';

dotenv.config({ path: path.resolve(__dirname, '../.env') });

const app = express();
const PORT = process.env.PORT || 3000;

const authMiddleware: RequestHandler = (req, res, next) => {
  const token = req.headers.authorization;
  try {
    jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch (err) {
    res
      .status(401)
      .json({ error: { code: 401, message: 'Could not authenticate user' } });
  }
};

// Set 30s timeout for all requests.
// Following instructions from
// https://github.com/expressjs/timeout#as-top-level-middleware)
app.use(timeout('30s'));

app.use(cors({ origin: process.env.APPLICATION_SERVER_URL }));
app.use(haltOnTimedout);

// Keep request body as plain text, since we are passing it directly to the
// Dialogflow API.
app.use(express.text({ type: 'application/json' }));
app.use(haltOnTimedout);

function haltOnTimedout(req: Request, res: Response, next: NextFunction) {
  if (!req.timedout) {
    next();
  }
}

app.get('/ping', (req, res) => {
  res.status(200).send('OK');
});

app.use(
  '/v2beta1/projects/:projectId',
  authMiddleware,
  dialogflowv2beta1Router
);

app.use(
  '/v2beta1/projects/:projectId/locations/:locationId',
  authMiddleware,
  dialogflowv2beta1Router
);

app.use('/auth', authRouter);

app.listen(PORT, () => {
  console.log(`Listening on port ${PORT}`);
});
