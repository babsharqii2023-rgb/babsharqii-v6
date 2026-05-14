// ═══════════════════════════════════════════════════════════════════
// useBrainSound — React Hook for BrainSound
// Wraps the BrainSound class for use in React components
// ═══════════════════════════════════════════════════════════════════

'use client';

import { useRef, useCallback, useEffect } from 'react';
import { BrainSound, type SoundEvent, type SoundMode } from '@/lib/brain-sound';

interface UseBrainSoundReturn {
  playEvent: (event: SoundEvent, options?: { brainId?: string }) => void;
  playBrainActivation: (brainId: string) => void;
  updatePreferences: (prefs: { enabled?: boolean; volume?: number; mode?: SoundMode }) => void;
  resume: () => void;
}

export function useBrainSound(
  initialPrefs?: { enabled?: boolean; volume?: number; mode?: SoundMode }
): UseBrainSoundReturn {
  const soundRef = useRef<BrainSound | null>(null);

  // Create BrainSound instance on first use
  const getSound = useCallback(() => {
    if (!soundRef.current) {
      soundRef.current = new BrainSound(initialPrefs);
    }
    return soundRef.current;
  }, [initialPrefs]);

  const playEvent = useCallback((event: SoundEvent, options?: { brainId?: string }) => {
    getSound().playEvent(event, options);
  }, [getSound]);

  const playBrainActivation = useCallback((brainId: string) => {
    getSound().playBrainActivation(brainId);
  }, [getSound]);

  const updatePreferences = useCallback((prefs: { enabled?: boolean; volume?: number; mode?: SoundMode }) => {
    getSound().updatePreferences(prefs);
  }, [getSound]);

  const resume = useCallback(() => {
    getSound().resume();
  }, [getSound]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      soundRef.current?.destroy();
      soundRef.current = null;
    };
  }, []);

  return {
    playEvent,
    playBrainActivation,
    updatePreferences,
    resume,
  };
}
