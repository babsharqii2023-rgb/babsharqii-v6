// ═══════════════════════════════════════════════════════════════════
// مأمون v18 — Voice Command System
// Web Speech API for speech-to-text input + voice commands
// Works in Chrome, Edge, Safari — with graceful fallback
// ═══════════════════════════════════════════════════════════════════

'use client';

// ─── Speech Recognition Types ──────────────────────────────
interface SpeechRecognitionEvent {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
  length: number;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message: string;
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

export interface VoiceCommand {
  action: 'send' | 'switch_mode' | 'clear' | 'toggle_language' | 'status' | 'deliberate' | 'stop_listening';
  payload?: string;
  mode?: 'chat' | 'deliberation' | 'workshop' | 'command';
}

type VoiceCallback = (transcript: string, command?: VoiceCommand) => void;
type StateCallback = (state: VoiceState) => void;

export interface VoiceState {
  isListening: boolean;
  isSupported: boolean;
  transcript: string;
  confidence: number;
  error: string | null;
}

// ─── Voice Command Patterns ────────────────────────────────
const COMMAND_PATTERNS_AR: Array<{ pattern: RegExp; action: VoiceCommand['action']; mode?: VoiceCommand['mode'] }> = [
  { pattern: /افتح\s*(المحادثة|الشات|الدردشة)/, action: 'switch_mode', mode: 'chat' },
  { pattern: /افتح\s*(المداولة|المناظرة|النقاش)/, action: 'switch_mode', mode: 'deliberation' },
  { pattern: /افتح\s*(الورشة|المحرر|الكود)/, action: 'switch_mode', mode: 'workshop' },
  { pattern: /افتح\s*(القيادة|لوحة التحكم|الأوامر)/, action: 'switch_mode', mode: 'command' },
  { pattern: /غيّ?ر\s*اللغة|لغة|عربي|إنجليزي/, action: 'toggle_language' },
  { pattern: /امسح|مسح|نظّف|حذف/, action: 'clear' },
  { pattern: /حالة|وضع|تقرير/, action: 'status' },
  { pattern: /ناقش|مداول|ناظر/, action: 'deliberate' },
  { pattern: /توقف|أوقف|إيقاف/, action: 'stop_listening' },
];

const COMMAND_PATTERNS_EN: Array<{ pattern: RegExp; action: VoiceCommand['action']; mode?: VoiceCommand['mode'] }> = [
  { pattern: /open\s*(chat|conversation)/, action: 'switch_mode', mode: 'chat' },
  { pattern: /open\s*(deliberation|debate|discussion)/, action: 'switch_mode', mode: 'deliberation' },
  { pattern: /open\s*(workshop|editor|code)/, action: 'switch_mode', mode: 'workshop' },
  { pattern: /open\s*(command|control)/, action: 'switch_mode', mode: 'command' },
  { pattern: /change\s*language|switch\s*language|عربي/, action: 'toggle_language' },
  { pattern: /clear|clean|delete\s*chat/, action: 'clear' },
  { pattern: /status|health|report/, action: 'status' },
  { pattern: /deliberate|debate|discuss/, action: 'deliberate' },
  { pattern: /stop\s*listening|stop/, action: 'stop_listening' },
];

function parseVoiceCommand(text: string, lang: 'ar' | 'en'): VoiceCommand | null {
  const patterns = lang === 'ar' ? COMMAND_PATTERNS_AR : COMMAND_PATTERNS_EN;
  const lower = text.toLowerCase().trim();

  for (const { pattern, action, mode } of patterns) {
    if (pattern.test(lower)) {
      // Extract the payload (everything after the command)
      const match = lower.match(pattern);
      const payload = match ? text.slice(match.index! + match[0].length).trim() : text;
      return { action, mode, payload: payload || undefined };
    }
  }

  return null;
}

// ─── Voice Controller Class ────────────────────────────────

export class VoiceController {
  private recognition: SpeechRecognitionInstance | null = null;
  private onResult: VoiceCallback | null = null;
  private onStateChange: StateCallback | null = null;
  private _isListening = false;
  private _isSupported = false;
  private lang: 'ar' | 'en' = 'ar';
  private restartCount = 0;
  private maxRestarts = 3;

  constructor() {
    const SpeechRecognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognitionCtor) {
      this._isSupported = true;
      this.recognition = new SpeechRecognitionCtor();
      this.setupRecognition();
    }
  }

  private setupRecognition() {
    if (!this.recognition) return;

    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = this.lang === 'ar' ? 'ar-SA' : 'en-US';
    this.recognition.maxAlternatives = 1;

    this.recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      if (finalTranscript) {
        const command = parseVoiceCommand(finalTranscript, this.lang);
        this.onResult?.(finalTranscript, command || undefined);
      }

      this.emitState({
        isListening: true,
        isSupported: true,
        transcript: finalTranscript || interimTranscript,
        confidence: event.results[event.results.length - 1]?.[0]?.confidence ?? 0,
        error: null,
      });
    };

    this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      this.emitState({
        isListening: false,
        isSupported: true,
        transcript: '',
        confidence: 0,
        error: event.error,
      });
    };

    this.recognition.onend = () => {
      // Auto-restart if we're supposed to be listening
      if (this._isListening && this.restartCount < this.maxRestarts) {
        this.restartCount++;
        try {
          this.recognition?.start();
        } catch {
          this._isListening = false;
          this.emitState({
            isListening: false,
            isSupported: true,
            transcript: '',
            confidence: 0,
            error: 'restart_failed',
          });
        }
      } else if (this._isListening) {
        this._isListening = false;
        this.emitState({
          isListening: false,
          isSupported: true,
          transcript: '',
          confidence: 0,
          error: null,
        });
      }
    };
  }

  private emitState(state: VoiceState) {
    this.onStateChange?.(state);
  }

  // ─── Public API ─────────────────────────────────────────

  get isSupported(): boolean {
    return this._isSupported;
  }

  get isListening(): boolean {
    return this._isListening;
  }

  setLanguage(lang: 'ar' | 'en') {
    this.lang = lang;
    if (this.recognition) {
      this.recognition.lang = lang === 'ar' ? 'ar-SA' : 'en-US';
    }
  }

  start(onResult: VoiceCallback, onStateChange: StateCallback) {
    if (!this._isSupported || !this.recognition) return;

    this.onResult = onResult;
    this.onStateChange = onStateChange;
    this.restartCount = 0;

    try {
      this.recognition.start();
      this._isListening = true;
      this.emitState({
        isListening: true,
        isSupported: true,
        transcript: '',
        confidence: 0,
        error: null,
      });
    } catch (e) {
      this.emitState({
        isListening: false,
        isSupported: true,
        transcript: '',
        confidence: 0,
        error: 'start_failed',
      });
    }
  }

  stop() {
    this._isListening = false;
    this.restartCount = this.maxRestarts; // Prevent auto-restart
    try {
      this.recognition?.stop();
    } catch {
      // Already stopped
    }
    this.emitState({
      isListening: false,
      isSupported: true,
      transcript: '',
      confidence: 0,
      error: null,
    });
  }

  toggle(onResult: VoiceCallback, onStateChange: StateCallback) {
    if (this._isListening) {
      this.stop();
    } else {
      this.start(onResult, onStateChange);
    }
  }

  destroy() {
    this.stop();
    this.recognition = null;
    this.onResult = null;
    this.onStateChange = null;
  }
}

// ─── Singleton ─────────────────────────────────────────────

let voiceController: VoiceController | null = null;

export function getVoiceController(): VoiceController {
  if (!voiceController) {
    voiceController = new VoiceController();
  }
  return voiceController;
}
