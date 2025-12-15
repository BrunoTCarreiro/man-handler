/**
 * Application configuration with environment variable validation.
 *
 * Environment variables:
 * - VITE_API_BASE_URL: Backend API URL (default: http://localhost:8000)
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

export const config = {
  /**
   * Backend API base URL.
   * Set via VITE_API_BASE_URL environment variable.
   */
  apiBaseUrl: validateUrl(
    getEnvVar("VITE_API_BASE_URL", "http://localhost:8000"),
    "VITE_API_BASE_URL"
  ),
} as const;

// Log configuration in development
if (import.meta.env.DEV) {
  console.log("[Config] API Base URL:", config.apiBaseUrl);
}

