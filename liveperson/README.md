# LivePerson Integration

## Description

This directory will contain instructions and code samples on how the Agent Assist modules can be integrated into LivePerson to surface real-time suggestions. This will include two repositories:

1. An application server that will serve the Agent Assist modules UI.
2. A proxy server that will handle authentication and calls to the Dialogflow API.

Both of these will need to be deployed in order for the LivePerson integration to work. 

In addition, we will provide setup instructions for registering the application with LivePerson and configuring the Agent Assist widget.

## High-level steps

1. Deploy the UI Modules application server located in the `/frontend` directory.
2. Deploy the proxy server located in the `/proxy-server` directory.
3. Install the Conversational Cloud application in LivePerson.
4. Update the missing environment variables in both servers, and re-deploy them.
5. Configure the Agent Assist widget in LivePerson.

## 1. Deploy the Application server

 - [Instructions for deployment](./frontend/README.md)

## 2. Deploy the Proxy server

 - [Instructions for deployment](./proxy-server/README.md)

## 3. Install a Conversational Cloud application

In order for your application to be able to use LivePerson OAuth authentication, you will need to register it as a Conversational Cloud application in your LivePerson account. These instructions can be found at:
https://developers.liveperson.com/conversational-cloud-applications-installing-conversational-cloud-applications.html

Users will need to contact a LivePerson team member who can facilitate this installation. 

The Manifest Schema should look like the following (please replace all instances of `{APPLICATION_SERVER_URL}` with the URL of the UI application server from above):

```
{
  "client_name": "com.liveperson.GoogleAgentAssist",
  "display_name": "Agent Assist",
  "response_types": ["code"],
  "scope": "msg.consumer",
  "entry_uri": "{APPLICATION_SERVER_URL}",
  "grant_types": [
    "authorization_code",
    "client_credentials",
    "refresh_token"
  ],
  "redirect_uris": [
    "{APPLICATION_SERVER_URL}/home"
  ]
}
```

## 4. Update the missing environment variables

Once the Conversational Cloud application has been installed, LivePerson will provide a client ID and client secret. Please go back and update the environment variables of both services to include the correct values for `LP_CLIENT_ID` and `LP_CLIENT_SECRET`. Once that is done, re-deploy both applications.

## 5. Configure LivePerson widget

Please follow the instructions at: https://developers.liveperson.com/add-agent-widgets-add-your-own-widgets-to-the-agent-workspace.html

The URL of the application should be in the following format:

```
{APPLICATION_SERVER_URL}?conversationProfile={CONVERSATION_PROFILE_NAME}&features={FEATURES}`
```

 - Replace `{APPLICATION_SERVER_URL}` with the URL of the UI application server from above.
 - Replace `{CONVERSATION_PROFILE_NAME}` with the name of the Conversation Profile you would like to use (example: `projects/my-project/conversationProfiles/abc123`).
 - Replace `{FEATURES}` with a comma-separated list of Agent Assist features you would like the application to include.
    Currently supported features include: `SMART_REPLY`, `ARTICLE_SUGGESTION`, `FAQ`, `ARTICLE_SEARCH`, and `CONVERSATION_SUMMARIZATION`.
    Please only include features that are configured on your conversation profile.

Example URL:

```
https://my-project.wm.r.appspot.com?conversationProfile=projects/my-project/conversationProfiles/abc123&features=ARTICLE_SUGGESTION,CONVERSATION_SUMMARIZATION
```

## Disclaimer

This product is covered by the [Pre-GA Offerings Terms](https://cloud.google.com/terms/service-terms#1) of the Google Cloud Terms of Service. Pre-GA products might have limited support, and changes to pre-GA products might not be compatible with other pre-GA versions. For more information, see the [launch stage descriptions](https://cloud.google.com/products#product-launch-stages).
