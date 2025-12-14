import { useEffect } from "react";
import "./ToastHost.css";

export type ToastKind = "success" | "error" | "info";

export type Toast = {
  id: string;
  kind: ToastKind;
  title: string;
  message?: string;
  timeoutMs?: number;
};

interface ToastHostProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export function ToastHost({ toasts, onDismiss }: ToastHostProps) {
  useEffect(() => {
    const timers = toasts
      .filter((t) => (t.timeoutMs ?? 0) > 0)
      .map((t) => {
        const timeout = t.timeoutMs ?? 3500;
        return window.setTimeout(() => onDismiss(t.id), timeout);
      });

    return () => {
      timers.forEach((id) => window.clearTimeout(id));
    };
  }, [toasts, onDismiss]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-host" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          <div className="toast-top">
            <div className="toast-title">{t.title}</div>
            <button
              className="toast-close"
              onClick={() => onDismiss(t.id)}
              aria-label="Dismiss"
              type="button"
            >
              X
            </button>
          </div>
          {t.message && <div className="toast-message">{t.message}</div>}
        </div>
      ))}
    </div>
  );
}


