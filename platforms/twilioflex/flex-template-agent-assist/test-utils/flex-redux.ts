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
import mergeWith from 'lodash/mergeWith';
import unset from 'lodash/unset';
import { AppState } from '../src/types/manager';
import { reduxNamespace } from '../src/utils/state';
import { combineReducers, configureStore, createSlice } from '@reduxjs/toolkit';
import agentAssistReducer from '../../flex-template-agent-assist/src/feature-library/agent-assist/flex-hooks/states/AgentAssist';
import agentAssistAdminReducer from '../../flex-template-agent-assist/src/feature-library/agent-assist/flex-hooks/states/AgentAssistAdmin';

// NOTE: Not sure a great way to "set" the Flex redux store value
//       So the __mocks__/@twilio/flex-ui.js file will use this variable as value
//       And tests can use these functions to set value (will automatically get reset after each test)
let mockedReduxState: AppState = {
  flex: {
    worker: {
      activity: {
        available: false
      }
    }
  } as Flex.AppState,
  [reduxNamespace]: {} as AppState[typeof reduxNamespace],
};

export const getMockedReduxState = () => mockedReduxState;
export const resetReduxState = () => {
  mockedReduxState = {
    flex: {} as Flex.AppState,
    [reduxNamespace]: {} as AppState[typeof reduxNamespace],
  };
};
export const setFlexReduxState = (appState: Partial<Flex.AppState>) => {
  mergeWith(mockedReduxState, { flex: appState }, (_objValue, srcValue, key, obj) => {
    if (srcValue === undefined) {
      unset(obj, key);
    }
  });
};
export const setCustomReduxState = (appState: Partial<AppState[typeof reduxNamespace]>) => {
  mergeWith(mockedReduxState, { [reduxNamespace]: appState }, (_objValue, srcValue, key, obj) => {
    if (srcValue === undefined) {
      unset(obj, key);
    }
  });
};

const agentAssistReducers = combineReducers({
  agentAssist: agentAssistReducer,
  agentAssistAdmin: agentAssistAdminReducer
});

const mockFlexSlice = createSlice({
  name: 'flex',
  initialState: mockedReduxState.flex,
  reducers: {},
});

const rootReducer = combineReducers({
  flex: mockFlexSlice.reducer,
  [reduxNamespace]: agentAssistReducers,
});

export function setupStore(preloadedState?: Partial<AppState>) {
  return configureStore({
    reducer: rootReducer,
    preloadedState,
  });
}

export type AppStore = ReturnType<typeof setupStore>;
export type RootState = ReturnType<typeof rootReducer>;