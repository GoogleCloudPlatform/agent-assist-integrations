# Salesforce Agent Assist UI Integration (LWC)

Integrate Google Agent Assist UI modules with Salesforce Lightning Service Console to provide real-time AI suggestions for human agents across Messaging, Twilio Flex Voice, and Genesys Cloud Voice.

---

## 1. Official Documentation & Reference Guides

* **[Agent Assist Salesforce LWC Guide](https://cloud.google.com/agent-assist/docs/salesforce)**: Official setup and configuration guide for Salesforce.
* **[Twilio Flex Voice Integration with Salesforce](https://cloud.google.com/agent-assist/docs/twilio-flex-voice)**: Comparative reference architecture for Voice CTI integrations.
* **[Genesys Cloud Voice Integration](https://cloud.google.com/agent-assist/docs/genesys-cloud-voice)**: Official Genesys Cloud voice streaming documentation.
* **[Genesys Cloud & Agent Assist End-to-End Guide](../../GENESYS_INTEGRATION_GUIDE.md)**: Full step-by-step developer deployment guide.
* **[UI Modules Overview](https://cloud.google.com/agent-assist/docs/ui-modules)**: Architecture, features, and deployment options.
* **[UI Modules Container Documentation](https://cloud.google.com/agent-assist/docs/ui-modules-container-documentation)**: Managed container web component specification.
* **[UI Modules Events Documentation](https://cloud.google.com/agent-assist/docs/ui-modules-events-documentation)**: Event listener registration and custom connector dispatching.

---

## 2. Development Notes

### 2.1 Compatibility with Lightning Web Security (LWS)

By default, UI Modules JS will not load into an LWC because of Lightning Locker or Lightning Web Security conflicts with Angular's ZoneJS. Angular uses ZoneJS/NgZone to patch/wrap native browser events in order to listen for them. One patch that it loads in particular is incompatible with LWS, but it can be disabled:

```js
// This global flag allows the JS to load to work in an LWC
window.__Zone_disable_on_property = true;
// Put it at the top of .../lwc/componentName/componentName.js files after the imports
```

### 2.2 Agent Assist Event Namespacing

Because of Salesforce's tabbed conversation management in Lightning Service Console, it is necessary for Agent Assist UI module instances and events to be "namespaced". This prevents suggestion crosstalk between concurrent tabs.

```js
  const containerEl = document.createElement("agent-assist-ui-modules");
  let attributes = [
    ["namespace", uniqueIdForUiModuleInstance],
    // ... other attributes required to instantiate the container module.
    // https://cloud.google.com/agent-assist/docs/ui-modules-container-documentation
  ];
  attributes.forEach((attr) => containerEl.setAttribute(attr[0], attr[1]));
  uiModulesWrapperEl.appendChild(containerEl);

  dispatchAgentAssistEvent(
    eventName,
    eventPayload,
    { namespace: uniqueIdForUiModuleInstance } // binds event to namespaced instance
  );

  addAgentAssistEventListener(
    eventName,
    eventHandler,
    { namespace: uniqueIdForUiModuleInstance } // binds event to namespaced instance
  );
```

### 2.3 Supported Platform Connectors

The LWC dynamically routes to dedicated platform service implementations based on the `platform` property:
* **`messaging`**: Native Salesforce Messaging for In-App and Web / Live Agent Chat.
* **`twilioflex`**: Twilio Flex Voice integration using TaskRouter session discovery.
* **`genesyscloud`**: Genesys Cloud Open CTI Adapter with multi-tiered interaction discovery (`postMessage` softphone ping, shared storage cache, and Apex `Task.CallObject` query).
* **`servicecloudvoice-nice`**: Service Cloud Voice partner telephony.

### 2.4 Local Configuration and Customization

High-level behavioral configuration parameters (e.g., Dialogflow API version, polling attempts, delays, token refresh intervals, and console logging throttle rates) are fully centralized in [`config.js`](./force-app/main/default/lwc/agentAssistContainerModule/config.js):

* **`DIALOGFLOW_API_VERSION`**: Specifies the Dialogflow API version used for API requests (defaults to `"v2beta1"`).
* **`TOKEN_REFRESH_CHECK_INTERVAL_MS`**: Interval in milliseconds to automatically check and refresh UI Connector JWT tokens.
* **`TOKEN_HEALTHY_LOG_INTERVAL_MS`**: Controls console debug log verbosity by throttling the "Token is healthy" status log to output at most once every X milliseconds (defaults to 5 minutes).
* **Polling Configuration**: Customize Dialogflow conversation status check retries and delays via `POLL_MAX_RETRIES`, `POLL_INITIAL_DELAY_MS`, and `POLL_DELAY_INCREMENT_MS`.

### 2.5 Code Quality and Testing

```bash
# Execute Jest unit tests (113 test cases)
npm test

# Verify code style compliance
npm run lint

# Automatically format codebase with Prettier
npm run lint:fix
```
