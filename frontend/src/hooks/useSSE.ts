import { useEffect, useRef } from "react";

export function useSSE(onRefresh: () => void) {
  const callbackRef = useRef(onRefresh);
  callbackRef.current = onRefresh;

  useEffect(() => {
    const evtSource = new EventSource("/api/events");

    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "index_refreshed") {
          callbackRef.current();
        }
      } catch {
        // ignore
      }
    };

    evtSource.onerror = () => {
      evtSource.close();
      setTimeout(() => {
        // Reconnect handled by re-mount or manual trigger
      }, 5000);
    };

    return () => evtSource.close();
  }, []);
}
