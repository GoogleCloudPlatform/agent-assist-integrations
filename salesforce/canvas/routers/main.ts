import crypto from 'crypto';
import dotenv from 'dotenv';
import express from 'express';
import {uuid} from 'uuidv4';

dotenv.config();

const router = express.Router();

const consumerSecret = process.env.MAIN_CANVAS_CONSUMER_SECRET;
const clientId = process.env.MAIN_CANVAS_CONSUMER_KEY;
const proxyServer = process.env.PROXY_URL;

/*
 * handle Canvas signed POST request containing Canvas context and attempt
 * to decode the request using our Canvas application's consumer secret
 */
router.post('/', (req, res) => {
  if (!consumerSecret || !clientId) {
    res.send('Canvas OAuth settings missing');
  }

  const signedRequest = req.body.signed_request;
  const [encodedSignature, encodedEnvelope] = signedRequest.split('.');
  const check = crypto.createHmac('sha256', consumerSecret)
                    .update(encodedEnvelope)
                    .digest('base64');

  if (check !== encodedSignature) {
    res.send('Signature does not match.');
  }

  const signedRequestJson =
      JSON.parse(Buffer.from(encodedEnvelope, 'base64').toString('ascii'));

  const {context, client} = signedRequestJson;

  const {conversationProfile, features, debug} = req.query;

  if (!features || typeof features !== 'string') {
    res.send(
        'Error - please provide a features list in the URL query parameters');
    return;
  }

  if (!conversationProfile || typeof conversationProfile !== 'string') {
    res.send(
        'Error - please provide a conversation profile name in the URL query parameters');
    return;
  }

  const [, projectLocation] =
      conversationProfile.match(
          /(^projects\/[^/]+\/locations\/[^/]+)\/conversationProfiles\/[^/]+$/) ||
      [];

  if (!projectLocation) {
    res.send(
        'Error - please provide a correctly formatted conversation profile name ' +
        'in the URL query parameters. Format: ' +
        '"projects/<project_id>/locations/<location_id>/conversationProfiles/<conversation_profile_id>"');
    return;
  }

  // Generate a random conversation ID for demo purposes. In a real app, this
  // would come from an external source.
  const conversationId = `a${uuid()}`;

  const conversationName = `${projectLocation}/conversations/${conversationId}`;

  res.render('main', {
    clientId,
    proxyServer,
    salesforceToken: client.oauthToken,
    salesforceContext: context,
    signedRequestJson,
    conversationId,
    conversationProfile,
    conversationName,
    features,
    debug,
  });
});

export {router as mainRouter};
