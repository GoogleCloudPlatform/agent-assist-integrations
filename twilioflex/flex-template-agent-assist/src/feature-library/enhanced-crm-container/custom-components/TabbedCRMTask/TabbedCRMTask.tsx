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

import React, { useState, useEffect } from 'react';
import { Actions, ITask } from '@twilio/flex-ui';
import { Flex } from '@twilio-paste/core/flex';
import { Tabs, TabList, Tab, TabPanels, TabPanel } from '@twilio-paste/core/tabs';

export interface Props {
  thisTask?: ITask; // task assigned to component
  task?: ITask; // task in Context
}

interface LoadCRMContainerTabsPayload {
  task?: ITask;
  components: CRMComponent[];
}

interface CRMComponent {
  title: string;
  component: React.ComponentType;
  order?: number;
}

export const TabbedCRMTask = ({ thisTask, task }: Props) => {
  const [customComponents, setCustomComponents] = useState<CRMComponent[] | null>(null);

  // This allows short-lived tasks (e.g. callback tasks) to share/show
  // the same components as their parent task so CRM work can continue after
  // the short-lived task completes and disappears. This is done by rendering
  // components for every task, keeping the components alive, and toggling visibility.
  const display =
    task?.taskSid === thisTask?.taskSid || (thisTask && task?.attributes?.parentTask === thisTask?.sid)
      ? 'flex'
      : ('none' as any);

  const handleCustomComponent = (payload: LoadCRMContainerTabsPayload) => {
    // The action can be invoked multiple times at once. Ensure we handle the correct invocation.
    if (payload.task !== thisTask) {
      return;
    }

    // Remove listener so that this function is not executed again for this instance
    Actions.removeListener('afterLoadCRMContainerTabs', handleCustomComponent);

    if (payload.components) {
      setCustomComponents(payload.components.sort((a, b) => (a.order ?? 999) - (b.order ?? 999)));
    }
  };

  useEffect(() => {
    Actions.addListener('afterLoadCRMContainerTabs', handleCustomComponent);
    Actions.invokeAction('LoadCRMContainerTabs', {
      task: thisTask,
      components: [],
    });
  }, []);

  return (
    <div style={{ display, flex: '1 0 auto' }}>
      <Tabs baseId="enhanced-crm-tabs" element="CRM_TABS">
        <TabList aria-label="CRM tabs" element="CRM_TAB_LIST">
          {customComponents &&
            customComponents.map((component) => <Tab key={`crm-tab-${component.title}`}>{component.title}</Tab>)}
        </TabList>
        <TabPanels element="CRM_TAB_PANELS">
          {customComponents &&
            customComponents.map((component) => (
              <TabPanel element="CRM_TAB_PANEL" key={`crm-tab-panel-${component.title}`}>
                <Flex grow element="CRM_FLEX">
                  {component.component}
                </Flex>
              </TabPanel>
            ))}
        </TabPanels>
      </Tabs>
    </div>
  );
};
