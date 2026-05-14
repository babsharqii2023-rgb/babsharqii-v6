// =============================================================================
// BABSHARQII v23.0 — Backend Synchronization Service
// Live data sync with auto-reconnect, stale detection, and change diffing
// =============================================================================

export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting';

export type DataSource = 'backend' | 'cache' | 'fallback';

export interface SyncEventMap {
  connected: { timestamp: number };
  disconnected: { timestamp: number; reason?: string };
  reconnecting: { attempt: number; nextRetryIn: number };
  data_updated: { endpoint: string; changedFields: string[]; source: DataSource };
  stale_detected: { endpoint: string; ageMs: number };
}

type SyncEventHandler<K extends keyof SyncEventMap> = (payload: SyncEventMap[K]) => void;

interface CachedEntry<T = unknown> {
  data: T;
  timestamp: number;
  source: DataSource;
  endpoint: string;
}

interface PollConfig {
  endpoint: string;        // relative path like '/api/mamoun?endpoint=brains'
  intervalMs: number;      // how often to poll
  fallbackData: unknown;   // what to return when no data available
  proxyEndpoint?: string;  // if using the mamoun proxy, the ?endpoint= value
}

const DEFAULT_HEALTH_ENDPOINT = '/api/mamoun?endpoint=status';
const DEFAULT_HEALTH_INTERVAL = 10_000;
const STALE_THRESHOLD_MS = 30_000;
const MAX_BACKOFF_MS = 60_000;
const INITIAL_BACKOFF_MS = 1_000;

class BackendSyncService {
  private status: ConnectionStatus = 'disconnected';
  private listeners: Map<string, Set<(...args: unknown[]) => void>> = new Map();
  private cache: Map<string, CachedEntry> = new Map();
  private pollTimers: Map<string, ReturnType<typeof setInterval>> = new Map();
  private healthTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private lastSuccessfulConnection: number | null = null;
  private registeredEndpoints: Map<string, PollConfig> = new Map();
  private started = false;

  // ─── Event Emitter ───────────────────────────────────────

  on<K extends keyof SyncEventMap>(event: K, handler: SyncEventHandler<K>): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    const wrapped = handler as (...args: unknown[]) => void;
    this.listeners.get(event)!.add(wrapped);
    return () => {
      this.listeners.get(event)?.delete(wrapped);
    };
  }

  private emit<K extends keyof SyncEventMap>(event: K, payload: SyncEventMap[K]): void {
    const handlers = this.listeners.get(event);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(payload);
        } catch (err) {
          console.error(`[BackendSync] Error in ${event} handler:`, err);
        }
      }
    }
  }

  // ─── Connection Management ───────────────────────────────

  getStatus(): ConnectionStatus {
    return this.status;
  }

  getLastSuccessfulConnection(): number | null {
    return this.lastSuccessfulConnection;
  }

  getCacheEntry(endpoint: string): CachedEntry | undefined {
    return this.cache.get(endpoint);
  }

  /**
   * Start the sync service — begins health polling and endpoint polling
   */
  start(): void {
    if (this.started) return;
    this.started = true;
    this.checkHealth();
    this.healthTimer = setInterval(() => this.checkHealth(), DEFAULT_HEALTH_INTERVAL);
  }

  /**
   * Stop all polling and reconnect timers
   */
  stop(): void {
    this.started = false;
    if (this.healthTimer) {
      clearInterval(this.healthTimer);
      this.healthTimer = null;
    }
    for (const [key, timer] of this.pollTimers) {
      clearInterval(timer);
    }
    this.pollTimers.clear();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Register an endpoint to be polled at a given interval
   */
  registerEndpoint(config: PollConfig): () => void {
    const key = config.endpoint;
    this.registeredEndpoints.set(key, config);

    // If we already have cached data, start polling immediately
    if (this.started && this.status === 'connected') {
      this.startEndpointPolling(key, config);
    } else if (this.started) {
      // Even when disconnected, try once to populate cache with fallback
      this.fetchEndpoint(config);
    }

    // Return unregister function
    return () => {
      this.registeredEndpoints.delete(key);
      const timer = this.pollTimers.get(key);
      if (timer) {
        clearInterval(timer);
        this.pollTimers.delete(key);
      }
    };
  }

  /**
   * Force a refetch of a specific endpoint
   */
  async refetch(endpoint: string): Promise<CachedEntry | undefined> {
    const config = this.registeredEndpoints.get(endpoint);
    if (!config) return undefined;
    await this.fetchEndpoint(config);
    return this.cache.get(endpoint);
  }

  /**
   * Force a refetch of all registered endpoints
   */
  async refetchAll(): Promise<void> {
    const promises: Promise<void>[] = [];
    for (const [key, config] of this.registeredEndpoints) {
      promises.push(this.fetchEndpoint(config));
    }
    await Promise.allSettled(promises);
  }

  // ─── Internal: Health Check ──────────────────────────────

  private async checkHealth(): Promise<void> {
    try {
      const response = await fetch(DEFAULT_HEALTH_ENDPOINT, {
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        const data = await response.json();
        const wasOffline = this.status !== 'connected';

        if (wasOffline) {
          // Just came back online!
          this.status = 'connected';
          this.reconnectAttempt = 0;
          this.lastSuccessfulConnection = Date.now();
          this.emit('connected', { timestamp: Date.now() });

          // Immediately refetch all endpoints with fresh data
          await this.refetchAll();

          // Start polling all registered endpoints
          for (const [key, config] of this.registeredEndpoints) {
            this.startEndpointPolling(key, config);
          }

          // Cancel any pending reconnect timer
          if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
          }
        } else {
          this.lastSuccessfulConnection = Date.now();
        }

        // Check for stale data
        this.checkStaleData();
      } else {
        this.handleDisconnect(`Backend returned ${response.status}`);
      }
    } catch {
      this.handleDisconnect('Network error');
    }
  }

  private handleDisconnect(reason: string): void {
    const wasConnected = this.status === 'connected';

    if (wasConnected) {
      this.status = 'disconnected';
      this.emit('disconnected', { timestamp: Date.now(), reason });

      // Stop all endpoint polling
      for (const [key, timer] of this.pollTimers) {
        clearInterval(timer);
      }
      this.pollTimers.clear();

      // Start reconnect with exponential backoff
      this.reconnectAttempt = 0;
      this.scheduleReconnect();
    } else if (this.status === 'reconnecting') {
      // Still failing, keep trying
      this.scheduleReconnect();
    }

    // Check for stale data
    this.checkStaleData();
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return; // Already scheduled

    this.status = 'reconnecting';
    this.reconnectAttempt++;

    const backoff = Math.min(
      INITIAL_BACKOFF_MS * Math.pow(2, this.reconnectAttempt - 1),
      MAX_BACKOFF_MS
    );
    // Add some jitter (±20%)
    const jitter = backoff * (0.8 + Math.random() * 0.4);
    const nextRetryIn = Math.round(jitter);

    this.emit('reconnecting', {
      attempt: this.reconnectAttempt,
      nextRetryIn,
    });

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      await this.checkHealth();
    }, nextRetryIn);
  }

  // ─── Internal: Endpoint Polling ──────────────────────────

  private startEndpointPolling(key: string, config: PollConfig): void {
    // Clear existing timer
    const existingTimer = this.pollTimers.get(key);
    if (existingTimer) clearInterval(existingTimer);

    const timer = setInterval(() => {
      this.fetchEndpoint(config);
    }, config.intervalMs);

    this.pollTimers.set(key, timer);
  }

  private async fetchEndpoint(config: PollConfig): Promise<void> {
    const { endpoint, fallbackData, proxyEndpoint } = config;

    try {
      const url = proxyEndpoint
        ? `/api/mamoun?endpoint=${encodeURIComponent(proxyEndpoint)}`
        : endpoint;

      const response = await fetch(url, {
        signal: AbortSignal.timeout(8000),
      });

      if (response.ok) {
        const rawData = await response.json();
        const source: DataSource = rawData.source === 'python_backend' ? 'backend' : 'cache';

        // Compare with cached data to detect changes
        const oldEntry = this.cache.get(endpoint);
        const changedFields = oldEntry
          ? this.diffObjects(oldEntry.data, rawData)
          : ['*initial*'];

        this.cache.set(endpoint, {
          data: rawData,
          timestamp: Date.now(),
          source,
          endpoint,
        });

        if (changedFields.length > 0) {
          this.emit('data_updated', {
            endpoint,
            changedFields,
            source,
          });
        }
      } else {
        // Server responded but with error — use cache or fallback
        this.useFallbackOrCache(endpoint, fallbackData);
      }
    } catch {
      // Network error — use cache or fallback
      this.useFallbackOrCache(endpoint, fallbackData);
    }
  }

  private useFallbackOrCache(endpoint: string, fallbackData: unknown): void {
    const existing = this.cache.get(endpoint);
    if (!existing) {
      // No cache available, use fallback
      this.cache.set(endpoint, {
        data: fallbackData,
        timestamp: Date.now(),
        source: 'fallback',
        endpoint,
      });
      this.emit('data_updated', {
        endpoint,
        changedFields: ['*fallback*'],
        source: 'fallback',
      });
    }
    // If cache exists, keep it (don't overwrite with stale fallback)
  }

  // ─── Internal: Stale Detection ───────────────────────────

  private checkStaleData(): void {
    const now = Date.now();
    for (const [endpoint, entry] of this.cache) {
      const ageMs = now - entry.timestamp;
      if (ageMs > STALE_THRESHOLD_MS) {
        this.emit('stale_detected', {
          endpoint,
          ageMs,
        });
      }
    }
  }

  /**
   * Returns true if a cached entry's data is older than the stale threshold
   */
  isStale(endpoint: string): boolean {
    const entry = this.cache.get(endpoint);
    if (!entry) return true;
    return Date.now() - entry.timestamp > STALE_THRESHOLD_MS;
  }

  /**
   * Get the age of cached data for an endpoint (in ms)
   */
  getDataAge(endpoint: string): number | null {
    const entry = this.cache.get(endpoint);
    if (!entry) return null;
    return Date.now() - entry.timestamp;
  }

  // ─── Internal: Object Diffing ───────────────────────────

  private diffObjects(oldData: unknown, newData: unknown, prefix = ''): string[] {
    const changes: string[] = [];

    if (oldData === newData) return changes;
    if (typeof oldData !== typeof newData || oldData === null || newData === null) {
      return [prefix || '*root*'];
    }

    if (typeof oldData === 'object' && typeof newData === 'object') {
      const oldObj = oldData as Record<string, unknown>;
      const newObj = newData as Record<string, unknown>;
      const allKeys = new Set([...Object.keys(oldObj), ...Object.keys(newObj)]);

      // Skip the 'source' field — it changes with every request
      for (const key of allKeys) {
        if (key === 'source') continue;
        const fullPath = prefix ? `${prefix}.${key}` : key;
        if (!(key in oldObj)) {
          changes.push(`${fullPath}(added)`);
        } else if (!(key in newObj)) {
          changes.push(`${fullPath}(removed)`);
        } else if (oldObj[key] !== newObj[key]) {
          if (typeof oldObj[key] === 'object' && typeof newObj[key] === 'object' && oldObj[key] !== null && newObj[key] !== null) {
            changes.push(...this.diffObjects(oldObj[key], newObj[key], fullPath));
          } else {
            changes.push(fullPath);
          }
        }
      }
    }

    return changes;
  }
}

// ─── Singleton Export ──────────────────────────────────────

const backendSyncService = new BackendSyncService();

// Auto-start on import (client-side only)
if (typeof window !== 'undefined') {
  // Defer start to avoid blocking initial render
  setTimeout(() => backendSyncService.start(), 100);
}

export { backendSyncService };
export type { PollConfig, CachedEntry };
