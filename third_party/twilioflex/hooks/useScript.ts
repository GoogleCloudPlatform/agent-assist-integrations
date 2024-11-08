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

/**
 * This script was taken from the @uidotdev/usehooks package and pasted
 * here because Flex only allows up to version 17.0.2 of react and some functions
 * require a min version of 18.
 */
import {useRef, useState, useEffect} from 'react';
interface UseScriptOptions {
  removeOnUnmount?: boolean;
}
type UserScriptReturnStatus = 'loading' | 'ready' | 'error' | 'unknown';
export function useScript(
  src: string,
  options: UseScriptOptions = {}
): UserScriptReturnStatus {
  const [status, setStatus] = useState<UserScriptReturnStatus>('loading');
  const optionsRef = useRef(options);
  useEffect(() => {
    let script = document.querySelector(
      `script[src="${src}"]`
    ) as HTMLScriptElement;
    const domStatus = script?.getAttribute(
      'data-status'
    ) as UserScriptReturnStatus;
    if (domStatus) {
      setStatus(domStatus);
      return;
    }
    if (script === null) {
      script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.setAttribute('data-status', 'loading');
      document.body.appendChild(script);
      const handleScriptLoad = () => {
        script.setAttribute('data-status', 'ready');
        setStatus('ready');
        removeEventListeners();
      };
      const handleScriptError = () => {
        script.setAttribute('data-status', 'error');
        setStatus('error');
        removeEventListeners();
      };
      const removeEventListeners = () => {
        script.removeEventListener('load', handleScriptLoad);
        script.removeEventListener('error', handleScriptError);
      };
      script.addEventListener('load', handleScriptLoad);
      script.addEventListener('error', handleScriptError);
      const removeOnUnmount = optionsRef.current.removeOnUnmount;
      return () => {
        if (removeOnUnmount === true) {
          script.remove();
          removeEventListeners();
        }
      };
    } else {
      setStatus('unknown');
    }
  }, [src]);
  return status;
}
