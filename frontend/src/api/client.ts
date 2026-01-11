import { config } from "../config";

export const BASE_URL = config.apiBaseUrl;

export function apiUrl(path: string): string {
  if (!path) return BASE_URL;
  return `${BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export type Source = {
  device_id: string | null;
  device_name: string | null;
  room: string | null;
  brand: string | null;
  model: string | null;
  file_name: string;
  page: number | null;
  snippet: string;
};

export type Device = {
  id: string;
  name: string;
  brand?: string | null;
  model?: string | null;
  room?: string | null;
  category?: string | null;
  manual_files: string[];
};

export type ChatResponse = {
  answer: string;
  sources: Source[];
};

export type ManualMetadata = {
  id: string;
  name: string;
  brand?: string | null;
  model?: string | null;
  room?: string | null;
  category?: string | null;
  manual_files: string[];
};

export type ManualExtractResponse = {
  token: string;
  original_filename: string;
  english_filename: string;
  english_pages: number[];
};

export type ManualTranslateResponse = {
  token: string;
  original_filename: string;
  translated_filename: string;
  original_language: string;
  pages_translated: number;
};

export type ManualAnalyzeResponse = {
  token: string;
  suggested_metadata: ManualMetadata;
};

export type ManualProcessResponse = {
  token: string;
  detected_language: string;
  translated: boolean;
  output_filename: string;
  pages: number[] | null;
  logs: string[];
};

export type ProcessingStatus = {
  status: "processing" | "complete" | "error" | "cancelled";
  logs: string[];
  stage: string;
  detected_language?: string;
  translated?: boolean;
  output_filename?: string;
};

export async function getDevices(): Promise<Device[]> {
  const res = await fetch(apiUrl("/devices"));
  if (!res.ok) {
    throw new Error("Failed to load devices");
  }
  return res.json();
}

export async function extractManual(file: File): Promise<ManualExtractResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(apiUrl("/manuals/extract"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Extract failed: ${text || res.status}`);
  }

  return res.json();
}

export async function translateManual(file: File): Promise<ManualTranslateResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(apiUrl("/manuals/translate"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Translation failed: ${text || res.status}`);
  }

  return res.json();
}

export async function processManual(file: File, isEnglishManual: boolean = false, signal?: AbortSignal): Promise<ManualProcessResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("is_english_manual", isEnglishManual ? "true" : "false");

  const res = await fetch(apiUrl("/manuals/process"), {
    method: "POST",
    body: formData,
    signal,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Process failed: ${text || res.status}`);
  }

  return res.json();
}

export async function getProcessingStatus(token: string): Promise<ProcessingStatus> {
  const res = await fetch(apiUrl(`/manuals/process/status/${token}`));
  
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Status check failed: ${text || res.status}`);
  }
  
  return res.json();
}

export async function cancelProcessing(token: string): Promise<void> {
  const res = await fetch(apiUrl(`/manuals/process/cancel/${token}`), {
    method: "POST",
  });
  
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Cancel failed: ${text || res.status}`);
  }
}

export async function resetApp(): Promise<void> {
  const res = await fetch(apiUrl("/reset"), { method: "POST" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Reset failed: ${text || res.status}`);
  }
}

export async function analyzeManual(token: string): Promise<ManualAnalyzeResponse> {
  const res = await fetch(apiUrl("/manuals/analyze"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Analyze failed: ${text || res.status}`);
  }

  return res.json();
}

type ManualCommitPayload = {
  token: string;
  manual_filename: string;
  metadata: ManualMetadata;
};

export async function commitManual(payload: ManualCommitPayload): Promise<Device> {
  const res = await fetch(apiUrl("/manuals/commit"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed: ${text || res.status}`);
  }

  const data = await res.json();
  return data.device;
}

export async function deleteDevice(deviceId: string): Promise<void> {
  const res = await fetch(apiUrl(`/devices/${deviceId}`), {
    method: "DELETE",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Delete failed: ${text || res.status}`);
  }
}

export async function replaceDeviceManual(deviceId: string): Promise<void> {
  const res = await fetch(apiUrl(`/devices/${deviceId}/replace`), {
    method: "POST",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Replace failed: ${text || res.status}`);
  }
}

export async function updateDevice(deviceId: string, metadata: Partial<ManualMetadata>): Promise<Device> {
  const res = await fetch(apiUrl(`/devices/${deviceId}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metadata),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Update failed: ${text || res.status}`);
  }

  return res.json();
}

export async function renameRoom(oldRoom: string, newRoom: string): Promise<void> {
  const res = await fetch(apiUrl("/devices/rooms/rename"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_room: oldRoom, new_room: newRoom }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Rename room failed: ${text || res.status}`);
  }
}

export async function getDeviceMarkdown(deviceId: string): Promise<string> {
  const res = await fetch(apiUrl(`/devices/${deviceId}/markdown`));
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to load markdown: ${text || res.status}`);
  }
  return res.text();
}

export function getDeviceFileUrl(deviceId: string, deviceRelativePath: string): string {
  const clean = deviceRelativePath.startsWith("/") ? deviceRelativePath.slice(1) : deviceRelativePath;
  return apiUrl(`/devices/${deviceId}/files/${clean}`);
}

export async function sendMessage(
  message: string,
  deviceId?: string | null,
  room?: string | null,
  sessionId?: string
): Promise<ChatResponse> {
  const res = await fetch(apiUrl("/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      device_id: deviceId ?? null,
      room: room ?? null,
      session_id: sessionId ?? null,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Chat failed: ${res.status} ${text}`);
  }

  return res.json();
}

export async function clearChatMemory(sessionId: string): Promise<void> {
  const res = await fetch(apiUrl(`/chat/clear/${sessionId}`), {
    method: "POST",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Clear memory failed: ${res.status} ${text}`);
  }
}

// NOTE: legacy `uploadManual()` removed (unused in current UX).

// =============================================================================
// Setup API
// =============================================================================

export type SetupStatusResponse = {
  setup_completed: boolean;
  ollama_status: {
    status: string;
    message: string;
    version?: string;
  };
  current_config: {
    llm_model: string;
    embedding_model: string;
    translation_model: string;
  };
};

export type OllamaModel = {
  name: string;
  size: number;
  modified: string;
};

export type OllamaModelsResponse = {
  status: string;
  llm_models: OllamaModel[];
  embedding_models: OllamaModel[];
  total: number;
  message?: string;
};

export async function getSetupStatus(): Promise<SetupStatusResponse> {
  const res = await fetch(apiUrl("/setup/status"));
  if (!res.ok) {
    throw new Error("Failed to get setup status");
  }
  return res.json();
}

export async function checkOllamaConnection(): Promise<{ status: string; message: string; version?: string }> {
  const res = await fetch(apiUrl("/setup/ollama/connection"));
  if (!res.ok) {
    throw new Error("Failed to check Ollama connection");
  }
  return res.json();
}

export async function getOllamaModels(): Promise<OllamaModelsResponse> {
  const res = await fetch(apiUrl("/setup/ollama/models"));
  if (!res.ok) {
    throw new Error("Failed to get Ollama models");
  }
  return res.json();
}

export async function testOllamaModel(
  modelName: string, 
  modelType: "llm" | "embedding",
  modelPurpose: "general" | "translation" | "ocr" = "general"
): Promise<{ status: string; message: string; input?: string; output?: string }> {
  const res = await fetch(apiUrl(`/setup/ollama/test-model?model_name=${encodeURIComponent(modelName)}&model_type=${modelType}&model_purpose=${modelPurpose}`), {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error("Failed to test model");
  }
  return res.json();
}

export async function restartOllama(): Promise<{ 
  status: "started" | "already_running" | "rate_limited" | "error"; 
  message: string 
}> {
  const res = await fetch(apiUrl("/setup/ollama/restart"), {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error("Failed to restart Ollama");
  }
  return res.json();
}

export async function testTranslation(text: string, sourceLang?: string): Promise<{
  status: string;
  input?: string;
  output?: string;
  source_lang?: string;
  message?: string;
}> {
  const res = await fetch(apiUrl("/setup/translation/test"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_lang: sourceLang }),
  });
  if (!res.ok) {
    throw new Error("Translation test failed");
  }
  return res.json();
}

export async function testOCR(file: File): Promise<{
  status: string;
  input?: string;
  output?: string;
  full_output?: string;
  message?: string;
}> {
  const formData = new FormData();
  formData.append("file", file);
  
  const res = await fetch(apiUrl("/setup/ocr/test"), {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error("OCR test failed");
  }
  return res.json();
}

export async function completeSetup(llmModel: string, embeddingModel: string, translationModel?: string, analysisModel?: string): Promise<{ status: string; message: string }> {
  const res = await fetch(apiUrl("/setup/complete"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      llm_model: llmModel,
      embedding_model: embeddingModel,
      translation_model: translationModel,
      analysis_model: analysisModel,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Setup completion failed: ${text || res.status}`);
  }

  return res.json();
}

export type ConfigData = {
  setup_completed: boolean;
  ollama_models: {
    llm: string;
    embedding: string;
    translation: string;
    analysis: string;
  };
  rag_params: {
    top_k: number;
    chunk_size: number;
    chunk_overlap: number;
  };
};

export async function getConfig(): Promise<ConfigData> {
  const res = await fetch(apiUrl("/setup/config"));
  if (!res.ok) {
    throw new Error("Failed to get configuration");
  }
  const data = await res.json();
  return data.config;
}

export type UpdateConfigParams = {
  llm_model?: string;
  embedding_model?: string;
  translation_model?: string;
  analysis_model?: string;
  top_k?: number;
  chunk_size?: number;
  chunk_overlap?: number;
};

export async function updateConfig(params: UpdateConfigParams): Promise<ConfigData> {
  const res = await fetch(apiUrl("/setup/config"), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Config update failed: ${text || res.status}`);
  }

  const data = await res.json();
  return data.config;
}


