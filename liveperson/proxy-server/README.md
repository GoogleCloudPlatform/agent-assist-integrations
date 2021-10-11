# Agent Assist UI Modules Proxy Server

## Introduction

The purpose of this documentation is to set up a proxy server that can be used in conjunction with Agent Assist UI Modules to simplify authentication with the Dialogflow API.

Although it is possible to set up this integration deployment on any hosting platform, these instructions will use [Google's Cloud Run](https://cloud.google.com/run/).

## Initial Setup

### Setting up gcloud CLI

The deployment process for GCP Cloud Run via this README utilizes gcloud CLI commands. Follow the steps below to set up gcloud CLI locally for this deployment.

1. On the gcloud CLI [documentation page](https://cloud.google.com/sdk/docs/quickstarts), select your OS and follow the instructions for the installation.
2. Run ``gcloud config get-value project`` to check the GCP Project configured.
3. Go into the Dialogflow agent’s settings and check the Project ID associated with the agent. The GCP Project configured in the gcloud CLI should match the agent’s Project ID.
4. If the project IDs do not match, run ``gcloud config set project PROJECT-ID``, replacing PROJECT-ID with the Project ID from step 3.

### Service Account Setup (GCP)

For the integration to function properly, it is necessary to create a Service Account in your GCP Project. See [this page](https://cloud.google.com/dialogflow/docs/quick/setup#sa-create) of the documentation for more details.

Follow the steps below to create a Service Account and set up the integration.

1. Select the project associated with your Agent Assist resources.
2. Click on the navigation menu in the GCP console, hover over "IAM & admin", and click "Service accounts".
3. Click on "+ CREATE SERVICE ACCOUNT", fill in the details, and give it the "Dialogflow Client API" role.

## Deploying the Integration

### Setup

1. Navigate to your desired GCP project.
2. Click on the navigation menu in the GCP console and click "Billing". Set up and enable billing for the project.
3. Enable Cloud Build and Cloud Run API for the project
[here](https://console.cloud.google.com/flows/enableapi?apiid=cloudbuild.googleapis.com,run.googleapis.com).
4. Clone this git repository onto your local machine or development environment:
`git clone [repository url]`
5. Open the root directory of the repository on your local machine or development environment.

### Deploying Using Cloud Run

In your local terminal, change the active directory to the repository’s root directory.

Run the following command to save the state of your repository into [GCP Container Registry](https://console.cloud.google.com/gcr/). Replace PROJECT-ID with your GCP Project ID.

```shell
gcloud builds submit --tag gcr.io/PROJECT-ID/dialogflow-proxy-server
```

Deploy your integration to live using the following command. Replace PROJECT-ID with your agent’s GCP project ID, and SERVICE-ACCOUNT-EMAIL with your service account client email.

```shell
gcloud run deploy --image gcr.io/PROJECT-ID/dialogflow-proxy-server --service-account=SERVICE-ACCOUNT-EMAIL --memory 1Gi --platform managed
```

 - When prompted for a region, select a region (for example, ``us-central1``).
 - When prompted for a service name hit enter to accept the default.
 - When prompted to allow unauthenticated invocations press ``y``.

More information can be found in Cloud Run
[documentation](https://cloud.google.com/run/docs/deploying).

You can view a list of your active integration deployments under [Cloud Run](https://console.cloud.google.com/run) in the GCP Console.


## Post-deployment

### Shutting Down the Proxy Server

In order to shut down the proxy server set up via the steps in this README, only deleting the Cloud Run service is required.

In your local terminal, run the following command and select the previously chosen target platform to list active deployments:

```shell
gcloud beta run services list
```

Then run the following command:

```shell
gcloud beta run services delete dialogflow-proxy-server
```
