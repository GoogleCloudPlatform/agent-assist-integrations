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
