/**
 * MIT License

 * Copyright (c) 2023 ui.dev

 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:

 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.

 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
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
