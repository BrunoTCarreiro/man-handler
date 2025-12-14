export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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

export async function processManual(file: File, signal?: AbortSignal): Promise<ManualProcessResponse> {
  const formData = new FormData();
  formData.append("file", file);

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

// NOTE: legacy `uploadManual()` removed (unused in current UX).


