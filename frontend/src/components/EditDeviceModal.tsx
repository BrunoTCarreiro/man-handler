import { useState, useEffect } from "react";
import type { Device } from "../api/client";
import "./EditDeviceModal.css";

interface EditDeviceModalProps {
  isOpen: boolean;
  device: Device | null;
  onClose: () => void;
  onSave: (deviceId: string, metadata: {
    name: string;
    brand?: string;
    model?: string;
    room?: string;
    category?: string;
  }) => Promise<void>;
}

export function EditDeviceModal({ isOpen, device, onClose, onSave }: EditDeviceModalProps) {
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [room, setRoom] = useState("");
  const [category, setCategory] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (device) {
      setName(device.name || "");
      setBrand(device.brand || "");
      setModel(device.model || "");
      setRoom(device.room || "");
      setCategory(device.category || "");
    }
  }, [device]);

  const handleSave = async () => {
    if (!device || !name.trim()) return;

    setIsSaving(true);
    try {
      await onSave(device.id, {
        name: name.trim(),
        brand: brand.trim() || undefined,
        model: model.trim() || undefined,
        room: room.trim() || undefined,
        category: category.trim() || undefined,
      });
      onClose();
    } catch (err) {
      console.error("Failed to save device:", err);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen || !device) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="edit-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="edit-modal-header">
          <h2>Edit Device</h2>
          <button className="close-button" onClick={onClose} aria-label="Close">
            X
          </button>
        </div>

        <div className="edit-modal-body">
          <div className="edit-field">
            <label htmlFor="edit-name">Name *</label>
            <input
              id="edit-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Device name"
            />
          </div>

          <div className="edit-field">
            <label htmlFor="edit-brand">Brand</label>
            <input
              id="edit-brand"
              type="text"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="Manufacturer"
            />
          </div>

          <div className="edit-field">
            <label htmlFor="edit-model">Model</label>
            <input
              id="edit-model"
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Model number"
            />
          </div>

          <div className="edit-field">
            <label htmlFor="edit-room">Room</label>
            <input
              id="edit-room"
              type="text"
              value={room}
              onChange={(e) => setRoom(e.target.value)}
              placeholder="e.g., kitchen, bedroom"
            />
          </div>

          <div className="edit-field">
            <label htmlFor="edit-category">Category</label>
            <input
              id="edit-category"
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g., appliance, furniture"
            />
          </div>
        </div>

        <div className="edit-modal-footer">
          <button
            className="edit-button secondary"
            onClick={onClose}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            className="edit-button primary"
            onClick={handleSave}
            disabled={isSaving || !name.trim()}
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

