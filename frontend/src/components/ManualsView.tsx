import { useState, useEffect } from "react";
import type { Device } from "../api/client";
import "./ManualsView.css";

interface ManualsViewProps {
  devices: Device[];
  onEdit: (device: Device) => void;
  onReplace: (deviceId: string) => void;
  onDelete: (deviceId: string) => void;
  onView: (device: Device) => void;
  onRenameRoom: (oldRoom: string, newRoom: string) => void;
  onAddManual: () => void;
}

export function ManualsView({
  devices,
  onEdit,
  onReplace,
  onDelete,
  onView,
  onRenameRoom,
  onAddManual,
}: ManualsViewProps) {
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

  return (
    <div className="manuals-view">
      <div className="manuals-header">
        <div>
          <h2>Manuals</h2>
          <p className="manuals-subtitle">Manage your device manuals and settings</p>
        </div>
        <button className="add-manual-button" onClick={onAddManual}>
          Add Manual
        </button>
      </div>

      <div className="manuals-content">
        {/* Device Management Section */}
        <section className="manuals-section">
          <h3>Device Management</h3>
          {devices.length === 0 ? (
            <div className="empty-state">
              <p>No devices yet. Add a manual to get started.</p>
            </div>
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
      </div>
    </div>
  );
}



