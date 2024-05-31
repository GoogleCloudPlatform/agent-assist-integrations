# GenesysCloud Integration

## Description

This document walks you through the steps required to integrate UI modules with Genesys Cloud and surface real-time suggestions. The following actions are included in this tutorial

## High-level steps

1. Deploy the application server for rendering agent assist UI Module in cloud run, follow the steps mentioned in `/frontend` directory
2. Deploy the backend server for the UI Module to call Dialogflow API, register authentication token, and setup cloud pub/sub and redis memory store 
3. Set up the Interaction Widget in Genesys Cloud
4. Create OAuth Client
5. Configure Messengers in Genesys Cloud
6. Configure the Agent Assist integration with the Interaction Widget in Genesys Cloud
7. Using the Genesys cloud Web chat/messaging Tools to test the integration

## 1. Deploy the Application server

 - [Instructions for deployment](./frontend/README.md)

## 2. Deploy the Backend server

 - [Instructions for deployment](https://github.com/GoogleCloudPlatform/agent-assist-integrations)

## 3. Set up the Interaction Widget in Genesys Clou

Currently, Genesys Cloud supports two types of messaging channels. These channels are designed to enhance customer engagement and provide efficient communication between agents and customers through chat.

The messenger option allows agents to manage multiple conversations and generate summaries. Both the messenger and chat V2 options feature real-time communication and are able to communicate with Agent Assist.  However, starting from 2020, Genesys are recommending all their customers to use Messenger as it has more available options for facilitating agent’s work like Asynchronous update and unlimited timeout. More details of the [feature comparison](https://help.mypurecloud.com/articles/web-messaging-and-web-chat-feature-comparison/) for the web messaging and web chat integration.


### Configure the Interaction Widget
To use either integration, users must configure the interaction widget. The widget monitors the ongoing chat and transfers the discussion data to Agent Assist, which then creates recommendations based on the context.

To configure the Integration Widget, follow the instructions for setting up an Interaction Widget integration in Genesys Cloud.

The URL of the application should be in the following format, with the following replacements:

Replace {APPLICATION_SERVER_URL} with the URL of your UI application server.
Append `&conversationid={{pcConversationId}}&gcHostOrigin={{gcHostOrigin}}&gcTargetEnv={{gcTargetEnv}}` at the end. 

```
{APPLICATION_SERVER_URL}?conversationid={{pcConversationId}}&gcHostOrigin={{gcHostOrigin}}&gcTargetEnv={{gcTargetEnv}}
```

The `{pcConversationId}` and `{gcHostOrigin}`, `{gcTargetEnv}` variables are used to construct the Genesys cloud client application to communicate with Genesys cloud. Once the iframe for the client application load, Genesys cloud would populate those variables automatically.

Update the Iframe Sandbox Options to `allow-scripts`,`allow-same-origin`,`allow-forms`,`allow-modals`,allow-popups

Update the Iframe Feature/Permissions Policy to
clipboard-write, microphone,display-capture


Example URL:
```
https://my-project.wm.r.appspot.com?conversationid={{pcConversationId}}&gcHostOrigin={{gcHostOrigin}}&gcTargetEnv={{gcTargetEnv}}
```


## 4. Create OAuth Client

You need to create a new OAuth client (Token Implicit Grant) to integrate with Genesys Cloud OAuth authentication. Follow the instructions for doing this in the [Genesys Cloud documentation](https://help.mypurecloud.com/articles/create-an-oauth-client/).

Ensure that the Grant Type is Implicit Grant (Browser). Add your application URL to the Authorized redirect URIs section in the following format

Update the Oauth client token duration to 3600 second, to match the JWT token for the Dialogflow API access of 1 hour.

`{APPLICATION_SERVER_URL}?conversationProfile={CONVERSATION_PROFILE_NAME}&features={FEATURES}`

- Replace `{APPLICATION_SERVER_URL}` with the URL of your UI application server.
- Replace {CONVERSATION_PROFILE_NAME} with the name of the Conversation Profile you would like to use (example: projects/my-project/conversationProfiles/abc123).
- Replace {FEATURES} with a comma-separated list of Agent Assist features you would like the application to include. Currently supported features include: SMART_REPLY, ARTICLE_SUGGESTION, and CONVERSATION_SUMMARIZATION. Only include features configured in your conversation profile. Currently the following features are supported in Genesys cloud
* ARTICLE_SUGGESTION
* FAQ
* ARTICLE_SEARCH
* SMART_REPLY
* CONVERSATION_SUMMARIZATION
* AGENT_COACHING
* KNOWLEDGE_ASSIST_V2
* SMART_REPLY


Example URL:

`https://my-project.wm.r.appspot.com?conversationProfile=projects/my-project/conversationProfiles/abc123&features=ARTICLE_SUGGESTION,CONVERSATION_SUMMARIZATION`

## 5. Configure Messengers in Genesys Cloud
To set up the Genesys Cloud messenger, follow the provided steps in this [doc](https://help.mypurecloud.com/articles/deploy-messenger/). After the messenger has been configured, follow the [instructions](https://help.mypurecloud.com/articles/deploy-messenger/) to deploy it. Once the messenger has been deployed, you can use it to communicate with your customers. 

* Example messenger configuration

Within the Appearance tab, you can choose your preferred language from the supported language section. The languages listed here are currently supported by Google Cloud Contact Center. All other sections are subject to your personal preferences. Language support currently differs based on the feature.

## 6. Testing the webchat and web Messenger
The Genesys cloud provides a testing tool for users to test their integration, and the tool is available through [the developer center](https://developer.genesys.cloud/devapps/web-chat-messenger). A simple walkthrough of how to use the developer tool

- In the upper right corner, select Account Selection and click on Add Account, and pick the region where your Genesys Cloud is serviced from, for example USE1. This will associate your account with the tool and you could test all the configurations provided in the previous step
- After adding the account, you could choose to test whether web messenger or web chat V2. 
    - For messenger, select the chat configuration deployed in section and click on start chat
    - For chat V2, select the chat configuration deployed in section and specify the Queue that will receive the message. Then click on the “Populate Fields” button at the Chat Data section. Then click on “Start Chat” 


## Disclaimer

This product is covered by the [Pre-GA Offerings Terms](https://cloud.google.com/terms/service-terms#1) of the Google Cloud Terms of Service. Pre-GA products might have limited support, and changes to pre-GA products might not be compatible with other pre-GA versions. For more information, see the [launch stage descriptions](https://cloud.google.com/products#product-launch-stages).
