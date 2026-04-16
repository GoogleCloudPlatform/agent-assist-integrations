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

import React from 'react';
import { useFlexSelector } from '@twilio/flex-ui';

import AppState from '../../../../types/manager/AppState';
import TabbedCRMTask from '../TabbedCRMTask';

export const TabbedCRMContainer = () => {
  const tasks = useFlexSelector((state: AppState) => state.flex.worker.tasks);

  // Only render new containers for tasks without a parent task
  const tasksFiltered = Array.from(tasks.values()).filter((task) => !task.attributes.parentTask);

  // Render for only the filtered tasks as well as an instance for when there is no task selected
  return (
    <>
      {tasksFiltered.map((task) => (
        <TabbedCRMTask thisTask={task} key={task.taskSid} />
      ))}
      <TabbedCRMTask thisTask={undefined} key="no-task" />
    </>
  );
};
