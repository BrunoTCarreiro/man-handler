import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import type { Device } from "../api/client";
import { getDeviceMarkdown, getDeviceFileUrl } from "../api/client";
import { getErrorMessage } from "../api/errors";
import "./ViewManualModal.css";

interface ViewManualModalProps {
  isOpen: boolean;
  device: Device | null;
  onClose: () => void;
}

export function ViewManualModal({ isOpen, device, onClose }: ViewManualModalProps) {
  const [content, setContent] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");

  useEffect(() => {
    if (!isOpen || !device) {
      setContent("");
      setError(null);
      return;
    }

    const loadMarkdown = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const text = await getDeviceMarkdown(device.id);
        setContent(text);
      } catch (err: unknown) {
        setError(getErrorMessage(err, "Failed to load manual content"));
        console.error("Error loading markdown:", err);
      } finally {
        setIsLoading(false);
      }
    };

    loadMarkdown();
  }, [isOpen, device]);

  if (!isOpen || !device) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="view-modal-overlay" onClick={handleOverlayClick}>
      <div className="view-modal-content">
        <div className="view-modal-header">
          <div>
            <h2>{device.name}</h2>
            {device.model && <p className="device-subtitle">{device.brand} {device.model}</p>}
          </div>
          <div className="header-actions">
            <button
              className="view-toggle-button"
              onClick={() => setViewMode(viewMode === "raw" ? "rendered" : "raw")}
              title={viewMode === "raw" ? "Switch to rendered view" : "Switch to raw view"}
            >
              {viewMode === "raw" ? "View Rendered" : "View Raw"}
            </button>
            <button className="close-button" onClick={onClose} aria-label="Close">
              X
            </button>
          </div>
        </div>
        
        <div className="view-modal-body">
          {isLoading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Loading manual...</p>
            </div>
          )}
          
          {error && (
            <div className="error-state">
              <p className="error-message">{error}</p>
              <button onClick={onClose}>Close</button>
            </div>
          )}
          
          {!isLoading && !error && content && (
            <div className={`markdown-content ${viewMode}`}>
              {viewMode === "raw" ? (
                <pre>{content}</pre>
              ) : (
                <ReactMarkdown
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    img: ({node, ...props}) => (
                      <img
                        {...props}
                        src={
                          device?.id && props.src?.startsWith("images/")
                            ? getDeviceFileUrl(device.id, props.src)
                            : props.src
                        }
                        alt={props.alt || 'Manual image'}
                      />
                    ),
                  }}
                  skipHtml={false}
                >
                  {content}
                </ReactMarkdown>
              )}
            </div>
          )}
          
          {!isLoading && !error && !content && (
            <div className="empty-state">
              <p>No markdown content found for this device.</p>
            </div>
          )}
        </div>
        
        <div className="view-modal-footer">
          <button className="footer-button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

