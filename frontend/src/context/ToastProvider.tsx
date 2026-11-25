import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ToastContext as Context } from "./ToastContext";
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 5000);
    return () => clearTimeout(timer);
  }, [message]);
  return (
    <Context.Provider value={setMessage}>
      {children}
      {message && (
        <div role="status" className="toast">
          {message}
          <button
            aria-label="Dismiss notification"
            onClick={() => setMessage("")}
          >
            ×
          </button>
        </div>
      )}
    </Context.Provider>
  );
}
