/**
 * Copyright 2024 Google LLC
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

//@ts-nocheck
import React, { useEffect } from 'react';
import * as Flex from '@twilio/flex-ui'; // eslint-disable-line node/no-unpublished-import
import { useScript } from '../../../lib/src/third_party/hooks/useScript';
import {
    ChatMessage,
    ChatBubble,
    ChatMessageMeta,
    ChatMessageMetaItem,
    useChatLogger,
    ChatLogger,
} from '@twilio-paste/chat-log';
import { Box } from '@twilio-paste/core/box';

type messageVariant = 'inbound' | 'outbound';

const transcriptFactory = (
    variant: messageVariant,
    message: string,
    metaLabel: string
) => {
    const time = new Date().toLocaleString('en-US', {
        hour: 'numeric',
        minute: 'numeric',
        hour12: true,
    });
    return {
        variant,
        content: (
            <ChatMessage variant={variant}>
                <ChatBubble>{message}</ChatBubble>
                <ChatMessageMeta aria-label={metaLabel + time}>
                    <ChatMessageMetaItem>{time}</ChatMessageMetaItem>
                </ChatMessageMeta>
            </ChatMessage>
        ),
    };
};

export const Transcript = (): JSX.Element | null => {
    const { chats, push } = useChatLogger();
    useEffect(()=>{
        // Create IE + others compatible event handler
        var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
        var eventer = window[eventMethod];
        var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";
        // Listen to message from child window
        function newMessageReceievedHandler(e){
            switch (e.data.type) {
                case 'new-message-received':
                    let userRole = e.data.detail.participantRole;
                    let message = e.data.detail.content;
                    let variant = userRole === 'END_USER' ? 'inbound' : 'outbound';
                    let metaLabel =
                        userRole === 'END_USER' ? 'said by customer at ' : 'said by agent at ';
                    push(transcriptFactory(variant, message, metaLabel));
                    break;
            }
        }

        eventer(messageEvent, newMessageReceievedHandler, false);

        return () => {
            const removeEventMethod = window.removeEventListener ? "removeEventListener" : "detachEvent";
            const removeEventer = window[removeEventMethod];
            const removeMessageEvent = removeEventMethod == "detachEvent" ? "onmessage" : "message";
            removeEventer(removeMessageEvent, newMessageReceievedHandler)
        }
    },[]);

    return <div style={{
        display: 'flex',
        flex: '1 1 auto',
        overflow: 'auto',
        padding: '1.25rem 1rem',
        lineHeight: '1rem',
        color: 'rgb(18, 28, 45)'}
}>
        <div style={{ width: '100%' }}><ChatLogger chats={chats} /></div></div>;
};

Transcript.displayName = 'Transcript';
