import { useState, useEffect, useRef } from "react";
import type {
  ManualMetadata,
  ManualAnalyzeResponse,
  ManualProcessResponse,
  Device,
} from "../api/client";
import { analyzeManual, processManual, commitManual, getDevices, getProcessingStatus, cancelProcessing, deleteDevice } from "../api/client";
import { getErrorMessage } from "../api/errors";
import "./ManualOnboardingModal.css";

interface ManualOnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (devices: Device[]) => void;
  replacingDevice?: Device | null;
}

type WizardStep = "file-selection" | "processing" | "analysis" | "upload";

export function ManualOnboardingModal({
  isOpen,
  onClose,
  onSuccess,
  replacingDevice = null,
}: ManualOnboardingModalProps) {
  const emptyMetadata: ManualMetadata = {
    id: "",
    name: "",
    brand: "",
    model: "",
    room: "",
    category: "",
    manual_files: [],
  };

  const [currentStep, setCurrentStep] = useState<WizardStep>("file-selection");
  const [manualFile, setManualFile] = useState<File | null>(null);
  const [processResult, setProcessResult] = useState<ManualProcessResponse | null>(null);
  const [processLog, setProcessLog] = useState<string[]>([]);
  const [analyzeResult, setAnalyzeResult] = useState<ManualAnalyzeResponse | null>(null);
  const [manualMetadata, setManualMetadata] = useState<ManualMetadata>(emptyMetadata);
  const [analyzeStatus, setAnalyzeStatus] = useState<string | null>(null);
  const [commitStatus, setCommitStatus] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processAbort, setProcessAbort] = useState<AbortController | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);
  const [currentToken, setCurrentToken] = useState<string | null>(null);
  const processLogRef = useRef<HTMLDivElement | null>(null);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  // Auto-scroll to latest log entry
  useEffect(() => {
    if (processLogRef.current && processLog.length > 0) {
      processLogRef.current.scrollTop = processLogRef.current.scrollHeight;
    }
  }, [processLog]);

  const stopStatusPolling = () => {
    if (pollingIntervalRef.current !== null) {
      window.clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  const resetWizard = () => {
    setCurrentStep("file-selection");
    setManualFile(null);
    setProcessResult(null);
    setProcessLog([]);
    setAnalyzeResult(null);
    setManualMetadata(emptyMetadata);
    setAnalyzeStatus(null);
    setCommitStatus(null);
    setProcessAbort(null);
    setIsProcessing(false);
    setIsAnalyzing(false);
    setIsCommitting(false);
    setCurrentToken(null);
    stopStatusPolling();
  };

  const handleClose = () => {
    // If any work in progress, show confirmation
    if (isProcessing || isAnalyzing || isCommitting || manualFile || processResult) {
      setShowCancelConfirm(true);
    } else {
      resetWizard();
      onClose();
    }
  };

  const handleCancelWizard = async () => {
    // Cancel any ongoing processing
    if (currentToken && isProcessing) {
      try {
        await cancelProcessing(currentToken);
      } catch (err) {
        console.error("Failed to cancel processing:", err);
      }
    }
    
    stopStatusPolling();
    setShowCancelConfirm(false);
    resetWizard();
    onClose();
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopStatusPolling();
    };
  }, []);

  // (Auto-scroll handled above; keep single effect to avoid duplicate work.)

  // Auto-start analysis when entering step 3
  useEffect(() => {
    if (currentStep === "analysis" && processResult && !analyzeResult && !isAnalyzing) {
      handleAnalyze();
    }
  }, [currentStep]);

  // Reset wizard when modal opens (clean state)
  useEffect(() => {
    if (isOpen) {
      resetWizard();
      // If replacing a device, pre-fill its metadata
      if (replacingDevice) {
        setManualMetadata({
          id: replacingDevice.id,
          name: replacingDevice.name,
          brand: replacingDevice.brand || "",
          model: replacingDevice.model || "",
          room: replacingDevice.room || "",
          category: replacingDevice.category || "",
          manual_files: replacingDevice.manual_files || [],
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, replacingDevice]);

  if (!isOpen) return null;

  const handleFileSelect = (file: File | null) => {
    setManualFile(file);
    if (file) {
      setProcessResult(null);
      setProcessLog([]);
      setAnalyzeResult(null);
      setManualMetadata(emptyMetadata);
      setAnalyzeStatus(null);
      setCommitStatus(null);
    }
  };

  const handleProcess = async () => {
    if (!manualFile) return;
    
    // Stop any existing polling
    stopStatusPolling();
    
    setIsProcessing(true);
    setProcessLog(["[INFO] Uploading file..."]);
    setAnalyzeStatus(null);
    setCommitStatus(null);

    try {
      // Call process endpoint - it returns immediately with a token
      const response = await processManual(manualFile);
      const token = response.token;
      setCurrentToken(token);
      
      setProcessLog((prev) => [...prev, "[INFO] Processing started, polling for updates..."]);
      
      // Start polling for status
      await pollUntilComplete(token);
      
    } catch (err: unknown) {
      setProcessLog((prev) => [...prev, `[ERROR] Failed to start processing: ${getErrorMessage(err)}`]);
      setIsProcessing(false);
      setCurrentToken(null);
    }
  };

  const pollUntilComplete = async (token: string) => {
    return new Promise<void>((resolve, reject) => {
      const pollInterval = setInterval(async () => {
        try {
          const status = await getProcessingStatus(token);
          
          // Update logs
          if (status.logs && Array.isArray(status.logs)) {
            setProcessLog(status.logs);
          }
          
          // Check if done
          if (status.status === "complete") {
            clearInterval(pollInterval);
            
            // Extract results from status
            const result: ManualProcessResponse = {
              token: token,
              detected_language: status.detected_language || "unknown",
              translated: status.translated || false,
              output_filename: status.output_filename || "",
              pages: null,
              logs: status.logs,
            };
            
            setProcessResult(result);
            setProcessLog((prev) => [
              ...prev,
              `[OK] Processed: ${result.output_filename}`,
              `[OK] Language: ${result.detected_language}`,
              `[OK] Translated: ${result.translated ? "yes" : "no"}`,
            ]);
            
            setIsProcessing(false);
            setCurrentToken(null);
            resolve();
            
          } else if (status.status === "cancelled") {
            clearInterval(pollInterval);
            setProcessLog((prev) => [...prev, "[INFO] Processing cancelled successfully"]);
            setIsProcessing(false);
            setCurrentToken(null);
            resolve();
            
          } else if (status.status === "error") {
            clearInterval(pollInterval);
            setProcessLog((prev) => [...prev, "[ERROR] Processing failed"]);
            setIsProcessing(false);
            setCurrentToken(null);
            reject(new Error("Processing failed"));
          }
          
        } catch (err: unknown) {
          console.debug("Polling error:", err);
        }
      }, 3000);
      
      // Store interval ref for cancellation
      pollingIntervalRef.current = pollInterval;
    });
  };

  const handleAnalyze = async () => {
    const token = processResult?.token;
    if (!token) return;
    
    setIsAnalyzing(true);
    setAnalyzeStatus("Analyzing manual with AI...");
    setCommitStatus(null);

    try {
      const response = await analyzeManual(token);
      setAnalyzeResult(response);
      setManualMetadata(response.suggested_metadata);
      setAnalyzeStatus("[OK] Metadata populated. Review and edit if needed.");
    } catch (err: unknown) {
      setAnalyzeStatus(`[ERROR] Analyze failed: ${getErrorMessage(err)}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCommit = async () => {
    const result = processResult;
    if (!result) return;
    
    const manualFilename = result.output_filename || manualMetadata.manual_files[0] || "";

    if (!manualFilename) {
      setCommitStatus("[ERROR] No manual filename available to upload.");
      return;
    }

    if (!manualMetadata.id.trim() || !manualMetadata.name.trim()) {
      setCommitStatus("[ERROR] Device ID and name are required before uploading.");
      return;
    }

    setIsCommitting(true);
    
    try {
      // If replacing a device, delete the old one first
      if (replacingDevice) {
        setCommitStatus(`Deleting old manual for "${replacingDevice.name}"...`);
        await deleteDevice(replacingDevice.id);
        setCommitStatus("Old manual deleted. Uploading new manual...");
      } else {
        setCommitStatus("Uploading manual and updating index...");
      }

      const device = await commitManual({
        token: result.token,
        manual_filename: manualFilename,
        metadata: {
          ...manualMetadata,
          manual_files: [manualFilename],
        },
      });
      
      if (replacingDevice) {
        setCommitStatus(`[OK] Manual replaced successfully for "${device.name}"!`);
      } else {
        setCommitStatus(`[OK] Upload complete for device "${device.name}"!`);
      }
      
      // Refresh device list and close modal
      const updatedDevices = await getDevices();
      setTimeout(() => {
        resetWizard();
        onSuccess(updatedDevices);
        onClose();
      }, 1500);
    } catch (err: unknown) {
      setCommitStatus(`[ERROR] ${replacingDevice ? "Replace" : "Upload"} failed: ${getErrorMessage(err)}`);
    } finally {
      setIsCommitting(false);
    }
  };

  const canGoNext = () => {
    switch (currentStep) {
      case "file-selection":
        return manualFile !== null;
      case "processing":
        return processResult !== null && !isProcessing;
      case "analysis":
        return analyzeResult !== null && !isAnalyzing;
      case "upload":
        return false; // No next step
      default:
        return false;
    }
  };

  const canGoPrevious = () => {
    return currentStep !== "file-selection" && !isProcessing && !isAnalyzing && !isCommitting;
  };

  const handleNext = () => {
    if (currentStep === "file-selection" && manualFile) {
      setCurrentStep("processing");
    } else if (currentStep === "processing" && processResult) {
      setCurrentStep("analysis");
      // Auto-start analysis when entering step 3
      setTimeout(() => handleAnalyze(), 100);
    } else if (currentStep === "analysis" && analyzeResult) {
      setCurrentStep("upload");
    }
  };

  const handlePrevious = () => {
    if (currentStep === "processing") setCurrentStep("file-selection");
    else if (currentStep === "analysis") setCurrentStep("processing");
    else if (currentStep === "upload") setCurrentStep("analysis");
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case "file-selection":
        return (
          <div className="wizard-step">
            <h3>Step 1: Select Manual File</h3>
            <p className="step-description">
              {replacingDevice 
                ? `Choose a new PDF manual to replace the existing one for ${replacingDevice.name}.`
                : 'Choose a PDF manual to add to your knowledge base.'}
            </p>
            <div className="file-input-wrapper">
              <input
                type="file"
                accept=".pdf"
                id="manual-file-input"
                onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
                disabled={isProcessing}
              />
              <label htmlFor="manual-file-input" className="file-label">
                {manualFile ? (
                  <>
                    <span className="file-icon">[OK]</span>
                    <span className="file-name">{manualFile.name}</span>
                  </>
                ) : (
                  <>
                    <span className="file-icon">[...]</span>
                    <span>Choose PDF file</span>
                  </>
                )}
              </label>
            </div>
          </div>
        );

      case "processing":
        return (
          <div className="wizard-step">
            <h3>Step 2: Process Manual</h3>
            <p className="step-description">
              Extract English content. Non-English manuals will be auto-translated.
            </p>
            <div className="process-actions">
              <button
                type="button"
                onClick={handleProcess}
                disabled={!manualFile || isProcessing}
                className="action-button"
              >
                {isProcessing ? (
                  <>
                    <span className="spinner"></span>
                    Processing...
                  </>
                ) : (
                  "Start Processing"
                )}
              </button>
              {isProcessing && (
                <button
                  type="button"
                  onClick={async () => {
                    if (currentToken) {
                      try {
                        setProcessLog((prev) => [...prev, "[INFO] Cancellation requested..."]);
                        await cancelProcessing(currentToken);
                        // Keep polling - it will detect "cancelled" status and unlock UI
                      } catch (err: unknown) {
                        const errorMsg = getErrorMessage(err, "");
                        
                        // "Token not found" means processing already finished
                        if (errorMsg.includes("Token not found")) {
                          setProcessLog((prev) => [...prev, "[INFO] Processing already completed"]);
                          // Keep polling to get final status
                        } else {
                          // Real error - backend crashed or unavailable
                          setProcessLog((prev) => [...prev, `[ERROR] Cancel failed: ${errorMsg}`]);
                          // Stop polling and unlock UI on real errors
                          stopStatusPolling();
                          setIsProcessing(false);
                          setCurrentToken(null);
                        }
                      }
                    }
                  }}
                  className="action-button cancel-processing"
                >
                  Cancel
                </button>
              )}
            </div>
            <div ref={processLogRef} className="process-log">
              {processLog.length > 0 ? (
                processLog.map((line, idx) => (
                  <div
                    key={idx}
                    className={`log-line ${idx === processLog.length - 1 ? "log-line-latest" : ""}`}
                  >
                    {line}
                  </div>
                ))
              ) : (
                <div className="log-placeholder">Processing results will appear here...</div>
              )}
            </div>
          </div>
        );

      case "analysis":
        return (
          <div className="wizard-step">
            <h3>Step 3: AI Analysis</h3>
            <p className="step-description">
              Let AI extract device metadata from the manual.
            </p>
            <div className="metadata-grid">
              {(
                ["id", "name", "brand", "model", "room", "category"] as Array<
                  "id" | "name" | "brand" | "model" | "room" | "category"
                >
              ).map((field) => (
                <label key={field}>
                  {field.toUpperCase()}
                  <input
                    type="text"
                    value={manualMetadata[field] ?? ""}
                    onChange={(e) =>
                      setManualMetadata((prev) => ({
                        ...prev,
                        [field]: e.target.value,
                      }))
                    }
                  />
                </label>
              ))}
            </div>
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!processResult || isAnalyzing}
              className="action-button"
            >
              {isAnalyzing ? "Analyzing..." : "Analyze with AI"}
            </button>
            {analyzeStatus && <p className="status-message">{analyzeStatus}</p>}
          </div>
        );

      case "upload":
        return (
          <div className="wizard-step">
            <h3>Step 4: Upload to Knowledge Base</h3>
            <p className="step-description">
              Review the metadata and upload the manual to your knowledge base.
            </p>
            <div className="metadata-review">
              <div className="review-item">
                <span className="review-label">Device:</span>
                <span className="review-value">{manualMetadata.name || "—"}</span>
              </div>
              <div className="review-item">
                <span className="review-label">Brand:</span>
                <span className="review-value">{manualMetadata.brand || "—"}</span>
              </div>
              <div className="review-item">
                <span className="review-label">Model:</span>
                <span className="review-value">{manualMetadata.model || "—"}</span>
              </div>
              <div className="review-item">
                <span className="review-label">Room:</span>
                <span className="review-value">{manualMetadata.room || "—"}</span>
              </div>
              <div className="review-item">
                <span className="review-label">Category:</span>
                <span className="review-value">{manualMetadata.category || "—"}</span>
              </div>
            </div>
            {commitStatus && <p className="status-message">{commitStatus}</p>}
          </div>
        );
    }
  };

  const steps: WizardStep[] = ["file-selection", "processing", "analysis", "upload"];
  const currentStepIndex = steps.indexOf(currentStep);

  return (
    <>
      {/* Confirmation popup */}
      {showCancelConfirm && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="confirm-popup">
            <h3>Cancel Manual Upload?</h3>
            <p>All progress will be lost and any uploaded files will be deleted. This cannot be undone.</p>
            <div className="confirm-actions">
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="confirm-button secondary"
              >
                Keep Working
              </button>
              <button
                onClick={handleCancelWizard}
                className="confirm-button danger"
              >
                Yes, Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="modal-overlay" onClick={handleClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>{replacingDevice ? `Replace Manual - ${replacingDevice.name}` : 'Manual Onboarding'}</h2>
            <button className="close-button" onClick={handleClose} disabled={isProcessing || isAnalyzing || isCommitting} aria-label="Close">
              X
            </button>
          </div>

        <div className="wizard-progress">
          {steps.map((step, idx) => (
            <div
              key={step}
              className={`progress-step ${idx <= currentStepIndex ? "active" : ""} ${
                idx === currentStepIndex ? "current" : ""
              }`}
            >
              <div className="progress-circle">{idx + 1}</div>
              <div className="progress-label">
                {step === "file-selection" && "Select"}
                {step === "processing" && "Process"}
                {step === "analysis" && "Analyze"}
                {step === "upload" && "Upload"}
              </div>
            </div>
          ))}
        </div>

        <div className="wizard-content">{renderStepContent()}</div>

        <div className="modal-footer">
          <div className="footer-left">
            {currentStep !== "file-selection" && (
              <button
                onClick={handlePrevious}
                disabled={!canGoPrevious()}
                className="footer-button secondary"
              >
                ← Previous
              </button>
            )}
          </div>
          <div className="footer-right">
            <button
              onClick={handleClose}
              className="footer-button cancel-wizard"
            >
              Cancel
            </button>
            {currentStep !== "upload" ? (
              <button
                onClick={handleNext}
                disabled={!canGoNext()}
                className="footer-button primary"
              >
                Next →
              </button>
            ) : (
              <button
                onClick={handleCommit}
                disabled={isCommitting || !manualMetadata.id || !manualMetadata.name}
                className="footer-button primary"
              >
                {isCommitting 
                  ? (replacingDevice ? "Replacing..." : "Uploading...") 
                  : (replacingDevice ? "Replace Manual" : "Upload Manual")}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
    </>
  );
}

