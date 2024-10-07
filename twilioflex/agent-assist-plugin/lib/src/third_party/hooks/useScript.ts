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
