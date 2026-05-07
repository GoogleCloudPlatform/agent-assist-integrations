# Salesforce Agent Assist UI Integration (LWC)

Integrate Agent Assist UI modules with Salesforce to provide real-time suggestions for your human agents.

## Integrate Agent Assist in Salesforce

Please see [this guide](https://cloud.google.com/agent-assist/docs/salesforce) for detailed steps on how to install and configure the Agent Assist Lightning Web Component in your Salesforce instance.

## Development Notes

### Compatibility with Lightning Web Security

By default, UI Modules js will not load into an LWC because of Lightning Locker or Lightning Web Security conflicts with Angular's ZoneJS. Angular uses ZoneJS/NgZone to patch/wrap native browser events in order to listen for them. One patch that it loads in particular is incompatible with LWS, but it can be disabled:

```js
// This global flag allows the JS to load to work in an LWC
window.__Zone_disable_on_property = true;
// Put it at the top of .../lwc/componentName/componentName.js files after the imports
```

### Agent Assist Event Namespacing

Because of Salesforce's tabbed conversation management, it is neccesary for Agent Assist UI module instances and events to be "namespaced". This prevents crosstalk between the instances.

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
    eventName: String,
    eventPayload: Object,
    { namespace: uniqueIdForUiModuleInstance } // binds event to namespaced instance
  )

  addAgentAssistEventListener(
    eventName,
    eventHandler,
    { namespace: uniqueIdForUiModuleInstance } // binds event to namespaced instance
  );
```

### Local Configuration and Customization

High-level behavioral configuration parameters (e.g., the Dialogflow API version, polling attempts, delays, token refresh intervals, and console logging throttle rates) are fully centralized in [config.js](file:///Users/jblakey/projects/agent-assist-ui-modules/salesforce/aa-lwc/force-app/main/default/lwc/agentAssistContainerModule/config.js) right next to the main controller:

* **`DIALOGFLOW_API_VERSION`**: Specifies the Dialogflow API version used for API requests (defaults to `"v2beta1"`).
* **`TOKEN_REFRESH_CHECK_INTERVAL_MS`**: Interval in milliseconds to automatically check and refresh UI Connector JWT tokens.
* **`TOKEN_HEALTHY_LOG_INTERVAL_MS`**: Controls console debug log verbosity by throttling the "Token is healthy" status log to output at most once every X milliseconds (defaults to 5 minutes).
* **Polling Configuration**: Customize Dialogflow conversation status check retries and delays via `POLL_MAX_RETRIES`, `POLL_INITIAL_DELAY_MS`, and `POLL_DELAY_INCREMENT_MS`.

### Code Quality and Formatting

The LWC codebase uses Prettier (configured via `.prettierrc`) to enforce code formatting and style guidelines. You can run checks and format the source tree using the following scripts:

```bash
# Verify code style compliance
npm run lint

# Automatically format and clean the codebase
npm run lint:fix
```

