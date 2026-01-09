import { useState, useEffect } from "react";
import {
  getConfig,
  getOllamaModels,
  testOllamaModel,
  updateConfig,
  type ConfigData,
  type OllamaModelsResponse,
} from "../api/client";
import { getErrorMessage } from "../api/errors";
import "./ModelConfigSection.css";

interface ModelConfigSectionProps {
  onConfigUpdate?: () => void;
}

export function ModelConfigSection({ onConfigUpdate }: ModelConfigSectionProps) {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [models, setModels] = useState<OllamaModelsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTestingLLM, setIsTestingLLM] = useState(false);
  const [isTestingEmbedding, setIsTestingEmbedding] = useState(false);
  const [isTestingTranslation, setIsTestingTranslation] = useState(false);
  const [isTestingOCR, setIsTestingOCR] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string>("");
  const [success, setSuccess] = useState<string>("");
  
  // Editing state
  const [editingLLM, setEditingLLM] = useState(false);
  const [editingEmbedding, setEditingEmbedding] = useState(false);
  const [editingTranslation, setEditingTranslation] = useState(false);
  const [selectedLLM, setSelectedLLM] = useState("");
  const [selectedEmbedding, setSelectedEmbedding] = useState("");
  const [selectedTranslation, setSelectedTranslation] = useState("");
  const [llmTestResult, setLlmTestResult] = useState("");
  const [embeddingTestResult, setEmbeddingTestResult] = useState("");
  const [translationTestResult, setTranslationTestResult] = useState("");
  const [ocrTestResult, setOcrTestResult] = useState("");
  
  const OCR_MODEL = "deepseek-ocr:3b"; // Hardcoded in backend
  
  // RAG params
  const [topK, setTopK] = useState(5);
  const [chunkSize, setChunkSize] = useState(800);
  const [chunkOverlap, setChunkOverlap] = useState(200);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await getConfig();
      setConfig(data);
      setTopK(data.rag_params.top_k);
      setChunkSize(data.rag_params.chunk_size);
      setChunkOverlap(data.rag_params.chunk_overlap);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const loadModels = async () => {
    setIsLoadingModels(true);
    setError("");
    try {
      const result = await getOllamaModels();
      if (result.status === "error") {
        setError(result.message || "Failed to load models");
      } else {
        setModels(result);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoadingModels(false);
    }
  };

  const handleStartEditLLM = () => {
    if (!config) return;
    setSelectedLLM(config.ollama_models.llm);
    setEditingLLM(true);
    setLlmTestResult("");
    if (!models) loadModels();
  };

  const handleStartEditEmbedding = () => {
    if (!config) return;
    setSelectedEmbedding(config.ollama_models.embedding);
    setEditingEmbedding(true);
    setEmbeddingTestResult("");
    if (!models) loadModels();
  };

  const handleStartEditTranslation = () => {
    if (!config) return;
    setSelectedTranslation(config.ollama_models.translation);
    setEditingTranslation(true);
    setTranslationTestResult("");
    if (!models) loadModels();
  };

  const handleTestTranslation = async () => {
    if (!selectedTranslation) return;
    setIsTestingTranslation(true);
    setTranslationTestResult("");
    try {
      const result = await testOllamaModel(selectedTranslation, "llm", "translation");
      if (result.status === "success" && result.output) {
        const display = result.input 
          ? `✓ Input: "${result.input}" → Output: "${result.output}"`
          : `✓ ${result.output}`;
        setTranslationTestResult(display);
      } else if (result.status === "success") {
        setTranslationTestResult("✓ Working");
      } else {
        setTranslationTestResult(`✗ ${result.message}`);
      }
    } catch (err) {
      setTranslationTestResult(`✗ ${getErrorMessage(err)}`);
    } finally {
      setIsTestingTranslation(false);
    }
  };

  const handleTestOCR = async () => {
    setIsTestingOCR(true);
    setOcrTestResult("");
    try {
      const result = await testOllamaModel(OCR_MODEL, "llm", "ocr");
      if (result.status === "success" && result.output) {
        const display = result.input 
          ? `✓ Input: "${result.input}" → Output: "${result.output}"`
          : `✓ ${result.output}`;
        setOcrTestResult(display);
      } else if (result.status === "success") {
        setOcrTestResult("✓ Working");
      } else {
        setOcrTestResult(`✗ ${result.message}`);
      }
    } catch (err) {
      setOcrTestResult(`✗ ${getErrorMessage(err)}`);
    } finally {
      setIsTestingOCR(false);
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

  const handleSaveLLM = async () => {
    if (!selectedLLM || !config) return;
    setIsSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateConfig({ llm_model: selectedLLM });
      setConfig(updated);
      setEditingLLM(false);
      setSuccess("LLM model updated successfully");
      onConfigUpdate?.();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveEmbedding = async () => {
    if (!selectedEmbedding || !config) return;
    setIsSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateConfig({ embedding_model: selectedEmbedding });
      setConfig(updated);
      setEditingEmbedding(false);
      setSuccess("Embedding model updated successfully");
      onConfigUpdate?.();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveTranslation = async () => {
    if (!selectedTranslation || !config) return;
    setIsSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateConfig({ translation_model: selectedTranslation });
      setConfig(updated);
      setEditingTranslation(false);
      setSuccess("Translation model updated successfully");
      onConfigUpdate?.();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveRAGParams = async () => {
    setIsSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateConfig({
        top_k: topK,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      });
      setConfig(updated);
      setSuccess("RAG parameters updated successfully");
      onConfigUpdate?.();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetToRecommended = async () => {
    setIsSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateConfig({
        llm_model: "mistral:instruct",
        embedding_model: "bge-m3",
        translation_model: "mistral:instruct",
        top_k: 5,
        chunk_size: 800,
        chunk_overlap: 200,
      });
      setConfig(updated);
      setTopK(5);
      setChunkSize(800);
      setChunkOverlap(200);
      setSuccess("Configuration reset to recommended settings");
      onConfigUpdate?.();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <section className="settings-section">
        <h3>Model Configuration</h3>
        <p className="loading-text">Loading configuration...</p>
      </section>
    );
  }

  if (!config) {
    return (
      <section className="settings-section">
        <h3>Model Configuration</h3>
        <p className="error-text">Failed to load configuration</p>
      </section>
    );
  }

  return (
    <section className="settings-section model-config-section">
      <h3>Model Configuration</h3>
      <p className="section-description">
        Manage Ollama models and RAG parameters for optimal performance.
      </p>

      {error && <div className="config-error">{error}</div>}
      {success && <div className="config-success">{success}</div>}

      {/* LLM Model */}
      <div className="config-item">
        <label className="config-label">Language Model (LLM)</label>
        {!editingLLM ? (
          <div className="config-value-row">
            <span className="config-value">{config.ollama_models.llm}</span>
            <button className="config-edit-btn" onClick={handleStartEditLLM}>
              Change
            </button>
          </div>
        ) : (
          <div className="config-edit-box">
            {isLoadingModels ? (
              <p className="loading-text-small">Loading models...</p>
            ) : models && models.llm_models.length > 0 ? (
              <>
                <select
                  value={selectedLLM}
                  onChange={(e) => {
                    setSelectedLLM(e.target.value);
                    setLlmTestResult("");
                  }}
                  className="config-select"
                >
                  {models.llm_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </select>
                <div className="config-actions">
                  <button
                    className="config-test-btn"
                    onClick={handleTestLLM}
                    disabled={isTestingLLM}
                  >
                    {isTestingLLM ? "Testing..." : "Test"}
                  </button>
                  <button
                    className="config-save-btn"
                    onClick={handleSaveLLM}
                    disabled={isSaving || selectedLLM === config.ollama_models.llm}
                  >
                    Save
                  </button>
                  <button
                    className="config-cancel-btn"
                    onClick={() => setEditingLLM(false)}
                  >
                    Cancel
                  </button>
                </div>
                {llmTestResult && (
                  <div className={`test-result-inline ${llmTestResult.startsWith("✓") ? "success" : "error"}`}>
                    {llmTestResult}
                  </div>
                )}
              </>
            ) : (
              <p className="no-models-text">No LLM models found</p>
            )}
          </div>
        )}
      </div>

      {/* Embedding Model */}
      <div className="config-item">
        <label className="config-label">Embedding Model</label>
        {!editingEmbedding ? (
          <div className="config-value-row">
            <span className="config-value">{config.ollama_models.embedding}</span>
            <button className="config-edit-btn" onClick={handleStartEditEmbedding}>
              Change
            </button>
          </div>
        ) : (
          <div className="config-edit-box">
            {isLoadingModels ? (
              <p className="loading-text-small">Loading models...</p>
            ) : models && models.embedding_models.length > 0 ? (
              <>
                <select
                  value={selectedEmbedding}
                  onChange={(e) => {
                    setSelectedEmbedding(e.target.value);
                    setEmbeddingTestResult("");
                  }}
                  className="config-select"
                >
                  {models.embedding_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </select>
                <div className="config-actions">
                  <button
                    className="config-test-btn"
                    onClick={handleTestEmbedding}
                    disabled={isTestingEmbedding}
                  >
                    {isTestingEmbedding ? "Testing..." : "Test"}
                  </button>
                  <button
                    className="config-save-btn"
                    onClick={handleSaveEmbedding}
                    disabled={isSaving || selectedEmbedding === config.ollama_models.embedding}
                  >
                    Save
                  </button>
                  <button
                    className="config-cancel-btn"
                    onClick={() => setEditingEmbedding(false)}
                  >
                    Cancel
                  </button>
                </div>
                {embeddingTestResult && (
                  <div className={`test-result-inline ${embeddingTestResult.startsWith("✓") ? "success" : "error"}`}>
                    {embeddingTestResult}
                  </div>
                )}
              </>
            ) : (
              <p className="no-models-text">No embedding models found</p>
            )}
          </div>
        )}
      </div>

      {/* Translation Model */}
      <div className="config-item">
        <label className="config-label">Translation Model</label>
        {!editingTranslation ? (
          <div className="config-value-row">
            <span className="config-value">{config.ollama_models.translation}</span>
            <button className="config-edit-btn" onClick={handleStartEditTranslation}>
              Change
            </button>
          </div>
        ) : (
          <div className="config-edit-box">
            {isLoadingModels ? (
              <p className="loading-text-small">Loading models...</p>
            ) : models && models.llm_models.length > 0 ? (
              <>
                <select
                  value={selectedTranslation}
                  onChange={(e) => {
                    setSelectedTranslation(e.target.value);
                    setTranslationTestResult("");
                  }}
                  className="config-select"
                >
                  {models.llm_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </select>
                <div className="config-actions">
                  <button
                    className="config-test-btn"
                    onClick={handleTestTranslation}
                    disabled={isTestingTranslation}
                  >
                    {isTestingTranslation ? "Testing..." : "Test"}
                  </button>
                  <button
                    className="config-save-btn"
                    onClick={handleSaveTranslation}
                    disabled={isSaving || selectedTranslation === config.ollama_models.translation}
                  >
                    Save
                  </button>
                  <button
                    className="config-cancel-btn"
                    onClick={() => setEditingTranslation(false)}
                  >
                    Cancel
                  </button>
                </div>
                {translationTestResult && (
                  <div className={`test-result-inline ${translationTestResult.startsWith("✓") ? "success" : "error"}`}>
                    {translationTestResult}
                  </div>
                )}
              </>
            ) : (
              <p className="no-models-text">No LLM models found</p>
            )}
          </div>
        )}
      </div>

      {/* OCR Model (Read-only) */}
      <div className="config-item">
        <label className="config-label">
          OCR Model
          <span className="config-hint">(Fixed in backend)</span>
        </label>
        <div className="config-value-row">
          <span className="config-value">{OCR_MODEL}</span>
          <button
            className="config-test-btn"
            onClick={handleTestOCR}
            disabled={isTestingOCR}
          >
            {isTestingOCR ? "Testing..." : "Test"}
          </button>
        </div>
        {ocrTestResult && (
          <div className={`test-result-inline ${ocrTestResult.startsWith("✓") ? "success" : "error"}`}>
            {ocrTestResult}
          </div>
        )}
      </div>

      {/* Advanced Settings Toggle */}
      <button
        className="advanced-toggle"
        onClick={() => setShowAdvanced(!showAdvanced)}
      >
        Advanced Settings {showAdvanced ? "▲" : "▼"}
      </button>

      {showAdvanced && (
        <div className="advanced-settings">
          <div className="rag-params">
            <div className="rag-param">
              <label>
                TOP_K
                <span className="param-hint">Number of chunks to retrieve</span>
              </label>
              <input
                type="number"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                min={1}
                max={20}
              />
            </div>
            <div className="rag-param">
              <label>
                CHUNK_SIZE
                <span className="param-hint">Characters per chunk</span>
              </label>
              <input
                type="number"
                value={chunkSize}
                onChange={(e) => setChunkSize(parseInt(e.target.value))}
                min={100}
                max={2000}
                step={100}
              />
            </div>
            <div className="rag-param">
              <label>
                CHUNK_OVERLAP
                <span className="param-hint">Overlap between chunks</span>
              </label>
              <input
                type="number"
                value={chunkOverlap}
                onChange={(e) => setChunkOverlap(parseInt(e.target.value))}
                min={0}
                max={500}
                step={50}
              />
            </div>
          </div>
          <div className="rag-actions">
            <button
              className="config-save-btn"
              onClick={handleSaveRAGParams}
              disabled={
                isSaving ||
                (topK === config.rag_params.top_k &&
                  chunkSize === config.rag_params.chunk_size &&
                  chunkOverlap === config.rag_params.chunk_overlap)
              }
            >
              Save RAG Parameters
            </button>
          </div>
        </div>
      )}

      {/* Reset to Recommended */}
      <button className="reset-to-recommended-btn" onClick={handleResetToRecommended} disabled={isSaving}>
        Reset to Recommended Settings
      </button>
    </section>
  );
}





