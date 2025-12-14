export function getErrorMessage(err: unknown, fallback = "Unknown error"): string {
  if (err instanceof Error) return err.message || fallback;
  if (typeof err === "string") return err || fallback;
  try {
    return JSON.stringify(err);
  } catch {
    return fallback;
  }
}


