// ═══════════════════════════════════════════════════════════════════
// BrainSound — نظام الصوت التوليدي للعقل الخارق
// Web Audio API generative sound system
// Each brain has a unique oscillator profile
// ═══════════════════════════════════════════════════════════════════

export type SoundEvent =
  | 'intent.detected'
  | 'screen.transition'
  | 'brain.activate'
  | 'brain.deactivate'
  | 'operation.complete'
  | 'operation.error'
  | 'message.receive';

export type SoundMode = 'immersive' | 'ambient' | 'minimal';

export interface SoundPreferences {
  enabled: boolean;
  volume: number; // 0-100
  mode: SoundMode;
}

// ─── Brain Audio Profiles ──────────────────────────────────────

interface BrainAudioProfile {
  id: string;
  oscillatorType: OscillatorType;
  baseFrequency: number;
  harmonicMultiplier: number;
  color: string;
}

const BRAIN_AUDIO_PROFILES: BrainAudioProfile[] = [
  { id: 'neural', oscillatorType: 'sawtooth', baseFrequency: 440, harmonicMultiplier: 1.5, color: '#00e5ff' },
  { id: 'causal', oscillatorType: 'sine', baseFrequency: 349, harmonicMultiplier: 1.33, color: '#ff9100' },
  { id: 'symbolic', oscillatorType: 'square', baseFrequency: 523, harmonicMultiplier: 1.5, color: '#448aff' },
  { id: 'bayesian', oscillatorType: 'triangle', baseFrequency: 392, harmonicMultiplier: 1.5, color: '#69f0ae' },
  { id: 'world_model', oscillatorType: 'sine', baseFrequency: 294, harmonicMultiplier: 1.33, color: '#ffd740' },
];

// ─── Sound Event Configs ───────────────────────────────────────

interface SoundEventConfig {
  frequency: number;
  duration: number;
  type: OscillatorType;
  volume: number;
  harmonics?: Array<{ freq: number; vol: number; delay: number }>;
}

const EVENT_CONFIGS: Record<SoundEvent, SoundEventConfig> = {
  'intent.detected': {
    frequency: 660,
    duration: 0.2,
    type: 'sine',
    volume: 0.12,
    harmonics: [
      { freq: 880, vol: 0.06, delay: 0.06 },
      { freq: 1100, vol: 0.03, delay: 0.12 },
    ],
  },
  'screen.transition': {
    frequency: 440,
    duration: 0.25,
    type: 'triangle',
    volume: 0.08,
    harmonics: [
      { freq: 554, vol: 0.04, delay: 0.08 },
    ],
  },
  'brain.activate': {
    frequency: 523,
    duration: 0.3,
    type: 'sine',
    volume: 0.1,
    harmonics: [
      { freq: 784, vol: 0.05, delay: 0.1 },
      { freq: 1046, vol: 0.03, delay: 0.2 },
    ],
  },
  'brain.deactivate': {
    frequency: 392,
    duration: 0.25,
    type: 'sine',
    volume: 0.06,
    harmonics: [
      { freq: 294, vol: 0.04, delay: 0.1 },
    ],
  },
  'operation.complete': {
    frequency: 523,
    duration: 0.15,
    type: 'sine',
    volume: 0.1,
    harmonics: [
      { freq: 659, vol: 0.07, delay: 0.08 },
      { freq: 784, vol: 0.05, delay: 0.16 },
    ],
  },
  'operation.error': {
    frequency: 220,
    duration: 0.3,
    type: 'square',
    volume: 0.08,
    harmonics: [
      { freq: 165, vol: 0.05, delay: 0.12 },
    ],
  },
  'message.receive': {
    frequency: 880,
    duration: 0.1,
    type: 'sine',
    volume: 0.07,
    harmonics: [
      { freq: 1100, vol: 0.03, delay: 0.05 },
    ],
  },
};

// ─── BrainSound Class ──────────────────────────────────────────

export class BrainSound {
  private audioCtx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private convolver: ConvolverNode | null = null;
  private brainChannels: Map<string, GainNode> = new Map();
  private preferences: SoundPreferences;
  private initialized = false;

  constructor(preferences?: Partial<SoundPreferences>) {
    this.preferences = {
      enabled: preferences?.enabled ?? true,
      volume: preferences?.volume ?? 50,
      mode: preferences?.mode ?? 'ambient',
    };
  }

  // ─── Initialize ────────────────────────────────────────────

  private init(): void {
    if (this.initialized) return;
    try {
      this.audioCtx = new AudioContext();
      this.masterGain = this.audioCtx.createGain();
      this.masterGain.gain.value = this.preferences.enabled
        ? (this.preferences.volume / 100) * 0.5
        : 0;

      // Create reverb (simple delay-based)
      this.convolver = this.createReverb();
      if (this.convolver) {
        this.convolver.connect(this.masterGain);
      }

      this.masterGain.connect(this.audioCtx.destination);

      // Create per-brain channels
      for (const profile of BRAIN_AUDIO_PROFILES) {
        const channelGain = this.audioCtx.createGain();
        channelGain.gain.value = this.preferences.mode === 'immersive' ? 0.8
          : this.preferences.mode === 'ambient' ? 0.4 : 0.15;
        channelGain.connect(this.masterGain);
        this.brainChannels.set(profile.id, channelGain);
      }

      this.initialized = true;
    } catch {
      // Web Audio not available
    }
  }

  // ─── Reverb (delay-based) ──────────────────────────────────

  private createReverb(): ConvolverNode | null {
    if (!this.audioCtx) return null;
    try {
      const convolver = this.audioCtx.createConvolver();
      const rate = this.audioCtx.sampleRate;
      const length = rate * 1.5;
      const impulse = this.audioCtx.createBuffer(2, length, rate);

      for (let channel = 0; channel < 2; channel++) {
        const data = impulse.getChannelData(channel);
        for (let i = 0; i < length; i++) {
          data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, 2.5) * 0.3;
        }
      }

      convolver.buffer = impulse;
      return convolver;
    } catch {
      return null;
    }
  }

  // ─── Play Core Tone ────────────────────────────────────────

  private playTone(
    frequency: number,
    duration: number,
    type: OscillatorType = 'sine',
    volume: number = 0.1,
    delay: number = 0,
    useReverb: boolean = false,
  ): void {
    if (!this.audioCtx || !this.masterGain) return;
    if (!this.preferences.enabled) return;

    const effectiveVol = volume * (this.preferences.volume / 100);
    if (effectiveVol < 0.001) return;

    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }

    const ctx = this.audioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const filter = ctx.createBiquadFilter();

    osc.type = type;
    osc.frequency.value = frequency;
    filter.type = 'lowpass';
    filter.frequency.value = 3000;
    filter.Q.value = 1;

    const now = ctx.currentTime + delay;
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(effectiveVol, now + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    osc.connect(filter);
    filter.connect(gain);

    if (useReverb && this.convolver) {
      const dryGain = ctx.createGain();
      const wetGain = ctx.createGain();
      dryGain.gain.value = 0.7;
      wetGain.gain.value = 0.3;
      gain.connect(dryGain);
      gain.connect(this.convolver);
      dryGain.connect(this.masterGain);
    } else {
      gain.connect(this.masterGain);
    }

    osc.start(now);
    osc.stop(now + duration + 0.05);
  }

  // ─── Play Sound Event ──────────────────────────────────────

  playEvent(event: SoundEvent, options?: { brainId?: string }): void {
    this.init();
    if (!this.preferences.enabled) return;

    const config = EVENT_CONFIGS[event];
    if (!config) return;

    const useReverb = this.preferences.mode === 'immersive';

    // If brainId specified, use brain-specific frequency
    let freq = config.frequency;
    let oscType = config.type;
    if (options?.brainId) {
      const profile = BRAIN_AUDIO_PROFILES.find(p => p.id === options.brainId);
      if (profile) {
        freq = profile.baseFrequency;
        oscType = profile.oscillatorType;
      }
    }

    // Main tone
    this.playTone(freq, config.duration, oscType, config.volume, 0, useReverb);

    // Harmonics
    if (config.harmonics) {
      for (const h of config.harmonics) {
        this.playTone(h.freq, config.duration * 0.7, 'sine', h.vol, h.delay, useReverb);
      }
    }
  }

  // ─── Play Brain-Specific Activation ────────────────────────

  playBrainActivation(brainId: string): void {
    this.init();
    const profile = BRAIN_AUDIO_PROFILES.find(p => p.id === brainId);
    if (!profile) return;

    const useReverb = this.preferences.mode === 'immersive';
    const vol = this.preferences.mode === 'minimal' ? 0.04 : 0.08;

    this.playTone(profile.baseFrequency, 0.2, profile.oscillatorType, vol, 0, useReverb);
    this.playTone(
      profile.baseFrequency * profile.harmonicMultiplier,
      0.15,
      'sine',
      vol * 0.5,
      0.08,
      useReverb,
    );
  }

  // ─── Update Preferences ────────────────────────────────────

  updatePreferences(prefs: Partial<SoundPreferences>): void {
    this.preferences = { ...this.preferences, ...prefs };

    if (this.masterGain) {
      this.masterGain.gain.value = this.preferences.enabled
        ? (this.preferences.volume / 100) * 0.5
        : 0;
    }

    // Update brain channel volumes
    for (const [id, channel] of this.brainChannels) {
      channel.gain.value = this.preferences.mode === 'immersive' ? 0.8
        : this.preferences.mode === 'ambient' ? 0.4 : 0.15;
    }
  }

  // ─── Get Brain Profiles ────────────────────────────────────

  getBrainProfiles(): BrainAudioProfile[] {
    return BRAIN_AUDIO_PROFILES;
  }

  // ─── Resume Audio Context ──────────────────────────────────

  resume(): void {
    if (this.audioCtx?.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  // ─── Destroy ───────────────────────────────────────────────

  destroy(): void {
    try {
      this.audioCtx?.close();
    } catch {
      // ignore
    }
    this.audioCtx = null;
    this.masterGain = null;
    this.convolver = null;
    this.brainChannels.clear();
    this.initialized = false;
  }
}
