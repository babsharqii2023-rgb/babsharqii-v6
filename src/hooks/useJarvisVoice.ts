'use client';

import { useCallback, useRef, useState } from 'react';

// ═══════════════════════════════════════════════════════════
// مأمون JARVIS — نظام الصوت
// صوت خيال علمي جميل مثل JARVIS من أيرون مان
// يستخدم Web Speech API مع فلترة الصوت العربية
// ═══════════════════════════════════════════════════════════

export function useJarvisVoice() {
  const [speaking, setSpeaking] = useState(false);
  const [enabled, setEnabled] = useState(true);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = useCallback((text: string, lang: 'ar' | 'en' = 'ar') => {
    if (!enabled || typeof window === 'undefined' || !window.speechSynthesis) return;

    // إيقاف أي كلام سابق
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === 'ar' ? 'ar-SA' : 'en-US';
    utterance.rate = lang === 'ar' ? 0.95 : 1.0;
    utterance.pitch = lang === 'ar' ? 1.1 : 0.9;
    utterance.volume = 0.85;

    // محاولة اختيار صوت عربي إن وُجد
    const voices = window.speechSynthesis.getVoices();
    const arabicVoice = voices.find(v => v.lang.startsWith('ar'));
    if (arabicVoice) {
      utterance.voice = arabicVoice;
    } else {
      // فلترة: صوت أنثوي عالي الجودة كبديل
      const femaleVoice = voices.find(v =>
        v.name.toLowerCase().includes('google') && v.lang.startsWith('en')
      );
      if (femaleVoice) utterance.voice = femaleVoice;
    }

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, [enabled]);

  const stop = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setSpeaking(false);
  }, []);

  const toggle = useCallback(() => {
    setEnabled(prev => {
      if (prev) stop();
      return !prev;
    });
  }, [stop]);

  return { speak, stop, toggle, speaking, enabled };
}
