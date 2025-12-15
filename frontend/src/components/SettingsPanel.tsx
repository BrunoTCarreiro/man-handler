import { useState, useEffect } from "react";
import type { Device } from "../api/client";
import "./SettingsPanel.css";

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  devices: Device[];
  onEdit: (device: Device) => void;
  onReplace: (deviceId: string) => void;
  onDelete: (deviceId: string) => void;
  onView: (device: Device) => void;
  onRenameRoom: (oldRoom: string, newRoom: string) => void;
  onReset: () => void;
  isResetting: boolean;
}

export function SettingsPanel({
  isOpen,
  onClose,
  devices,
  onEdit,
  onReplace,
  onDelete,
  onView,
  onRenameRoom,
  onReset,
  isResetting,
}: SettingsPanelProps) {
  const [editingRoom, setEditingRoom] = useState<string | null>(null);
  const [newRoomName, setNewRoomName] = useState("");
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  // Group devices by room
  const devicesByRoom = devices.reduce((acc, device) => {
    const room = device.room || "Uncategorized";
    if (!acc[room]) acc[room] = [];
    acc[room].push(device);
    return acc;
  }, {} as Record<string, Device[]>);

  const sortedRooms = Object.keys(devicesByRoom).sort();

  const handleStartEditRoom = (room: string) => {
    setEditingRoom(room);
    setNewRoomName(room === "Uncategorized" ? "" : room);
  };

  const handleSaveRoomName = (oldRoom: string) => {
    const trimmedName = newRoomName.trim();
    if (trimmedName && trimmedName !== oldRoom) {
      onRenameRoom(oldRoom, trimmedName);
    }
    setEditingRoom(null);
    setNewRoomName("");
  };

  const handleCancelEditRoom = () => {
    setEditingRoom(null);
    setNewRoomName("");
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (_event: MouseEvent) => {
      if (openDropdown) {
        setOpenDropdown(null);
      }
    };

    if (openDropdown) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [openDropdown]);

  if (!isOpen) return null;

  return (
    <div className={`settings-panel ${isOpen ? "open" : ""}`}>
      <div className="settings-header">
        <h2>Settings</h2>
        <button className="close-settings-button" onClick={onClose} aria-label="Close">
          X
        </button>
      </div>

      <div className="settings-content">
        {/* Device Management Section */}
        <section className="settings-section">
          <h3>Device Management</h3>
          {devices.length === 0 ? (
            <p className="empty-state">No devices yet. Add a manual to get started.</p>
          ) : (
            <div className="device-list">
              {sortedRooms.map((room) => (
                <div key={room} className="room-group">
                  <div className="room-header">
                    {editingRoom === room ? (
                      <div className="room-edit-container">
                        <input
                          type="text"
                          value={newRoomName}
                          onChange={(e) => setNewRoomName(e.target.value)}
                          placeholder="Room name"
                          className="room-name-input"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveRoomName(room);
                            if (e.key === "Escape") handleCancelEditRoom();
                          }}
                        />
                        <button
                          className="room-action-button save"
                          onClick={() => handleSaveRoomName(room)}
                          title="Save"
                        >
                          Save
                        </button>
                        <button
                          className="room-action-button cancel"
                          onClick={handleCancelEditRoom}
                          title="Cancel"
                          aria-label="Cancel"
                        >
                          X
                        </button>
                      </div>
                    ) : (
                      <>
                        <span className="room-name">{room}</span>
                        <button
                          className="room-edit-button"
                          onClick={() => handleStartEditRoom(room)}
                          title="Rename room"
                        >
                          Edit
                        </button>
                      </>
                    )}
                  </div>
                  <div className="device-items">
                    {devicesByRoom[room].map((device) => (
                      <div key={device.id} className="device-item">
                        <div className="device-info">
                          <span className="device-name">{device.name}</span>
                          {device.model && (
                            <span className="device-model">({device.model})</span>
                          )}
                        </div>
                        <div className="device-actions">
                          <div className="actions-dropdown">
                            <button
                              className="actions-dropdown-button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setOpenDropdown(openDropdown === device.id ? null : device.id);
                              }}
                            >
                              Actions ▾
                            </button>
                            {openDropdown === device.id && (
                              <div className="actions-dropdown-menu" onClick={(e) => e.stopPropagation()}>
                                <button
                                  className="dropdown-item view"
                                  onClick={() => {
                                    setOpenDropdown(null);
                                    onView(device);
                                  }}
                                >
                                  View Manual
                                </button>
                                <button
                                  className="dropdown-item edit"
                                  onClick={() => {
                                    setOpenDropdown(null);
                                    onEdit(device);
                                  }}
                                >
                                  Edit Metadata
                                </button>
                                <button
                                  className="dropdown-item replace"
                                  onClick={() => {
                                    setOpenDropdown(null);
                                    onReplace(device.id);
                                  }}
                                >
                                  Replace Manual
                                </button>
                                <button
                                  className="dropdown-item delete"
                                  onClick={() => {
                                    setOpenDropdown(null);
                                    onDelete(device.id);
                                  }}
                                >
                                  Delete Device
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Database Reset Section */}
        <section className="settings-section">
          <h3>Database Reset</h3>
          <p className="section-description">
            Reset all data including devices, manuals, and vector database. This action cannot be undone.
          </p>
          <button
            className="reset-database-button"
            onClick={onReset}
            disabled={isResetting}
          >
            {isResetting ? "Resetting..." : "Reset Database"}
          </button>
        </section>
      </div>
    </div>
  );
}

