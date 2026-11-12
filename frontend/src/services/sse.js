// Thin wrapper around EventSource so the React layer only sees plain events.
export function connectEvents({ onEvent, onOpen, onError }) {
  const source = new EventSource("/events");

  source.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data));
    } catch {
      /* ignore malformed frames */
    }
  };
  source.onopen = () => onOpen?.();
  source.onerror = () => onError?.();

  return () => source.close();
}
