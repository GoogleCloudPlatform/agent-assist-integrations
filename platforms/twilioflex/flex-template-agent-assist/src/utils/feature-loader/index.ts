/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import * as Flex from '@twilio/flex-ui';

import { FeatureDefinition } from '../../types/feature-loader';
import { addLoadedFeature, setLoadedFeaturesPopulated } from '../configuration';
import * as Actions from './actions';
import * as AgentAssistEvents from './agent-assist-events';
import * as Channels from './channels';
import * as ChatOrchestrator from './chat-orchestrator';
import * as Components from './components';
import * as CssOverrides from './css-overrides';
import * as Events from './events';
import * as JsClientEvents from './jsclient-event-listeners';
import * as KeyboardShortcuts from './keyboard-shortcuts';
import * as Logger from './logger';
import * as Notifications from './notifications';
import * as NotificationEvents from './notification-events';
import * as PasteElements from './paste-elements';
import * as Reducers from './reducers';
import * as Strings from './strings';
import * as TeamsFilters from './teams-filters';
import * as SyncClientTokenUpdated from '../sdk-clients/sync/tokenUpdated';
import * as TaskRouterReplaceCompleteTask from '../serverless/TaskRouter/CompleteTask';
import * as SendLogsToBrowserConsole from '../logger/sendLogsToBrowserConsole';
// @ts-ignore
// eslint-disable-next-line import/no-useless-path-segments
import features from '../../feature-library/*/index.ts';

export const initFeatures = (flex: typeof Flex, manager: Flex.Manager) => {
  if (typeof features === 'undefined') {
    // no features discovered; abort
    return;
  }

  for (const file of features) {
    // Each feature index file should export a `register` function for us to invoke
    if (!file.register) {
      console.error('Feature found, but its index file does not export a `register` function', file);
      return;
    }

    try {
      const feature = file.register() as FeatureDefinition;

      if (feature && feature.name) {
        loadFeature(flex, manager, feature);
        addLoadedFeature(feature.name);
      }
    } catch (error) {
      console.error('Error loading feature:', error);
    }
  }

  setLoadedFeaturesPopulated(true);

  // Register built-in hooks
  Actions.addHook(flex, manager, 'built-in TaskRouterService', TaskRouterReplaceCompleteTask);
  Events.addHook(flex, manager, 'built-in Sync client', SyncClientTokenUpdated);
  Logger.addHook(flex, manager, 'built-in logger to browser console', SendLogsToBrowserConsole);

  // After all features have initialized, execute deferred hooks
  Logger.init(manager);
  CssOverrides.init(manager);
  PasteElements.init(flex);
  Reducers.init(manager);
  Strings.init(manager);
  KeyboardShortcuts.init(flex, manager);
  Components.init(flex, manager);
  TeamsFilters.init(flex, manager);
};

export const loadFeature = (flex: typeof Flex, manager: Flex.Manager, feature: FeatureDefinition) => {
  // Features invoke this function to register their hooks
  const name = feature.name ?? 'unknown';
  const hooks = feature.hooks ?? [];
  console.info(`%cFeature enabled: ${name}`, 'background: green; color: white;');

  for (const hook of hooks) {
    // Each hook exports a function or property for us to handle.
    // Register the hook based on the export(s) present.

    if (hook.actionHook) {
      Actions.addHook(flex, manager, name, hook);
    }

    if (hook.channelHook) {
      Channels.addHook(flex, manager, name, hook);
    }

    if (hook.chatOrchestratorHook) {
      ChatOrchestrator.addHook(flex, manager, name, hook);
    }

    if (hook.componentHook) {
      Components.addHook(flex, manager, name, hook);
    }

    if (hook.cssOverrideHook) {
      CssOverrides.addHook(flex, manager, name, hook);
    }

    if (hook.eventHook) {
      Events.addHook(flex, manager, name, hook);
    }

    if (hook.jsClientHook) {
      JsClientEvents.addHook(flex, manager, name, hook);
    }

    if (hook.keyboardShortcutHook) {
      KeyboardShortcuts.addHook(flex, manager, name, hook);
    }

    if (hook.loggerHook) {
      Logger.addHook(flex, manager, name, hook);
    }

    if (hook.notificationHook) {
      Notifications.addHook(flex, manager, name, hook);
    }

    if (hook.notificationEventHook) {
      NotificationEvents.addHook(flex, manager, name, hook);
    }

    if (hook.pasteElementHook) {
      PasteElements.addHook(flex, manager, name, hook);
    }

    if (hook.reducerHook) {
      Reducers.addHook(flex, manager, name, hook);
    }

    if (hook.stringHook) {
      Strings.addHook(flex, manager, name, hook);
    }

    if (hook.systemStringHook) {
      Strings.addSystemHook(flex, manager, name, hook);
    }

    if (hook.teamsFilterHook) {
      TeamsFilters.addHook(flex, manager, name, hook);
    }
  }
};

export const initAgentAssistFeatures = (flex: typeof Flex, manager: Flex.Manager) => {
  if (typeof features === 'undefined') {
    // no features discovered; abort
    return;
  }

  for (const file of features) {
    // Each feature index file should export a `register` function for us to invoke
    if (!file.register) {
      console.error('Feature found, but its index file does not export a `register` function', file);
      return;
    }

    try {
      const feature = file.register() as FeatureDefinition;

      if (feature && feature.name) {
        loadAgentAssistEvents(flex, manager, feature);
      }
    } catch (error) {
      console.error('Error loading feature:', error);
    }
  }
};

export const loadAgentAssistEvents = async (flex: typeof Flex, manager: Flex.Manager, feature: FeatureDefinition) => {
  const name = feature.name ?? 'unknown';
  const hooks = feature.hooks ?? [];
  for (const hook of hooks) {
    if (hook.agentAssistEventHook) {
      AgentAssistEvents.addHook(flex, manager, name, hook);
    }
  }
};
