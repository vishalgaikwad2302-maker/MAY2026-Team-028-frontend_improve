import { createContext, useCallback, useContext, useRef, useState } from "react";
import { IconCheckCircle, IconAlertCircle, IconAlertTriangle } from "../components/Icons";

const ToastContext = createContext(null);

const ICONS = {
  success: IconCheckCircle,
  error: IconAlertCircle,
  info: IconAlertTriangle,
};

const DEFAULT_DURATION = 3500;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // notify("Complaint submitted", "success") — fire-and-forget, self-dismisses.
  // Any feature can call this instead of rolling its own inline banner/alert.
  const notify = useCallback(
    (message, type = "info", duration = DEFAULT_DURATION) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, message, type }]);
      if (duration) {
        setTimeout(() => dismiss(id), duration);
      }
      return id;
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ notify, dismiss }}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => {
          const Icon = ICONS[t.type] || ICONS.info;
          return (
            <div key={t.id} className={`toast toast-${t.type}`}>
              <Icon />
              <span>{t.message}</span>
              <button
                type="button"
                className="toast-close"
                aria-label="Dismiss"
                onClick={() => dismiss(t.id)}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

const noop = { notify: () => {}, dismiss: () => {} };

// Falls back to a no-op instead of null so a missed <ToastProvider> higher up
// (e.g. forgetting to update main.jsx) fails silently rather than crashing
// every screen that calls useToast().
export const useToast = () => useContext(ToastContext) || noop;