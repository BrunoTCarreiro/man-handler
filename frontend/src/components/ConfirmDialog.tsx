import "./ConfirmDialog.css";

type ConfirmVariant = "danger" | "default";

export type ConfirmDialogState = {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
};

interface ConfirmDialogProps extends ConfirmDialogState {
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-header">
          <h3>{title}</h3>
          <button className="confirm-close" onClick={onCancel} aria-label="Close" type="button">
            X
          </button>
        </div>
        <div className="confirm-body">
          <p>{message}</p>
        </div>
        <div className="confirm-footer">
          <button className="confirm-btn secondary" onClick={onCancel} type="button">
            {cancelText}
          </button>
          <button
            className={`confirm-btn primary ${variant === "danger" ? "danger" : ""}`}
            onClick={onConfirm}
            type="button"
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}


