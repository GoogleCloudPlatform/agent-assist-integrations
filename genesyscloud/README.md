# Genesys Cloud Integration for Google Agent Assist

This directory contains reference implementations and deployment configurations for integrating Google Agent Assist with Genesys Cloud.

## Modules

* **[`frontend/`](./frontend/)**: Express/Node.js web application hosting the Agent Assist UI Modules as a Genesys Cloud Interaction Widget.
* **[`genesyscloud-audiohook/`](./genesyscloud-audiohook/)**: Python/Flask WebSocket server implementing the Genesys Cloud AudioHook protocol to stream dual-channel voice conversations into Dialogflow CX.

## Comprehensive Integration Guide

For the full, step-by-step developer guide covering Google Cloud deployment, Genesys Cloud setup, and Salesforce Service Cloud Open CTI / LWC integration, see:

👉 **[Genesys Cloud & Agent Assist Integration Guide](../GENESYS_INTEGRATION_GUIDE.md)**

## Official Google Cloud Documentation

* [Genesys Cloud Application Integration](https://cloud.google.com/agent-assist/docs/genesys-cloud-app)
* [Genesys Cloud Voice Integration](https://cloud.google.com/agent-assist/docs/genesys-cloud-voice)
