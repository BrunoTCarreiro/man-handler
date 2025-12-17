/**
 * Application configuration with environment variable validation.
 *
 * Environment variables:
 * - VITE_API_BASE_URL: Backend API URL (default: http://localhost:8000)
 * - VITE_EXPOSE_NETWORK: Set to "1" to enable network access and auto-detection
 */

function getEnvVar(key: string, defaultValue: string): string {
  const value = import.meta.env[key];
  if (value === undefined || value === "") {
    return defaultValue;
  }
  return value;
}

function validateUrl(url: string, name: string): string {
  try {
    new URL(url);
    return url;
  } catch {
    console.warn(
      `[Config] Invalid URL for ${name}: "${url}". Using default.`
    );
    return "http://localhost:8000";
  }
}

/**
 * Get the API base URL.
 * - If VITE_API_BASE_URL is explicitly set, use it
 * - If VITE_EXPOSE_NETWORK is enabled, auto-detect from current hostname
 * - Otherwise, default to localhost
 */
function getApiBaseUrl(): string {
  const explicitUrl = getEnvVar("VITE_API_BASE_URL", "");
  
  // If explicitly set, use it
  if (explicitUrl) {
    return validateUrl(explicitUrl, "VITE_API_BASE_URL");
  }
  
  // Check if network exposure is enabled
  const exposeNetwork = getEnvVar("VITE_EXPOSE_NETWORK", "0") === "1";
  
  // Only auto-detect if network exposure is enabled
  if (exposeNetwork && typeof window !== "undefined") {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    // Use port 8000 for the backend API
    const apiUrl = `${protocol}//${hostname}:8000`;
    return apiUrl;
  }
  
  // Default to localhost
  return "http://localhost:8000";
}

export const config = {
  /**
   * Backend API base URL.
   * Auto-detects from current hostname if VITE_API_BASE_URL is not set.
   * This allows the app to work when accessed via local network IP addresses.
   */
  apiBaseUrl: getApiBaseUrl(),
} as const;

// Log configuration in development
if (import.meta.env.DEV) {
  console.log("[Config] API Base URL:", config.apiBaseUrl);
}

