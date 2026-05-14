// =============================================================================
// BABSHARQII v18.0 — Python Backend Helper
// Shared utility for checking backend availability and proxying requests.
// =============================================================================

const PYTHON_BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
const BACKEND_TIMEOUT = 5000;

let backendAvailableCache: boolean | null = null;
let lastBackendCheck = 0;
const BACKEND_CHECK_INTERVAL = 30_000; // Re-check every 30s

/**
 * Check if the Python backend is currently available.
 * Results are cached for 30 seconds to avoid excessive health checks.
 */
export async function isBackendAvailable(): Promise<boolean> {
  const now = Date.now();
  if (backendAvailableCache !== null && now - lastBackendCheck < BACKEND_CHECK_INTERVAL) {
    return backendAvailableCache;
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    const response = await fetch(`${PYTHON_BACKEND_URL}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    backendAvailableCache = response.ok;
  } catch {
    backendAvailableCache = false;
  }
  lastBackendCheck = now;
  return backendAvailableCache;
}

/**
 * Call the Python backend with a timeout.
 * Returns null if backend is unavailable or request fails.
 */
export async function callBackend(
  path: string,
  options?: RequestInit
): Promise<Response | null> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), BACKEND_TIMEOUT);

    const response = await fetch(`${PYTHON_BACKEND_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    clearTimeout(timeoutId);
    return response.ok ? response : null;
  } catch {
    return null;
  }
}

/**
 * Convenience: call backend and parse JSON response.
 * Returns null if unavailable or response is not ok.
 */
export async function callBackendJSON<T = Record<string, unknown>>(
  path: string,
  options?: RequestInit
): Promise<T | null> {
  const resp = await callBackend(path, options);
  if (!resp) return null;
  try {
    return (await resp.json()) as T;
  } catch {
    return null;
  }
}

export { PYTHON_BACKEND_URL };
