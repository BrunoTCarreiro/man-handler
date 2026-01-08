import { ModelConfigSection } from "./ModelConfigSection";
import "./SettingsPanel.css";

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onReset: () => void;
  isResetting: boolean;
}

export function SettingsPanel({
  isOpen,
  onClose,
  onReset,
  isResetting,
}: SettingsPanelProps) {

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
        {/* Model Configuration Section */}
        <ModelConfigSection />

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

