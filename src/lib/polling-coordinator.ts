/**
 * BABSHARQII v40.0 — Unified Polling Coordinator
 * منسق الاستطلاع الموحد — يمنع إرهاق السيرفر
 * 
 * بدلاً من 8 بانلات تستطلع بشكل مستقل كل 5-10 ثوانٍ (≈48-96 طلب/دقيقة)،
 * يجمع الطلبات في دورة واحدة كل 10 ثوانٍ (≈6 طلبات/دقيقة).
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// ── Global Polling State ──────────────────────────────────────────────────

interface PollEntry {
  key: string;
  fetcher: () => Promise<unknown>;
  interval: number; // milliseconds
  lastFetch: number;
  data: unknown;
  error: boolean;
  loading: boolean;
  listeners: Set<(data: unknown, error: boolean) => void>;
}

const pollRegistry = new Map<string, PollEntry>();
let globalTickInterval: ReturnType<typeof setInterval> | null = null;
let activePanelCount = 0;

function startGlobalTick() {
  if (globalTickInterval) return;
  globalTickInterval = setInterval(tickAll, 2000); // فحص كل 2 ثانية
}

function stopGlobalTick() {
  if (globalTickInterval && activePanelCount === 0 && pollRegistry.size === 0) {
    clearInterval(globalTickInterval);
    globalTickInterval = null;
  }
}

async function tickAll() {
  const now = Date.now();
  for (const [, entry] of pollRegistry) {
    if (now - entry.lastFetch >= entry.interval && !entry.loading) {
      entry.loading = true;
      try {
        const data = await entry.fetcher();
        entry.data = data;
        entry.error = false;
        entry.lastFetch = now;
        // إبلاغ كل المستمعين
        for (const listener of entry.listeners) {
          listener(data, false);
        }
      } catch {
        entry.error = true;
        for (const listener of entry.listeners) {
          listener(entry.data, true);
        }
      } finally {
        entry.loading = false;
      }
    }
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────

/**
 * Hook موحد لاستطلاع البيانات من الباكند
 * يمنع الطلبات المتكررة وينسق بين البانلات
 * 
 * @param key مفتاح فريد للطلب
 * @param fetcher دالة جلب البيانات
 * @param interval الفترة بين الطلبات (ms) - الافتراضي 10000
 */
export function usePolledData<T>(
  key: string,
  fetcher: () => Promise<T>,
  interval: number = 10000
): { data: T | null; error: boolean; loading: boolean; refresh: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    activePanelCount++;
    startGlobalTick();

    // إنشاء أو الانضمام لمدخل الاستطلاع
    let entry = pollRegistry.get(key);
    if (!entry) {
      entry = {
        key,
        fetcher: () => fetcherRef.current(),
        interval,
        lastFetch: 0, // سيجلب فوراً
        data: null,
        error: false,
        loading: false,
        listeners: new Set(),
      };
      pollRegistry.set(key, entry);
    }

    const listener: (data: unknown, error: boolean) => void = (newData, newError) => {
      setData(newData as T);
      setError(newError);
      setLoading(false);
    };

    entry.listeners.add(listener);

    // جلب فوري أول مرة
    if (!entry.data && !entry.loading) {
      entry.loading = true;
      fetcherRef.current().then((result) => {
        if (entry) {
          entry.data = result;
          entry.error = false;
          entry.lastFetch = Date.now();
          entry.loading = false;
          for (const l of entry.listeners) {
            l(result, false);
          }
        }
      }).catch(() => {
        if (entry) {
          entry.error = true;
          entry.loading = false;
          for (const l of entry.listeners) {
            l(entry.data, true);
          }
        }
      });
    } else if (entry.data) {
      // بيانات موجودة مسبقاً — استخدمها
      setData(entry.data as T);
      setError(entry.error);
      setLoading(false);
    }

    return () => {
      entry!.listeners.delete(listener);
      activePanelCount--;
      if (entry!.listeners.size === 0) {
        pollRegistry.delete(key);
      }
      stopGlobalTick();
    };
  }, [key, interval]);

  const refresh = useCallback(() => {
    const entry = pollRegistry.get(key);
    if (entry) {
      entry.lastFetch = 0; // سيجلب في الدورة التالية
    }
  }, [key]);

  return { data, error, loading, refresh };
}

/**
 * فترات الاستطلاع المقترحة لكل نوع بيانات
 * البيانات البطيئة التغير = فترة أطول = ضغط أقل على السيرفر
 */
export const POLL_INTERVALS = {
  CRITICAL: 5000,    // بيانات حرجة (نبض القلب، حالة النظام)
  NORMAL: 10000,     // بيانات عادية (أدمغة، مشاريع)
  SLOW: 15000,       // بيانات بطيئة (وعي، تطور)
  VERY_SLOW: 30000,  // بيانات نادرة التغير (إعدادات، أمان)
} as const;
