import { useEffect, useRef, useState } from "react";
import { checkOllamaConnection, getConfig, restartOllama, type ConfigData } from "../api/client";
import "./StatusHeader.css";

type OllamaStatus = {
  status: string;
  message: string;
  version?: string;
};

// Global state for status checks - can be triggered by any component
let globalStatusCheck: (() => Promise<void>) | null = null;

/**
 * Manually trigger a status check from anywhere in the app.
 * Call this before Ollama-dependent actions (chat, processing, etc.)
 */
export async function refreshOllamaStatus() {
  if (globalStatusCheck) {
    await globalStatusCheck();
  }
}

export function StatusHeader() {
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRestarting, setIsRestarting] = useState(false);
  const lastCheckRef = useRef<number>(Date.now());

  async function loadStatus() {
    try {
      const [ollamaRes, configRes] = await Promise.all([
        checkOllamaConnection(),
        getConfig(),
      ]);
      setOllamaStatus(ollamaRes);
      setConfig(configRes);
      lastCheckRef.current = Date.now();
    } catch (err) {
      console.error("Failed to load status:", err);
      setOllamaStatus({ status: "error", message: "Connection failed" });
      lastCheckRef.current = Date.now();
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRestartOllama() {
    if (isRestarting) return;
    
    setIsRestarting(true);
    try {
      const result = await restartOllama();
      console.log(result.message);
      
      // Wait 3 seconds before checking status
      setTimeout(() => {
        loadStatus();
        setIsRestarting(false);
      }, 3000);
    } catch (err) {
      console.error("Failed to restart Ollama:", err);
      setIsRestarting(false);
    }
  }

  useEffect(() => {
    // Register global check function
    globalStatusCheck = loadStatus;

    // Initial load
    loadStatus();

    // Polling interval: check every 15 seconds
    const interval = setInterval(loadStatus, 15000);

    // Check when tab becomes visible (user returns)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Only check if more than 10 seconds since last check
        const timeSinceLastCheck = Date.now() - lastCheckRef.current;
        if (timeSinceLastCheck > 10000) {
          loadStatus();
        }
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      globalStatusCheck = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array - only run once on mount

  if (isLoading) {
    return (
      <div className="status-header">
        <div className="status-loading">Loading status...</div>
      </div>
    );
  }

  const isConnected = ollamaStatus?.status === "connected";
  const OCR_MODEL = "deepseek-ocr:3b"; // Hardcoded in backend

  return (
    <div className="status-header">
      {/* Ollama Connection Status */}
      <div className="status-item">
        <div className="status-label">Ollama</div>
        <div 
          className={`status-value ${isConnected ? "status-connected" : "status-disconnected"} ${!isConnected ? "status-clickable" : ""}`}
          onClick={!isConnected ? handleRestartOllama : undefined}
          title={!isConnected ? "Click to restart Ollama" : undefined}
        >
          <span className="status-indicator"></span>
          {isRestarting ? "Restarting..." : (isConnected ? "Connected" : "Disconnected")}
          {ollamaStatus?.version && <span className="status-version">v{ollamaStatus.version}</span>}
        </div>
      </div>

      {/* Models */}
      {config && (
        <>
          <div className="status-separator"></div>
          
          <div className="status-item">
            <div className="status-label">LLM</div>
            <div className="status-value status-model">{config.ollama_models.llm}</div>
          </div>

          <div className="status-item">
            <div className="status-label">Embedding</div>
            <div className="status-value status-model">{config.ollama_models.embedding}</div>
          </div>

          <div className="status-item">
            <div className="status-label">Translation</div>
            <div className="status-value status-model">{config.ollama_models.translation}</div>
          </div>

          <div className="status-item">
            <div className="status-label">OCR</div>
            <div className="status-value status-model">{OCR_MODEL}</div>
          </div>
        </>
      )}
    </div>
  );
}

