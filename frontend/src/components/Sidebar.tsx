import { ChatIcon, BookIcon, SettingsIcon } from "./icons";
import "./Sidebar.css";

interface SidebarProps {
  isExpanded: boolean;
  activeSection: "ask" | "manuals" | "settings";
  onToggle: () => void;
  onSectionChange: (section: "ask" | "manuals" | "settings") => void;
  onClose?: () => void;
}

export function Sidebar({ isExpanded, activeSection, onToggle, onSectionChange, onClose }: SidebarProps) {
  return (
    <>
      {isExpanded && (
        <div className="sidebar-backdrop" onClick={onClose || onToggle} />
      )}
      <aside className={`sidebar ${isExpanded ? "expanded" : "collapsed"}`}>
        <div className="sidebar-header">
          <div className="logo-placeholder">
            {isExpanded ? "MH" : "M"}
          </div>
          {isExpanded && <h1 className="sidebar-title">ManHandler</h1>}
          {isExpanded && (
            <button
              className="sidebar-toggle"
              onClick={onToggle}
              aria-label="Collapse sidebar"
            >
              ◀
            </button>
          )}
        </div>

      <nav className="sidebar-nav">
        <button
          className={`nav-item ${activeSection === "ask" ? "active" : ""}`}
          onClick={() => onSectionChange("ask")}
          title={isExpanded ? undefined : "Ask"}
        >
          <span className="nav-icon">
            <ChatIcon size={20} />
          </span>
          {isExpanded && <span className="nav-label">Ask</span>}
        </button>
        <button
          className={`nav-item ${activeSection === "manuals" ? "active" : ""}`}
          onClick={() => onSectionChange("manuals")}
          title={isExpanded ? undefined : "Manuals"}
        >
          <span className="nav-icon">
            <BookIcon size={20} />
          </span>
          {isExpanded && <span className="nav-label">Manuals</span>}
        </button>
        <button
          className={`nav-item ${activeSection === "settings" ? "active" : ""}`}
          onClick={() => onSectionChange("settings")}
          title={isExpanded ? undefined : "Settings"}
        >
          <span className="nav-icon">
            <SettingsIcon size={20} />
          </span>
          {isExpanded && <span className="nav-label">Settings</span>}
        </button>
      </nav>
      
      {!isExpanded && (
        <div 
          className="sidebar-resize-handle"
          onClick={onToggle}
          aria-label="Expand sidebar"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onToggle();
            }
          }}
        />
      )}
    </aside>
    </>
  );
}

