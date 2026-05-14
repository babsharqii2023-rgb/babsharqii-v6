// ═══════════════════════════════════════════════════════════════════
// مأمون v18 — useVoice Hook
// React hook for voice input and voice commands
// ═══════════════════════════════════════════════════════════════════

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { getVoiceController, type VoiceCommand, type VoiceState } from '@/lib/voice';

interface UseVoiceReturn {
  isListening: boolean;
  isSupported: boolean;
  transcript: string;
  confidence: number;
  error: string | null;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
  lastCommand: VoiceCommand | null;
}

export function useVoice(
  onTranscript?: (text: string) => void,
  onCommand?: (command: VoiceCommand) => void,
  lang: 'ar' | 'en' = 'ar'
): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>({
    isListening: false,
    isSupported: false,
    transcript: '',
    confidence: 0,
    error: null,
  });
  const [lastCommand, setLastCommand] = useState<VoiceCommand | null>(null);
  const controllerRef = useRef<ReturnType<typeof getVoiceController> | null>(null);

  useEffect(() => {
    const controller = getVoiceController();
    controllerRef.current = controller;
    setState(prev => ({ ...prev, isSupported: controller.isSupported }));
    return () => {
      // Don't destroy — keep the singleton
    };
  }, []);

  useEffect(() => {
    if (controllerRef.current) {
      controllerRef.current.setLanguage(lang);
    }
  }, [lang]);

  const handleResult = useCallback((text: string, command?: VoiceCommand) => {
    if (command) {
      setLastCommand(command);
      onCommand?.(command);
    } else {
      onTranscript?.(text);
    }
  }, [onTranscript, onCommand]);

  const handleStateChange = useCallback((newState: VoiceState) => {
    setState(newState);
  }, []);

  const startListening = useCallback(() => {
    controllerRef.current?.start(handleResult, handleStateChange);
  }, [handleResult, handleStateChange]);

  const stopListening = useCallback(() => {
    controllerRef.current?.stop();
    setState(prev => ({ ...prev, isListening: false }));
  }, []);

  const toggleListening = useCallback(() => {
    if (state.isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [state.isListening, startListening, stopListening]);

  return {
    isListening: state.isListening,
    isSupported: state.isSupported,
    transcript: state.transcript,
    confidence: state.confidence,
    error: state.error,
    startListening,
    stopListening,
    toggleListening,
    lastCommand,
  };
}
