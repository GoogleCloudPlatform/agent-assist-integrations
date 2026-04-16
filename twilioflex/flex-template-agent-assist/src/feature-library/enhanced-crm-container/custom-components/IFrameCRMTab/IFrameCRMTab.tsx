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

import React, { useState, useRef } from 'react';
import { IconButton, ITask } from '@twilio/flex-ui';

import { IFrameRefreshButtonStyledDiv } from './IFrameCRMTab.Styles';
import { getUrl, displayUrlWhenNoTasks } from '../../config';
import { replaceStringAttributes } from '../../../../utils/helpers';

export interface Props {
  task: ITask;
}

export const IFrameCRMTab = ({ task }: Props) => {
  const iFrameRef = useRef<HTMLIFrameElement>(null);
  const [iFrameKey, setIframeKey] = useState(0 as number);

  const handleOnClick = () => {
    setIframeKey(Math.floor(Math.random() * (Number.MAX_SAFE_INTEGER + 1)));
  };

  const url = replaceStringAttributes(task ? getUrl() : displayUrlWhenNoTasks(), task);

  return (
    <>
      <IFrameRefreshButtonStyledDiv onClick={handleOnClick}>
        <IconButton variant="primary" icon="Loading" />
      </IFrameRefreshButtonStyledDiv>
      <iframe key={iFrameKey} src={url} ref={iFrameRef} />
    </>
  );
};
