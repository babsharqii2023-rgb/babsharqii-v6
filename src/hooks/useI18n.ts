'use client';

import { useState, useCallback, useEffect } from 'react';
import { type Lang, getLang, setLang, toggleLang as toggle, t, type TranslationKey } from '@/lib/i18n';

export function useI18n() {
  const [lang, setLangState] = useState<Lang>(getLang);

  useEffect(() => {
    const handler = () => setLangState(getLang());
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  const set = useCallback((newLang: Lang) => {
    setLang(newLang);
    setLangState(newLang);
    // Dispatch custom event so other components update
    window.dispatchEvent(new Event('mamoun-lang-change'));
  }, []);

  const toggleLang = useCallback(() => {
    const next = toggle();
    setLangState(next);
    window.dispatchEvent(new Event('mamoun-lang-change'));
  }, []);

  // Listen for custom lang change events
  useEffect(() => {
    const handler = () => setLangState(getLang());
    window.addEventListener('mamoun-lang-change', handler);
    return () => window.removeEventListener('mamoun-lang-change', handler);
  }, []);

  return {
    lang,
    setLang: set,
    toggleLang,
    t: useCallback((key: TranslationKey) => t(key, lang), [lang]),
    isRTL: lang === 'ar',
    dir: lang === 'ar' ? 'rtl' as const : 'ltr' as const,
  };
}
