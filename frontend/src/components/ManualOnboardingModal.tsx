import { useState, useEffect, useRef, useCallback } from "react";
import type {
  ManualMetadata,
  ManualAnalyzeResponse,
  Device,
} from "../api/client";
import {
  analyzeManual,
  processManual,
  getDevices,
  getProcessingStatus,
  cancelProcessing,
  deleteDevice,
  commitManualsBatch,
  getManualPdfUrl,
  type BatchCommitItem,
} from "../api/client";
import { getErrorMessage } from "../api/errors";
import { refreshOllamaStatus } from "./StatusHeader";
import { PdfViewer } from "./PdfViewer";
import "./ManualOnboardingModal.css";

interface ManualOnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (devices: Device[]) => void;
  replacingDevice?: Device | null;
}

type WizardStep = "file-selection" | "processing" | "verification" | "upload";

type BatchManualStatus = "pending" | "processing" | "complete" | "error" | "cancelled";

interface BatchManualItem {
  id: string;
  file: File;
  status: BatchManualStatus;
  token: string | null;
  logs: string[];
  outputFilename: string | null;
  detectedLanguage: string | null;
  translated: boolean;
  metadata: ManualMetadata | null;
  analyzeStatus: "pending" | "analyzing" | "complete" | "error";
  analyzeError: string | null;
  isVerified: boolean;
}

const emptyMetadata: ManualMetadata = {
  id: "",
  name: "",
  brand: "",
  model: "",
  room: "",
  category: "",
  manual_files: [],
};

export function ManualOnboardingModal({
  isOpen,
  onClose,
  onSuccess,
  replacingDevice = null,
}: ManualOnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>("file-selection");
  const [batchItems, setBatchItems] = useState<BatchManualItem[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [commitStatus, setCommitStatus] = useState<string | null>(null);
  const [isCommitting, setIsCommitting] = useState(false);
  const [isUploadComplete, setIsUploadComplete] = useState(false);
  const pollingIntervalsRef = useRef<Map<string, number>>(new Map());
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [isEnglishManual, setIsEnglishManual] = useState(false);
  const processLogRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Get the currently selected item
  const selectedItem = batchItems.find((item) => item.id === selectedItemId) || null;

  // Check if all items are processed
  const allProcessed = batchItems.length > 0 && batchItems.every(
    (item) => item.status === "complete" || item.status === "error" || item.status === "cancelled"
  );

  // Check if any item is currently processing
  const anyProcessing = batchItems.some((item) => item.status === "processing");

  // Check if all items are verified
  const allVerified = batchItems.length > 0 && batchItems.every(
    (item) => item.isVerified || item.status === "error" || item.status === "cancelled"
  );

  // Get items ready for upload (verified and complete)
  const itemsReadyForUpload = batchItems.filter(
    (item) => item.isVerified && item.status === "complete" && item.metadata
  );

  // Auto-scroll processing logs
  useEffect(() => {
    if (processLogRef.current && selectedItem?.logs.length) {
      processLogRef.current.scrollTop = processLogRef.current.scrollHeight;
    }
  }, [selectedItem?.logs]);

  const stopAllPolling = useCallback(() => {
    pollingIntervalsRef.current.forEach((intervalId) => {
      window.clearInterval(intervalId);
    });
    pollingIntervalsRef.current.clear();
  }, []);

  const stopPollingForItem = useCallback((itemId: string) => {
    const intervalId = pollingIntervalsRef.current.get(itemId);
    if (intervalId !== undefined) {
      window.clearInterval(intervalId);
      pollingIntervalsRef.current.delete(itemId);
    }
  }, []);

  const resetWizard = useCallback(() => {
    setCurrentStep("file-selection");
    setBatchItems([]);
    setSelectedItemId(null);
    setCommitStatus(null);
    setIsCommitting(false);
    setIsUploadComplete(false);
    setIsEnglishManual(false);
    stopAllPolling();
  }, [stopAllPolling]);

  const handleClose = () => {
    if (anyProcessing || batchItems.length > 0 || isCommitting) {
      setShowCancelConfirm(true);
    } else {
      resetWizard();
      onClose();
    }
  };

  const handleCancelWizard = async () => {
    // Cancel any ongoing processing
    for (const item of batchItems) {
      if (item.token && item.status === "processing") {
        try {
          await cancelProcessing(item.token);
        } catch (err) {
          console.error("Failed to cancel processing:", err);
        }
      }
    }

    stopAllPolling();
    setShowCancelConfirm(false);
    resetWizard();
    onClose();
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopAllPolling();
    };
  }, [stopAllPolling]);

  // Reset wizard when modal opens
  useEffect(() => {
    if (isOpen) {
      resetWizard();
      // If replacing a device, we'll handle it differently (single file mode)
      if (replacingDevice) {
        // Pre-fill metadata for replace mode
      }
    }
  }, [isOpen, replacingDevice, resetWizard]);

  if (!isOpen) return null;

  const handleFilesSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const newItems: BatchManualItem[] = Array.from(files).map((file, index) => ({
      id: `${Date.now()}-${index}-${file.name}`,
      file,
      status: "pending",
      token: null,
      logs: [],
      outputFilename: null,
      detectedLanguage: null,
      translated: false,
      metadata: null,
      analyzeStatus: "pending",
      analyzeError: null,
      isVerified: false,
    }));

    setBatchItems((prev) => [...prev, ...newItems]);
  };

  const handleRemoveFile = (itemId: string) => {
    stopPollingForItem(itemId);
    setBatchItems((prev) => prev.filter((item) => item.id !== itemId));
  };

  const updateBatchItem = (itemId: string, updates: Partial<BatchManualItem>) => {
    setBatchItems((prev) =>
      prev.map((item) => (item.id === itemId ? { ...item, ...updates } : item))
    );
  };

  const processNextItem = async () => {
    // Find the next pending item
    const nextItem = batchItems.find((item) => item.status === "pending");
    if (!nextItem) return;

    await processItem(nextItem.id);
  };

  const processItem = async (itemId: string) => {
    const item = batchItems.find((i) => i.id === itemId);
    if (!item) return;

    updateBatchItem(itemId, {
      status: "processing",
      logs: ["[INFO] Uploading file..."],
    });

    try {
      await refreshOllamaStatus();

      const response = await processManual(item.file, isEnglishManual);
      const token = response.token;

      updateBatchItem(itemId, {
        token,
        logs: ["[INFO] Processing started, polling for updates..."],
      });

      // Start polling for this item
      pollForItem(itemId, token);
    } catch (err: unknown) {
      updateBatchItem(itemId, {
        status: "error",
        logs: [...item.logs, `[ERROR] Failed to start processing: ${getErrorMessage(err)}`],
      });
      // Process next item
      setTimeout(processNextItem, 100);
    }
  };

  const pollForItem = (itemId: string, token: string) => {
    const pollInterval = window.setInterval(async () => {
      try {
        const status = await getProcessingStatus(token);

        // Update logs
        if (status.logs && Array.isArray(status.logs)) {
          updateBatchItem(itemId, { logs: status.logs });
        }

        if (status.status === "complete") {
          stopPollingForItem(itemId);
          updateBatchItem(itemId, {
            status: "complete",
            outputFilename: status.output_filename || "",
            detectedLanguage: status.detected_language || "unknown",
            translated: status.translated || false,
            logs: [
              ...(status.logs || []),
              `[OK] Processed: ${status.output_filename}`,
              `[OK] Language: ${status.detected_language}`,
              `[OK] Translated: ${status.translated ? "yes" : "no"}`,
            ],
          });
          // Process next item
          setTimeout(processNextItem, 100);
        } else if (status.status === "cancelled") {
          stopPollingForItem(itemId);
          updateBatchItem(itemId, {
            status: "cancelled",
            logs: [...(status.logs || []), "[INFO] Processing cancelled"],
          });
          // Process next item
          setTimeout(processNextItem, 100);
        } else if (status.status === "error") {
          stopPollingForItem(itemId);
          updateBatchItem(itemId, {
            status: "error",
            logs: [...(status.logs || []), "[ERROR] Processing failed"],
          });
          // Process next item
          setTimeout(processNextItem, 100);
        }
      } catch (err) {
        console.debug("Polling error:", err);
      }
    }, 3000);

    pollingIntervalsRef.current.set(itemId, pollInterval);
  };

  const handleStartProcessing = async () => {
    if (batchItems.length === 0) return;

    await refreshOllamaStatus();

    // Start processing the first item
    processNextItem();
  };

  const handleAnalyzeItem = async (itemId: string) => {
    const item = batchItems.find((i) => i.id === itemId);
    if (!item || !item.token) return;

    updateBatchItem(itemId, {
      analyzeStatus: "analyzing",
      analyzeError: null,
    });

    try {
      const response: ManualAnalyzeResponse = await analyzeManual(item.token);
      updateBatchItem(itemId, {
        metadata: response.suggested_metadata,
        analyzeStatus: "complete",
      });
    } catch (err: unknown) {
      updateBatchItem(itemId, {
        analyzeStatus: "error",
        analyzeError: getErrorMessage(err),
        metadata: emptyMetadata,
      });
    }
  };

  const handleUpdateMetadata = (itemId: string, field: keyof ManualMetadata, value: string) => {
    setBatchItems((prev) =>
      prev.map((item) => {
        if (item.id !== itemId || !item.metadata) return item;
        return {
          ...item,
          metadata: {
            ...item.metadata,
            [field]: value,
          },
        };
      })
    );
  };

  const handleVerifyItem = (itemId: string) => {
    const item = batchItems.find((i) => i.id === itemId);
    if (!item || !item.metadata || !item.metadata.id || !item.metadata.name) return;

    updateBatchItem(itemId, { isVerified: true });

    // Auto-select next unverified item
    const nextUnverified = batchItems.find(
      (i) => i.id !== itemId && !i.isVerified && i.status === "complete"
    );
    if (nextUnverified) {
      setSelectedItemId(nextUnverified.id);
      // Auto-analyze if not already done
      if (nextUnverified.analyzeStatus === "pending") {
        handleAnalyzeItem(nextUnverified.id);
      }
    }
  };

  const handleCommitBatch = async () => {
    if (itemsReadyForUpload.length === 0) return;

    setIsCommitting(true);
    setCommitStatus("Preparing to upload manuals...");

    try {
      // If replacing a device, delete the old one first
      if (replacingDevice && itemsReadyForUpload.length === 1) {
        setCommitStatus(`Deleting old manual for "${replacingDevice.name}"...`);
        await deleteDevice(replacingDevice.id);
        setCommitStatus("Old manual deleted. Uploading new manual...");
      }

      const commitItems: BatchCommitItem[] = itemsReadyForUpload.map((item) => ({
        token: item.token!,
        manual_filename: item.outputFilename!,
        metadata: {
          ...item.metadata!,
          manual_files: [item.outputFilename!],
        },
      }));

      setCommitStatus(`Uploading ${commitItems.length} manual(s)...`);

      const result = await commitManualsBatch(commitItems);

      if (result.errors.length > 0) {
        setCommitStatus(
          `[OK] Uploaded ${result.devices.length} manual(s). ${result.errors.length} error(s) occurred.`
        );
      } else {
        setCommitStatus(`[OK] Successfully uploaded ${result.devices.length} manual(s)!`);
      }

      setIsUploadComplete(true);

      // Refresh device list and close modal
      const updatedDevices = await getDevices();
      setTimeout(() => {
        resetWizard();
        onSuccess(updatedDevices);
        onClose();
      }, 1500);
    } catch (err: unknown) {
      setCommitStatus(`[ERROR] Upload failed: ${getErrorMessage(err)}`);
    } finally {
      setIsCommitting(false);
    }
  };

  // Auto-analyze when selecting an item in verification step
  useEffect(() => {
    if (
      currentStep === "verification" &&
      selectedItem &&
      selectedItem.status === "complete" &&
      selectedItem.analyzeStatus === "pending"
    ) {
      handleAnalyzeItem(selectedItem.id);
    }
  }, [currentStep, selectedItemId]);

  // Auto-select first complete item when entering verification step
  useEffect(() => {
    if (currentStep === "verification" && !selectedItemId) {
      const firstComplete = batchItems.find((item) => item.status === "complete");
      if (firstComplete) {
        setSelectedItemId(firstComplete.id);
      }
    }
  }, [currentStep, selectedItemId, batchItems]);

  const canGoNext = () => {
    switch (currentStep) {
      case "file-selection":
        return batchItems.length > 0;
      case "processing":
        return allProcessed && batchItems.some((item) => item.status === "complete");
      case "verification":
        return allVerified && itemsReadyForUpload.length > 0;
      case "upload":
        return false;
      default:
        return false;
    }
  };

  const canGoPrevious = () => {
    return (
      currentStep !== "file-selection" &&
      !anyProcessing &&
      !isCommitting &&
      !isUploadComplete
    );
  };

  const handleNext = () => {
    if (currentStep === "file-selection" && batchItems.length > 0) {
      setCurrentStep("processing");
    } else if (currentStep === "processing" && allProcessed) {
      setCurrentStep("verification");
    } else if (currentStep === "verification" && allVerified) {
      setCurrentStep("upload");
    }
  };

  const handlePrevious = () => {
    if (currentStep === "processing") setCurrentStep("file-selection");
    else if (currentStep === "verification") setCurrentStep("processing");
    else if (currentStep === "upload") setCurrentStep("verification");
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case "file-selection":
        return (
          <div className="wizard-step">
            <h3>Step 1: Select Manual Files</h3>
            <p className="step-description">
              {replacingDevice
                ? `Choose a new PDF manual to replace the existing one for ${replacingDevice.name}.`
                : "Choose one or more PDF manuals to add to your knowledge base."}
            </p>
            <div className="file-input-wrapper">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                multiple={!replacingDevice}
                id="manual-file-input"
                onChange={(e) => handleFilesSelect(e.target.files)}
              />
              <label htmlFor="manual-file-input" className="file-label">
                <span className="file-icon">[+]</span>
                <span>
                  {replacingDevice ? "Choose PDF file" : "Choose PDF file(s)"}
                </span>
              </label>
            </div>

            {batchItems.length > 0 && (
              <div className="selected-files-list">
                <h4>Selected Files ({batchItems.length})</h4>
                <ul>
                  {batchItems.map((item) => (
                    <li key={item.id} className="selected-file-item">
                      <span className="file-name">{item.file.name}</span>
                      <button
                        type="button"
                        className="remove-file-btn"
                        onClick={() => handleRemoveFile(item.id)}
                        aria-label={`Remove ${item.file.name}`}
                      >
                        X
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );

      case "processing":
        return (
          <div className="wizard-step">
            <h3>Step 2: Process Manuals</h3>
            <p className="step-description">
              Extract English content. Non-English manuals will be auto-translated.
            </p>
            <div className="process-options">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={isEnglishManual}
                  onChange={(e) => setIsEnglishManual(e.target.checked)}
                  disabled={anyProcessing}
                />
                <span>English manuals (skip language detection, process entire manual)</span>
              </label>
            </div>
            <div className="process-actions">
              <button
                type="button"
                onClick={handleStartProcessing}
                disabled={batchItems.length === 0 || anyProcessing || allProcessed}
                className="action-button"
              >
                {anyProcessing ? (
                  <>
                    <span className="spinner"></span>
                    Processing...
                  </>
                ) : allProcessed ? (
                  "Processing Complete"
                ) : (
                  "Start Processing"
                )}
              </button>
            </div>

            <div className="batch-progress-table">
              <table>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Status</th>
                    <th>Language</th>
                  </tr>
                </thead>
                <tbody>
                  {batchItems.map((item) => (
                    <tr
                      key={item.id}
                      className={`status-row status-${item.status}`}
                      onClick={() => setSelectedItemId(item.id)}
                    >
                      <td className="file-name-cell">{item.file.name}</td>
                      <td className="status-cell">
                        {item.status === "pending" && <span className="status-badge pending">Pending</span>}
                        {item.status === "processing" && (
                          <span className="status-badge processing">
                            <span className="spinner-small"></span> Processing
                          </span>
                        )}
                        {item.status === "complete" && <span className="status-badge complete">Complete</span>}
                        {item.status === "error" && <span className="status-badge error">Error</span>}
                        {item.status === "cancelled" && <span className="status-badge cancelled">Cancelled</span>}
                      </td>
                      <td className="language-cell">
                        {item.detectedLanguage || "—"}
                        {item.translated && " (translated)"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {selectedItem && (
              <div ref={processLogRef} className="process-log">
                <div className="log-header">Logs: {selectedItem.file.name}</div>
                {selectedItem.logs.length > 0 ? (
                  selectedItem.logs.map((line, idx) => (
                    <div
                      key={idx}
                      className={`log-line ${idx === selectedItem.logs.length - 1 ? "log-line-latest" : ""}`}
                    >
                      {line}
                    </div>
                  ))
                ) : (
                  <div className="log-placeholder">Processing logs will appear here...</div>
                )}
              </div>
            )}
          </div>
        );

      case "verification":
        return (
          <div className="wizard-step verification-step">
            <h3>Step 3: Verify Metadata</h3>
            <p className="step-description">
              Review each manual with the original PDF. Click on a manual to verify its metadata.
            </p>
            <div className="verification-layout">
              {/* Manual list sidebar */}
              <div className="verification-sidebar">
                <h4>Manuals</h4>
                <ul className="verification-list">
                  {batchItems
                    .filter((item) => item.status === "complete")
                    .map((item) => (
                      <li
                        key={item.id}
                        className={`verification-list-item ${selectedItemId === item.id ? "selected" : ""} ${item.isVerified ? "verified" : ""}`}
                        onClick={() => setSelectedItemId(item.id)}
                      >
                        <span className="verify-indicator">
                          {item.isVerified ? "[OK]" : "[ ]"}
                        </span>
                        <span className="item-name" title={item.file.name}>
                          {item.file.name.length > 25
                            ? item.file.name.slice(0, 22) + "..."
                            : item.file.name}
                        </span>
                      </li>
                    ))}
                </ul>
                <div className="verification-progress">
                  {itemsReadyForUpload.length} / {batchItems.filter((i) => i.status === "complete").length} verified
                </div>
              </div>

              {/* Main content area */}
              <div className="verification-main">
                {selectedItem && selectedItem.status === "complete" ? (
                  <>
                    {/* PDF Viewer */}
                    <div className="verification-pdf">
                      <PdfViewer
                        file={selectedItem.token ? getManualPdfUrl(selectedItem.token) : null}
                        maxHeight="350px"
                      />
                    </div>

                    {/* Metadata Form */}
                    <div className="verification-form">
                      {selectedItem.analyzeStatus === "analyzing" ? (
                        <div className="analyzing-status">
                          <span className="spinner"></span>
                          <span>Analyzing manual with AI...</span>
                        </div>
                      ) : selectedItem.analyzeStatus === "error" ? (
                        <div className="analyze-error">
                          <p>Analysis failed: {selectedItem.analyzeError}</p>
                          <button
                            type="button"
                            onClick={() => handleAnalyzeItem(selectedItem.id)}
                            className="action-button small"
                          >
                            Retry Analysis
                          </button>
                        </div>
                      ) : (
                        <>
                          <div className="metadata-grid">
                            {(["id", "name", "brand", "model", "room", "category"] as const).map(
                              (field) => (
                                <label key={field}>
                                  {field.toUpperCase()}
                                  {(field === "id" || field === "name") && (
                                    <span className="required">*</span>
                                  )}
                                  <input
                                    type="text"
                                    value={selectedItem.metadata?.[field] ?? ""}
                                    onChange={(e) =>
                                      handleUpdateMetadata(selectedItem.id, field, e.target.value)
                                    }
                                    disabled={selectedItem.isVerified}
                                  />
                                </label>
                              )
                            )}
                          </div>
                          <div className="verification-actions">
                            {!selectedItem.isVerified ? (
                              <button
                                type="button"
                                onClick={() => handleVerifyItem(selectedItem.id)}
                                disabled={
                                  !selectedItem.metadata?.id || !selectedItem.metadata?.name
                                }
                                className="action-button primary"
                              >
                                Mark as Verified
                              </button>
                            ) : (
                              <div className="verified-badge">
                                <span>[OK]</span> Verified
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="no-selection">
                    <p>Select a manual from the list to verify its metadata.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case "upload":
        return (
          <div className="wizard-step">
            <h3>Step 4: Upload to Knowledge Base</h3>
            <p className="step-description">
              Review and upload all verified manuals to your knowledge base.
            </p>
            <div className="upload-review">
              <h4>Ready to Upload ({itemsReadyForUpload.length})</h4>
              <ul className="upload-list">
                {itemsReadyForUpload.map((item) => (
                  <li key={item.id} className="upload-list-item">
                    <div className="upload-item-info">
                      <span className="device-name">{item.metadata?.name || item.file.name}</span>
                      <span className="device-details">
                        {[item.metadata?.brand, item.metadata?.model, item.metadata?.room]
                          .filter(Boolean)
                          .join(" | ") || "No additional details"}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            {commitStatus && <p className="status-message">{commitStatus}</p>}
          </div>
        );
    }
  };

  const steps: WizardStep[] = ["file-selection", "processing", "verification", "upload"];
  const currentStepIndex = steps.indexOf(currentStep);

  return (
    <>
      {/* Confirmation popup */}
      {showCancelConfirm && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="confirm-popup">
            <h3>Cancel Manual Upload?</h3>
            <p>
              All progress will be lost and any uploaded files will be deleted. This cannot be
              undone.
            </p>
            <div className="confirm-actions">
              <button onClick={() => setShowCancelConfirm(false)} className="confirm-button secondary">
                Keep Working
              </button>
              <button onClick={handleCancelWizard} className="confirm-button danger">
                Yes, Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="modal-overlay" onClick={handleClose}>
        <div
          className={`modal-content ${currentStep === "verification" ? "modal-wide" : ""}`}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="modal-header">
            <h2>
              {replacingDevice
                ? `Replace Manual - ${replacingDevice.name}`
                : batchItems.length > 1
                  ? `Batch Manual Onboarding (${batchItems.length} files)`
                  : "Manual Onboarding"}
            </h2>
            <button
              className="close-button"
              onClick={handleClose}
              disabled={anyProcessing || isCommitting || isUploadComplete}
              aria-label="Close"
            >
              X
            </button>
          </div>

          <div className="wizard-progress">
            {steps.map((step, idx) => (
              <div
                key={step}
                className={`progress-step ${idx <= currentStepIndex ? "active" : ""} ${idx === currentStepIndex ? "current" : ""}`}
              >
                <div className="progress-circle">{idx + 1}</div>
                <div className="progress-label">
                  {step === "file-selection" && "Select"}
                  {step === "processing" && "Process"}
                  {step === "verification" && "Verify"}
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
                disabled={isUploadComplete}
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
                  onClick={handleCommitBatch}
                  disabled={isCommitting || isUploadComplete || itemsReadyForUpload.length === 0}
                  className="footer-button primary"
                >
                  {isCommitting
                    ? "Uploading..."
                    : isUploadComplete
                      ? "Complete"
                      : `Upload ${itemsReadyForUpload.length} Manual(s)`}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
