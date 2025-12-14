import { useEffect, useMemo, useState } from "react";
import type { ChatResponse, Device, ManualMetadata, Source } from "./api/client";
import {
  getDevices,
  sendMessage,
  resetApp,
  deleteDevice,
  updateDevice,
  renameRoom,
} from "./api/client";
import { getErrorMessage } from "./api/errors";
import { ManualOnboardingModal } from "./components/ManualOnboardingModal";
import { EditDeviceModal } from "./components/EditDeviceModal";
import { SettingsPanel } from "./components/SettingsPanel";
import { ViewManualModal } from "./components/ViewManualModal";
import { ToastHost, type Toast } from "./components/ToastHost";
import { ConfirmDialog, type ConfirmDialogState } from "./components/ConfirmDialog";

type MessageRole = "user" | "assistant";

type Message = {
  role: MessageRole;
  content: string;
  sources?: Source[];
};

function randomSessionId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function App() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => randomSessionId());
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isSettingsPanelOpen, setIsSettingsPanelOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [deviceToEdit, setDeviceToEdit] = useState<Device | null>(null);
  const [deviceToReplace, setDeviceToReplace] = useState<Device | null>(null);
  const [deviceToView, setDeviceToView] = useState<Device | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    isOpen: false,
    title: "",
    message: "",
    confirmText: "Confirm",
    cancelText: "Cancel",
    variant: "default",
  });
  const [confirmResolver, setConfirmResolver] = useState<((value: boolean) => void) | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const d = await getDevices();
        setDevices(d);
        if (d.length > 0) {
          setSelectedDeviceId(d[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    })();
  }, []);

  async function refreshDevices() {
    const updated = await getDevices();
    setDevices(updated);
    return updated;
  }

  function pushToast(toast: Omit<Toast, "id">) {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((prev) => [...prev, { id, timeoutMs: 3500, ...toast }]);
  }

  function dismissToast(id: string) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  function confirmAsync(state: Omit<ConfirmDialogState, "isOpen">): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      setConfirmResolver(() => resolve);
      setConfirmDialog({ ...state, isOpen: true });
    });
  }

  const currentDevice = useMemo(
    () => devices.find((d) => d.id === selectedDeviceId) ?? null,
    [devices, selectedDeviceId]
  );

  async function handleSend() {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendMessage(
        text,
        selectedDeviceId,
        null,
        sessionId
      );
      const assistantMessage: Message = {
        role: "assistant",
        content: response.answer,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const assistantMessage: Message = {
        role: "assistant",
        content: `Error: ${getErrorMessage(err, "Failed to send message")}`,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleReset() {
    if (isResetting) return;
    const ok = await confirmAsync({
      title: "Reset database",
      message: "This will reset all data and reload the application. Continue?",
      confirmText: "Reset",
      cancelText: "Cancel",
      variant: "danger",
    });
    if (!ok) return;
    
    setIsResetting(true);
    try {
      await resetApp();
      setDevices([]);
      setMessages([]);
      window.location.reload();
    } catch (err: unknown) {
      pushToast({ kind: "error", title: "Reset failed", message: getErrorMessage(err) });
      setIsResetting(false);
    }
  }

  function handleModalSuccess(updatedDevices: Device[]) {
    setDevices(updatedDevices);
    if (updatedDevices.length > 0 && !selectedDeviceId) {
      setSelectedDeviceId(updatedDevices[0].id);
    }
  }

  function handleEditDevice(device: Device) {
    setDeviceToEdit(device);
    setIsEditModalOpen(true);
  }

  function handleViewDevice(device: Device) {
    setDeviceToView(device);
    setIsViewModalOpen(true);
  }

  async function handleDeleteDevice(deviceId: string) {
    const device = devices.find((d) => d.id === deviceId);
    if (!device) return;
    
    const ok = await confirmAsync({
      title: "Delete device",
      message: `Delete "${device.name}" and all its manuals? This cannot be undone.`,
      confirmText: "Delete",
      cancelText: "Cancel",
      variant: "danger",
    });
    if (!ok) return;
    
    try {
      await deleteDevice(deviceId);
      
      // Refresh devices list
      const updatedDevices = await refreshDevices();
      
      // If deleted device was selected, clear or select first
      if (selectedDeviceId === deviceId) {
        if (updatedDevices.length > 0) {
          setSelectedDeviceId(updatedDevices[0].id);
        } else {
          setSelectedDeviceId(null);
        }
      }
      
      pushToast({ kind: "success", title: "Device deleted", message: `"${device.name}" removed.` });
    } catch (err: unknown) {
      pushToast({ kind: "error", title: "Delete failed", message: getErrorMessage(err) });
    }
  }

  function handleReplaceDevice(deviceId: string) {
    const device = devices.find((d) => d.id === deviceId);
    if (!device) return;
    
    // Open the onboarding wizard with the device to replace
    setDeviceToReplace(device);
    setIsModalOpen(true);
  }

  async function handleRenameRoom(oldRoom: string, newRoom: string) {
    try {
      await renameRoom(oldRoom, newRoom);
      
      // Refresh devices list
      await refreshDevices();
      
      pushToast({ kind: "success", title: "Room renamed", message: `"${oldRoom}" → "${newRoom}"` });
    } catch (err: unknown) {
      pushToast({ kind: "error", title: "Rename failed", message: getErrorMessage(err) });
    }
  }

  async function handleUpdateDevice(deviceId: string, metadata: Partial<ManualMetadata>) {
    try {
      const updatedDevice = await updateDevice(deviceId, metadata);
      
      // Update devices list
      const updatedDevices = devices.map(d => 
        d.id === deviceId ? updatedDevice : d
      );
      setDevices(updatedDevices);
      
      pushToast({ kind: "success", title: "Device updated", message: `"${updatedDevice.name}" saved.` });
    } catch (err: unknown) {
      pushToast({ kind: "error", title: "Update failed", message: getErrorMessage(err) });
      throw err;
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="app-root">
      <ToastHost toasts={toasts} onDismiss={dismissToast} />
      <ConfirmDialog
        {...confirmDialog}
        onCancel={() => {
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
          confirmResolver?.(false);
          setConfirmResolver(null);
        }}
        onConfirm={() => {
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
          confirmResolver?.(true);
          setConfirmResolver(null);
        }}
      />
      <header className="top-bar">
        <div>
          <h1>Home Manual Assistant</h1>
          <p className="subtitle">
            Ask questions about your appliances, tools, and gadgets using local manuals.
          </p>
        </div>
        <div className="header-actions">
          <div className="action-buttons">
            <button
              className="add-manual-button"
              onClick={() => setIsModalOpen(true)}
            >
              Add Manual
            </button>
            <button
              className="settings-button"
              onClick={() => setIsSettingsPanelOpen(true)}
              title="Settings"
            >
              Settings
            </button>
          </div>
        </div>
      </header>

      <main className="layout">
        <section className="chat-panel">
          <div className="messages">
            {messages.length === 0 && (
              <div className="empty-state">
                <p>
                  Select a device and ask a question like
                  {" "}
                  <strong>"How do I clean the filter?"</strong>
                  {" "}
                  or
                  {" "}
                  <strong>"What does error code E23 mean?"</strong>.
                </p>
              </div>
            )}
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`message message-${m.role}`}
              >
                <div className="message-role">
                  {m.role === "user" ? "You" : "Assistant"}
                </div>
                <div className="message-content">{m.content}</div>
              </div>
            ))}
          </div>
          <div className="input-bar">
            <select
              id="device"
              className="device-dropdown"
              value={selectedDeviceId ?? ""}
              onChange={(e) =>
                setSelectedDeviceId(e.target.value || null)
              }
            >
              {devices.length === 0 ? (
                <option value="">No devices yet</option>
              ) : (
                <>
                  <option value="">All devices</option>
                  {(() => {
                    // Group devices by room
                    const devicesByRoom = devices.reduce((acc, device) => {
                      const room = device.room || "Uncategorized";
                      if (!acc[room]) acc[room] = [];
                      acc[room].push(device);
                      return acc;
                    }, {} as Record<string, Device[]>);

                    // Sort rooms alphabetically
                    const sortedRooms = Object.keys(devicesByRoom).sort();

                    return sortedRooms.map((room) => (
                      <optgroup key={room} label={room}>
                        {devicesByRoom[room].map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name} {d.model ? `(${d.model})` : ""}
                          </option>
                        ))}
                      </optgroup>
                    ));
                  })()}
                </>
              )}
            </select>
            <input
              type="text"
              placeholder={
                currentDevice
                  ? `Ask about ${currentDevice.name}...`
                  : "Ask a question about your devices..."
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button onClick={handleSend} disabled={isLoading || !input.trim()}>
              {isLoading ? "Thinking..." : "Send"}
            </button>
          </div>
        </section>
      </main>

      <ManualOnboardingModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setDeviceToReplace(null);
        }}
        onSuccess={handleModalSuccess}
        replacingDevice={deviceToReplace}
      />
      <EditDeviceModal
        isOpen={isEditModalOpen}
        device={deviceToEdit}
        onClose={() => {
          setIsEditModalOpen(false);
          setDeviceToEdit(null);
        }}
        onSave={handleUpdateDevice}
      />
      <SettingsPanel
        isOpen={isSettingsPanelOpen}
        onClose={() => setIsSettingsPanelOpen(false)}
        devices={devices}
        onEdit={handleEditDevice}
        onView={handleViewDevice}
        onReplace={handleReplaceDevice}
        onDelete={handleDeleteDevice}
        onRenameRoom={handleRenameRoom}
        onReset={handleReset}
        isResetting={isResetting}
      />
      <ViewManualModal
        isOpen={isViewModalOpen}
        device={deviceToView}
        onClose={() => {
          setIsViewModalOpen(false);
          setDeviceToView(null);
        }}
      />
    </div>
  );
}


