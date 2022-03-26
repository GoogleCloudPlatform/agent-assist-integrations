# Agent Assist Modules Proxy Server

## Introduction

The purpose of this documentation is to set up a proxy server that can be used in conjunction with Agent Assist Modules application server to simplify authentication with the Dialogflow API.

Although it is possible to set up this integration deployment on any hosting platform, these instructions will use [Google's Cloud Run](https://cloud.google.com/run/).

## Initial setup
Open the project repository, and create a `.env` file in the `/liveperson/proxy-server` directory. The following environment variables will need to be defined:

`LP_ACCOUNT_ID`
LivePerson account ID.

`LP_CLIENT_ID`
Your LivePerson client ID. This will be provided by LivePerson once the Conversational Cloud application has been installed.
(Skip for now, update once the information has been provided).

`LP_CLIENT_SECRET`
Your LivePerson client secret. This will be provided by LivePerson once the Conversational Cloud application has been installed.
(Skip for now, update once the information has been provided).

`LP_SENTINEL_DOMAIN`
Go to https://developers.liveperson.com/domain-api.html. Enter your account number, and look up the domain for “sentinel”.

`LP_ACCOUNT_CONFIG_READONLY_DOMAIN`
Go to https://developers.liveperson.com/domain-api.html. Enter your account number, and look up the domain for “accountConfigReadOnly”.

`APPLICATION_SERVER_URL`
The origin URL of the UI application server. Use the URL that was generated when deploying the UI application server in Part 1.

`JWT_SECRET`
A “secret” phrase that will be used to sign the authentication tokens. Any phrase may be used, although a long, random secret is most secure. Please see best practices at https://fusionauth.io/learn/expert-advice/tokens/building-a-secure-jwt/#keys.
 
Example .env file:

```
LP_ACCOUNT_ID = 12345678
LP_CLIENT_ID = abc-123-f0f0
LP_CLIENT_SECRET = abc123abc123abc123abc123
LP_SENTINEL_DOMAIN = va.sentinel.liveperson.net
LP_ACCOUNT_CONFIG_READONLY_DOMAIN = z1.acr.liveperson.net
APPLICATION_SERVER_URL = https://my-project.wm.r.appspot.com
JWT_SECRET = an_example_JWT_secret_phrase_please_use_something_better
```

## Deployment

### Setting up gcloud CLI

The deployment processes outlined in this README utilize gcloud CLI commands. Follow the steps below to set up the gcloud CLI locally for this deployment.

1. On the gcloud CLI [documentation page](https://cloud.google.com/sdk/docs/quickstarts), select your OS and follow the instructions for the installation.
2. Run ``gcloud config get-value project`` to check the GCP Project configured.
3. Go into the Dialogflow agent’s settings and check the Project ID associated with the agent. The GCP Project configured in the gcloud CLI should match the agent’s Project ID.
4. If the project IDs do not match, run ``gcloud config set project PROJECT-ID``, replacing PROJECT-ID with the Project ID from step 3.


### App Engine
https://cloud.google.com/appengine/docs/standard/nodejs/quickstart

Once the gcloud CLI has been configured, create an App Engine application in your Google Cloud project if one does not exist:

```
gcloud app create --project=[YOUR_PROJECT_ID]
```

Then, navigate to the `/liveperson/proxy-server` directory in this repository, and run:

```
tsc && gcloud app deploy
```

Once the command has been run, the CLI will display the URL to which the application will be deployed (target_url). Once you have this, please update the `DF_PROXY_SERVER_URL` environment variable in the `.env` file located in the `/liveperson/frontend` directory, and re-deploy the UI application server. 

### Cloud Run

#### Service Account Setup (GCP)

For the integration to function properly, it is necessary to create a Service Account in your GCP Project. See [this page](https://cloud.google.com/dialogflow/docs/quick/setup#sa-create) of the documentation for more details.

Follow the steps below to create a Service Account and set up the integration.

1. Select the project associated with your Agent Assist resources.
2. Click on the navigation menu in the GCP console, hover over "IAM & admin", and click "Service accounts".
3. Click on "+ CREATE SERVICE ACCOUNT", fill in the details, and give it the "Dialogflow Client API" role.

### Enable APIs

1. Navigate to your desired GCP project.
2. Click on the navigation menu in the GCP console and click "Billing". Set up and enable billing for the project.
3. Enable Cloud Build and Cloud Run API for the project
[here](https://console.cloud.google.com/flows/enableapi?apiid=cloudbuild.googleapis.com,run.googleapis.com).
4. Clone this git repository onto your local machine or development environment:
`git clone [repository url]`
5. Open the root directory of the repository on your local machine or development environment.

#### Deploying via CLI

In your local terminal, change the active directory to the repository’s root directory.

Run the following command to save the state of your repository into [GCP Container Registry](https://console.cloud.google.com/gcr/). Replace `PROJECT-ID` with your GCP Project ID.

```shell
gcloud builds submit --tag gcr.io/PROJECT-ID/agent-assist-modules-proxy-server
```

Deploy your integration to live using the following command. Replace `PROJECT-ID` with your agent’s GCP project ID, and `SERVICE-ACCOUNT-EMAIL` with your service account client email.

```shell
gcloud run deploy --image gcr.io/PROJECT-ID/agent-assist-modules-proxy-server --service-account=SERVICE-ACCOUNT-EMAIL --memory 1Gi --platform managed
```

 - When prompted for a region, select a region (for example, ``us-central1``).
 - When prompted for a service name hit enter to accept the default.
 - When prompted to allow unauthenticated invocations press ``y``.

More information can be found in Cloud Run
[documentation](https://cloud.google.com/run/docs/deploying).

You can view a list of your active integration deployments under [Cloud Run](https://console.cloud.google.com/run) in the GCP Console.


#### Shutting Down the Proxy Server

In order to shut down the proxy server set up via the steps in this README, only deleting the Cloud Run service is required.

In your local terminal, run the following command and select the previously chosen target platform to list active deployments:

```shell
gcloud beta run services list
```

Then run the following command:

```shell
gcloud beta run services delete agent-assist-modules-proxy-server
```

## Disclaimer

This product is covered by the [Pre-GA Offerings Terms](https://cloud.google.com/terms/service-terms#1) of the Google Cloud Terms of Service. Pre-GA products might have limited support, and changes to pre-GA products might not be compatible with other pre-GA versions. For more information, see the [launch stage descriptions](https://cloud.google.com/products#product-launch-stages).
