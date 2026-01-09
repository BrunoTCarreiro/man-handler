import { useState, useEffect } from "react";
import {
  checkOllamaConnection,
  getOllamaModels,
  testOllamaModel,
  completeSetup,
  type OllamaModelsResponse,
} from "../api/client";
import { getErrorMessage } from "../api/errors";
import "./FirstTimeSetupWizard.css";

interface FirstTimeSetupWizardProps {
  onComplete: () => void;
}

export function FirstTimeSetupWizard({ onComplete }: FirstTimeSetupWizardProps) {
  const [ollamaStatus, setOllamaStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [ollamaMessage, setOllamaMessage] = useState<string>("");
  const [models, setModels] = useState<OllamaModelsResponse | null>(null);
  const [selectedLLM, setSelectedLLM] = useState<string>("");
  const [selectedEmbedding, setSelectedEmbedding] = useState<string>("");
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isTestingLLM, setIsTestingLLM] = useState(false);
  const [isTestingEmbedding, setIsTestingEmbedding] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<string>("");
  const [embeddingTestResult, setEmbeddingTestResult] = useState<string>("");
  const [isCompleting, setIsCompleting] = useState(false);
  const [error, setError] = useState<string>("");

  // Check Ollama connection on mount
  useEffect(() => {
    checkConnection();
  }, []);

  // Auto-load models when connected
  useEffect(() => {
    if (ollamaStatus === "connected" && !models) {
      loadModels();
    }
  }, [ollamaStatus, models]);

  const checkConnection = async () => {
    setOllamaStatus("checking");
    setError("");
    try {
      const result = await checkOllamaConnection();
      setOllamaMessage(result.message);
      
      if (result.status === "connected") {
        setOllamaStatus("connected");
      } else {
        setOllamaStatus("disconnected");
        setError(result.message);
      }
    } catch (err) {
      setOllamaStatus("disconnected");
      const message = getErrorMessage(err);
      setOllamaMessage(message);
      setError(message);
    }
  };

  const loadModels = async () => {
    setIsLoadingModels(true);
    setError("");
    try {
      const result = await getOllamaModels();
      
      if (result.status === "error") {
        setError(result.message || "Failed to load models");
        setModels(null);
      } else {
        setModels(result);
        
        // Auto-select recommended models if available
        const recommendedLLM = result.llm_models.find(m => m.name.includes("mistral:instruct"));
        const recommendedEmbedding = result.embedding_models.find(m => m.name.includes("bge-m3"));
        
        if (recommendedLLM) setSelectedLLM(recommendedLLM.name);
        if (recommendedEmbedding) setSelectedEmbedding(recommendedEmbedding.name);
        
        // If no recommended models, select first available
        if (!recommendedLLM && result.llm_models.length > 0) {
          setSelectedLLM(result.llm_models[0].name);
        }
        if (!recommendedEmbedding && result.embedding_models.length > 0) {
          setSelectedEmbedding(result.embedding_models[0].name);
        }
      }
    } catch (err) {
      setError(getErrorMessage(err));
      setModels(null);
    } finally {
      setIsLoadingModels(false);
    }
  };

  const handleTestLLM = async () => {
    if (!selectedLLM) return;
    
    setIsTestingLLM(true);
    setLlmTestResult("");
    try {
      const result = await testOllamaModel(selectedLLM, "llm");
      if (result.status === "success" && result.output) {
        const display = result.input 
          ? `✓ Input: "${result.input}" → Output: "${result.output}"`
          : `✓ ${result.output}`;
        setLlmTestResult(display);
      } else if (result.status === "success") {
        setLlmTestResult("✓ Working");
      } else {
        setLlmTestResult(`✗ ${result.message}`);
      }
    } catch (err) {
      setLlmTestResult(`✗ ${getErrorMessage(err)}`);
    } finally {
      setIsTestingLLM(false);
    }
  };

  const handleTestEmbedding = async () => {
    if (!selectedEmbedding) return;
    
    setIsTestingEmbedding(true);
    setEmbeddingTestResult("");
    try {
      const result = await testOllamaModel(selectedEmbedding, "embedding");
      if (result.status === "success" && result.output) {
        const display = result.input 
          ? `✓ Input: "${result.input}" → ${result.output}`
          : `✓ ${result.output}`;
        setEmbeddingTestResult(display);
      } else if (result.status === "success") {
        setEmbeddingTestResult("✓ Working");
      } else {
        setEmbeddingTestResult(`✗ ${result.message}`);
      }
    } catch (err) {
      setEmbeddingTestResult(`✗ ${getErrorMessage(err)}`);
    } finally {
      setIsTestingEmbedding(false);
    }
  };

  const handleComplete = async () => {
    if (!selectedLLM || !selectedEmbedding) {
      setError("Please select both LLM and embedding models");
      return;
    }

    setIsCompleting(true);
    setError("");
    try {
      await completeSetup(selectedLLM, selectedEmbedding, selectedLLM);
      onComplete();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsCompleting(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <div className="setup-overlay">
      <div className="setup-content">
        <div className="setup-header">
          <h1>Welcome to Home Manual Assistant!</h1>
          <p className="setup-subtitle">Let's get you set up with Ollama models</p>
        </div>

        <div className="setup-body">
          {/* Ollama Connection Status */}
          <div className="setup-section">
            <h3>1. Ollama Connection</h3>
            <div className={`connection-status status-${ollamaStatus}`}>
              <div className="status-icon">
                {ollamaStatus === "checking" && <span className="spinner"></span>}
                {ollamaStatus === "connected" && <span>✓</span>}
                {ollamaStatus === "disconnected" && <span>✗</span>}
              </div>
              <div className="status-text">
                <strong>{ollamaMessage}</strong>
                {ollamaStatus === "disconnected" && (
                  <p className="status-hint">
                    Make sure Ollama is running. You can start it with: <code>ollama serve</code>
                  </p>
                )}
              </div>
              {ollamaStatus === "disconnected" && (
                <button
                  className="retry-button"
                  onClick={checkConnection}
                  disabled={ollamaStatus === "checking"}
                >
                  Retry
                </button>
              )}
            </div>
          </div>

          {/* Model Selection */}
          {ollamaStatus === "connected" && (
            <>
              <div className="setup-section">
                <div className="section-header">
                  <h3>2. Select Models</h3>
                  <button
                    className="refresh-button"
                    onClick={loadModels}
                    disabled={isLoadingModels}
                    title="Refresh models list"
                  >
                    {isLoadingModels ? <span className="spinner-small"></span> : "↻"}
                  </button>
                </div>

                {isLoadingModels ? (
                  <div className="loading-message">
                    <span className="spinner"></span>
                    Loading available models...
                  </div>
                ) : models && models.total > 0 ? (
                  <>
                    {/* LLM Selection */}
                    <div className="model-group">
                      <label htmlFor="llm-select">
                        <strong>Language Model (LLM)</strong>
                        <span className="label-hint">For chat, translation, and analysis</span>
                      </label>
                      <div className="model-select-row">
                        <select
                          id="llm-select"
                          value={selectedLLM}
                          onChange={(e) => {
                            setSelectedLLM(e.target.value);
                            setLlmTestResult("");
                          }}
                          className="model-select"
                        >
                          <option value="">-- Select LLM --</option>
                          {models.llm_models.map((model) => (
                            <option key={model.name} value={model.name}>
                              {model.name} ({formatBytes(model.size)})
                            </option>
                          ))}
                        </select>
                        <button
                          className="test-button"
                          onClick={handleTestLLM}
                          disabled={!selectedLLM || isTestingLLM}
                        >
                          {isTestingLLM ? <span className="spinner-small"></span> : "Test"}
                        </button>
                      </div>
                      {llmTestResult && (
                        <div className={`test-result ${llmTestResult.startsWith("✓") ? "success" : "error"}`}>
                          {llmTestResult}
                        </div>
                      )}
                    </div>

                    {/* Embedding Selection */}
                    <div className="model-group">
                      <label htmlFor="embedding-select">
                        <strong>Embedding Model</strong>
                        <span className="label-hint">For semantic search in manuals</span>
                      </label>
                      <div className="model-select-row">
                        <select
                          id="embedding-select"
                          value={selectedEmbedding}
                          onChange={(e) => {
                            setSelectedEmbedding(e.target.value);
                            setEmbeddingTestResult("");
                          }}
                          className="model-select"
                        >
                          <option value="">-- Select Embedding Model --</option>
                          {models.embedding_models.map((model) => (
                            <option key={model.name} value={model.name}>
                              {model.name} ({formatBytes(model.size)})
                            </option>
                          ))}
                        </select>
                        <button
                          className="test-button"
                          onClick={handleTestEmbedding}
                          disabled={!selectedEmbedding || isTestingEmbedding}
                        >
                          {isTestingEmbedding ? <span className="spinner-small"></span> : "Test"}
                        </button>
                      </div>
                      {embeddingTestResult && (
                        <div className={`test-result ${embeddingTestResult.startsWith("✓") ? "success" : "error"}`}>
                          {embeddingTestResult}
                        </div>
                      )}
                    </div>

                    {/* Recommended models hint */}
                    {models.llm_models.length > 0 && models.embedding_models.length > 0 && (
                      <div className="setup-hint">
                        <strong>Recommended:</strong> mistral:instruct for LLM, bge-m3 for embeddings
                      </div>
                    )}
                  </>
                ) : (
                  <div className="no-models-message">
                    <p><strong>No models found!</strong></p>
                    <p>You need to pull Ollama models first. Run these commands:</p>
                    <pre className="command-block">
                      ollama pull mistral:instruct{"\n"}
                      ollama pull bge-m3
                    </pre>
                    <button className="refresh-button-large" onClick={loadModels}>
                      Refresh After Installing
                    </button>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Error Display */}
          {error && (
            <div className="setup-error">
              {error}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="setup-footer">
          <button
            className="complete-button"
            onClick={handleComplete}
            disabled={
              ollamaStatus !== "connected" ||
              !selectedLLM ||
              !selectedEmbedding ||
              isCompleting
            }
          >
            {isCompleting ? (
              <>
                <span className="spinner"></span>
                Completing Setup...
              </>
            ) : (
              "Complete Setup"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}





