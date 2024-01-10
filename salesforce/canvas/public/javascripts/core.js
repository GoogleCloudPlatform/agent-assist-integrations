/**
 * Adds a transfer number to the Dialogflow conversation. Allows a customer to
 * call the agent.
 */
function addConversationPhoneNumber(
    authToken, eventBasedConnectionEstablished, conversationInitialized,
    proxyServerEndpoint, conversationName, existingTelephonyNumber) {
  if (!eventBasedConnectionEstablished || !conversationInitialized) return;

  if (existingTelephonyNumber) {
    showTelephonyNumber(existingTelephonyNumber);
    return;
  }

  // For demo purposes only
  fetch(
      proxyServerEndpoint + '/v2beta1/' + conversationName +
          ':addConversationPhoneNumber',
      {
        method: 'POST',
        headers: [['Authorization', authToken]],
        body: JSON.stringify({}),
      })
      .then(function(res) {
        return res.json();
      })
      .then(function(body) {
        showTelephonyNumber(body.phoneNumber);
      });
}

function showTelephonyNumber(number) {
  var proxyNumber = number.replace(
      /(\+\d)(\d{3})(\d{3})(\d+)/, function(match, p1, p2, p3, p4) {
        return p2 + '-' + p3 + '-' + p4;
      });

  var messagesContainer = document.querySelector('.messages-container');

  const emptyTranscriptEl =
      '<h4 class="empty-transcript">To begin session, dial &nbsp;<span class="proxy-number">' +
      proxyNumber + '</span>.</h4>';

  if (messagesContainer) {
    messagesContainer.insertAdjacentHTML('afterbegin', emptyTranscriptEl);
  }
}

/**
 * Exchanges the agent's Salesforce OAuth token for one that can be used to call
 *the Dialogflow API.
 **/
function registerAuthToken(proxyServerEndpoint, salesforceToken) {
  return fetch(proxyServerEndpoint + '/register', {
           method: 'POST',
           headers: [['Authorization', salesforceToken]],
         })
      .then(function(res) {
        return res.json();
      })
      .then(function(body) {
        return body.token;
      });
}
