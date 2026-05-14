// ═══════════════════════════════════════════════════════════════════
// مأمون v18 — Mamoun Holo-Command Audio System
// Web Audio API powered — ALL sounds procedurally generated
// Every movement has a sound — feels like a LIVING ROBOT
// ═══════════════════════════════════════════════════════════════════

'use client';

let audioCtx: AudioContext | null = null;

function getAudioCtx(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

// ─── Master Volume ─────────────────────────────────────────
let masterVolume = 0.5;

export function setMasterVolume(vol: number) {
  masterVolume = Math.max(0, Math.min(1, vol));
}
export function getMasterVolume(): number {
  return masterVolume;
}

export function isAudioAvailable(): boolean {
  return typeof AudioContext !== 'undefined' || typeof (window as any).webkitAudioContext !== 'undefined';
}

// ─── Core: Play a tone with envelope ───────────────────────
function playTone(
  frequency: number,
  duration: number,
  type: OscillatorType = 'sine',
  volume: number = 0.15,
  detune: number = 0,
  delay: number = 0
) {
  try {
    const ctx = getAudioCtx();
    const vol = volume * masterVolume;
    if (vol < 0.001) return; // Skip silent tones

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const filter = ctx.createBiquadFilter();

    osc.type = type;
    osc.frequency.value = frequency;
    osc.detune.value = detune;

    filter.type = 'lowpass';
    filter.frequency.value = 3000;
    filter.Q.value = 1;

    gain.gain.setValueAtTime(0, ctx.currentTime + delay);
    gain.gain.linearRampToValueAtTime(vol, ctx.currentTime + delay + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    osc.start(ctx.currentTime + delay);
    osc.stop(ctx.currentTime + delay + duration + 0.01);
  } catch {
    // Audio not available — silent fallback
  }
}

// ─── Noise burst (for mechanical / air sounds) ─────────────
function playNoise(duration: number, volume: number = 0.05, delay: number = 0, filterFreq: number = 2000) {
  try {
    const ctx = getAudioCtx();
    const vol = volume * masterVolume;
    if (vol < 0.001) return;

    const bufferSize = ctx.sampleRate * duration;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * 0.5;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = filterFreq;
    filter.Q.value = 0.5;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, ctx.currentTime + delay);
    gain.gain.linearRampToValueAtTime(vol, ctx.currentTime + delay + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    source.start(ctx.currentTime + delay);
    source.stop(ctx.currentTime + delay + duration + 0.01);
  } catch {
    // Silent
  }
}

// ═══════════════════════════════════════════════════════════════
// 🤖 ROBOT MOVEMENT SOUNDS — Feels ALIVE
// ═══════════════════════════════════════════════════════════════

// ─── Boot Sound — Cinematic Power-On (Arc Reactor startup) ─
export function playBootSound() {
  // Deep reactor hum rising
  playTone(55, 2.0, 'sine', 0.12, 0, 0);
  playTone(82, 1.8, 'sine', 0.08, 0, 0.05);
  // Servo whine
  playNoise(0.6, 0.04, 0.2, 800);
  // Power-up sweep
  playTone(160, 0.5, 'sawtooth', 0.03, 0, 0.3);
  playTone(320, 0.4, 'triangle', 0.04, 0, 0.5);
  playTone(480, 0.3, 'sine', 0.03, 0, 0.7);
  // Mechanical click
  playTone(120, 0.04, 'square', 0.08, 0, 0.85);
  playNoise(0.03, 0.06, 0.85, 3000);
  // Sparkle
  playTone(1200, 0.15, 'sine', 0.03, 0, 0.9);
  playTone(1800, 0.1, 'sine', 0.02, 0, 1.0);
  // Final chime (Arc Reactor online!)
  playTone(880, 0.5, 'sine', 0.08, 0, 1.1);
  playTone(1320, 0.35, 'sine', 0.05, 0, 1.2);
  playTone(1760, 0.2, 'sine', 0.03, 0, 1.3);
  // Air release
  playNoise(0.3, 0.03, 1.4, 1500);
}

// ─── Mode Switch — Servo motor + holographic whoosh ────────
export function playModeSwitchSound(mode: 'chat' | 'deliberation' | 'workshop' | 'command' | 'consciousness') {
  const modeFreqs: Record<string, number> = {
    chat: 523,
    deliberation: 392,
    workshop: 440,
    command: 330,
    consciousness: 587, // D5 — ethereal, higher pitch for consciousness mode
  };
  const freq = modeFreqs[mode] || 440;

  // Servo whine (mechanical movement)
  playNoise(0.15, 0.04, 0, 1200);
  playTone(200, 0.1, 'sawtooth', 0.02, 0, 0);

  // Holographic whoosh
  playTone(freq * 1.5, 0.08, 'triangle', 0.06);
  playTone(freq, 0.15, 'sine', 0.1, 0, 0.06);
  playTone(freq * 1.25, 0.1, 'sine', 0.05, 0, 0.12);
  // Shimmer
  playTone(freq * 2, 0.06, 'sine', 0.02, 0, 0.08);

  // Mechanical lock
  playTone(150, 0.04, 'square', 0.05, 0, 0.15);
  playNoise(0.02, 0.03, 0.15, 2000);
}

// ─── Hover Sound — Subtle electronic hum ───────────────────
export function playHoverSound() {
  playTone(1400 + Math.random() * 200, 0.06, 'sine', 0.025);
  playTone(700, 0.04, 'triangle', 0.015, 0, 0.01);
}

// ─── Click / Tap Sound — Mechanical button press ──────────
export function playClickSound() {
  playTone(800, 0.03, 'square', 0.06);
  playNoise(0.02, 0.04, 0, 3500);
  playTone(600, 0.04, 'sine', 0.03, 0, 0.02);
}

// ─── Swipe Sound — Air whoosh ──────────────────────────────
export function playSwipeSound(direction: 'left' | 'right' | 'up' | 'down' = 'left') {
  const freqShift = direction === 'right' || direction === 'up' ? 1.2 : 0.8;
  playNoise(0.12, 0.05, 0, 1800 * freqShift);
  playTone(300 * freqShift, 0.08, 'sine', 0.02);
  playTone(500 * freqShift, 0.06, 'triangle', 0.015, 0, 0.03);
}

// ─── Card Pick Up — Mechanical grab ────────────────────────
export function playCardPickupSound() {
  playTone(350, 0.06, 'triangle', 0.04);
  playNoise(0.04, 0.03, 0, 2500);
  playTone(500, 0.04, 'sine', 0.03, 0, 0.04);
}

// ─── Card Drop — Mechanical release ────────────────────────
export function playCardDropSound() {
  playTone(250, 0.06, 'triangle', 0.04);
  playNoise(0.05, 0.04, 0, 2000);
  playTone(180, 0.05, 'sine', 0.02, 0, 0.02);
}

// ─── Data Processing — Blip blip ───────────────────────────
export function playDataBlip() {
  playTone(2000 + Math.random() * 500, 0.04, 'sine', 0.03);
}

export function playDataProcessSound() {
  for (let i = 0; i < 4; i++) {
    playTone(800 + i * 300 + Math.random() * 200, 0.05, 'sine', 0.03, 0, i * 0.08);
  }
}

// ─── Scan Sweep — Scanner sound ────────────────────────────
export function playScanSound() {
  playTone(400, 0.3, 'sawtooth', 0.02);
  playTone(600, 0.3, 'sawtooth', 0.015, 0, 0.1);
  playTone(800, 0.2, 'sine', 0.01, 0, 0.2);
}

// ─── Alert Chirp — Robot notification ──────────────────────
export function playAlertChirp(type: 'info' | 'success' | 'warning' | 'error' = 'info') {
  const configs = {
    info: { freq: 660, freq2: 880, vol: 0.07 },
    success: { freq: 523, freq2: 784, vol: 0.09 },
    warning: { freq: 440, freq2: 349, vol: 0.09 },
    error: { freq: 330, freq2: 262, vol: 0.11 },
  };
  const cfg = configs[type];
  playTone(cfg.freq, 0.08, 'sine', cfg.vol);
  playNoise(0.02, 0.02, 0, 3000);
  playTone(cfg.freq2, 0.12, 'sine', cfg.vol * 0.7, 0, 0.08);
}

// Keep backward compatibility
export const playNotificationSound = playAlertChirp;

// ─── Wake Sound — مأمون is listening ──────────────────────
export function playWakeSound() {
  playTone(440, 0.08, 'sine', 0.06);
  playTone(660, 0.08, 'sine', 0.05, 0, 0.06);
  playTone(880, 0.12, 'sine', 0.04, 0, 0.12);
  playNoise(0.05, 0.02, 0, 2500);
}

// ─── Sleep Sound — Powering down ──────────────────────────
export function playSleepSound() {
  playTone(440, 0.3, 'sine', 0.06);
  playTone(330, 0.3, 'sine', 0.05, 0, 0.2);
  playTone(220, 0.4, 'sine', 0.04, 0, 0.4);
  playNoise(0.3, 0.03, 0.5, 800);
}

// ─── Message Send Sound — Digital transmit ─────────────────
export function playSendSound() {
  playTone(880, 0.06, 'triangle', 0.06);
  playNoise(0.02, 0.03, 0, 3000);
  playTone(1100, 0.05, 'sine', 0.04, 0, 0.04);
}

// ─── Message Receive Sound — Digital incoming ──────────────
export function playReceiveSound() {
  playTone(660, 0.08, 'sine', 0.06);
  playTone(880, 0.06, 'sine', 0.04, 0, 0.06);
  playNoise(0.02, 0.02, 0.08, 2500);
}

// ─── Brain Activation Sound — Each brain has unique tone ───
export function playBrainActivationSound(brainId: string) {
  const brainFreqs: Record<string, number> = {
    neural: 440,
    causal: 349,
    symbolic: 523,
    bayesian: 392,
    world_model: 294,
  };
  const freq = brainFreqs[brainId] || 440;
  playTone(freq, 0.15, 'sine', 0.07);
  playNoise(0.04, 0.02, 0.1, 2000);
  playTone(freq * 1.5, 0.12, 'sine', 0.04, 0, 0.08);
  playTone(freq * 2, 0.08, 'sine', 0.02, 0, 0.16);
}

// ─── Thinking Sound — Subtle processor hum ─────────────────
let thinkingOsc: OscillatorNode | null = null;
let thinkingGain: GainNode | null = null;
let thinkingLFO: OscillatorNode | null = null;

export function startThinkingSound() {
  try {
    if (thinkingOsc) return; // Already playing
    const ctx = getAudioCtx();
    thinkingOsc = ctx.createOscillator();
    thinkingGain = ctx.createGain();

    thinkingOsc.type = 'sine';
    thinkingOsc.frequency.value = 120;
    thinkingGain.gain.value = 0;

    // Slow LFO for subtle pulsing (like a processor working)
    thinkingLFO = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    thinkingLFO.frequency.value = 2.5;
    lfoGain.gain.value = 0.015;
    thinkingLFO.connect(lfoGain);
    lfoGain.connect(thinkingGain.gain);
    thinkingLFO.start();

    // Add subtle data processing blips
    const lfo2 = ctx.createOscillator();
    const lfo2Gain = ctx.createGain();
    lfo2.frequency.value = 7;
    lfo2Gain.gain.value = 0.008;
    lfo2.connect(lfo2Gain);
    lfo2Gain.connect(thinkingGain.gain);
    lfo2.start();

    thinkingOsc.connect(thinkingGain);
    thinkingGain.connect(ctx.destination);

    thinkingGain.gain.linearRampToValueAtTime(0.025 * masterVolume, ctx.currentTime + 0.5);
    thinkingOsc.start();
  } catch {
    // Silent
  }
}

export function stopThinkingSound() {
  try {
    if (thinkingGain && audioCtx) {
      thinkingGain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.3);
    }
    setTimeout(() => {
      try { thinkingOsc?.stop(); } catch { /* */ }
      try { thinkingLFO?.stop(); } catch { /* */ }
      thinkingOsc = null;
      thinkingGain = null;
      thinkingLFO = null;
    }, 400);
  } catch {
    thinkingOsc = null;
    thinkingGain = null;
    thinkingLFO = null;
  }
}

// ─── Keyboard Click Sound ──────────────────────────────────
export function playKeyClick() {
  playTone(1800 + Math.random() * 400, 0.02, 'square', 0.008);
}

// ─── Tab Switch Sound — Quick beep ─────────────────────────
export function playTabSwitchSound() {
  playTone(1000, 0.04, 'sine', 0.03);
  playTone(1200, 0.03, 'sine', 0.02, 0, 0.03);
}

// ─── Toggle Sound — On/Off switch ──────────────────────────
export function playToggleSound(on: boolean) {
  if (on) {
    playTone(440, 0.06, 'sine', 0.05);
    playTone(660, 0.06, 'sine', 0.04, 0, 0.05);
  } else {
    playTone(660, 0.06, 'sine', 0.05);
    playTone(440, 0.06, 'sine', 0.04, 0, 0.05);
  }
}

// ─── PulseCore Press Sound — Navigation button ─────────────
export function playPulseCoreSound() {
  playTone(523, 0.06, 'sine', 0.05);
  playNoise(0.03, 0.02, 0, 2800);
}

// ─── Idle Hum — Continuous subtle presence ─────────────────
let idleOsc: OscillatorNode | null = null;
let idleGain: GainNode | null = null;

export function startIdleHum() {
  try {
    if (idleOsc) return;
    const ctx = getAudioCtx();
    idleOsc = ctx.createOscillator();
    idleGain = ctx.createGain();

    idleOsc.type = 'sine';
    idleOsc.frequency.value = 60;
    idleGain.gain.value = 0;

    // Very slow LFO
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    lfo.frequency.value = 0.3;
    lfoGain.gain.value = 0.005;
    lfo.connect(lfoGain);
    lfoGain.connect(idleGain.gain);
    lfo.start();

    // Subtle harmonics
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.value = 90;
    gain2.gain.value = 0;
    gain2.gain.linearRampToValueAtTime(0.006 * masterVolume, ctx.currentTime + 2);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start();

    idleOsc.connect(idleGain);
    idleGain.connect(ctx.destination);

    idleGain.gain.linearRampToValueAtTime(0.008 * masterVolume, ctx.currentTime + 2);
    idleOsc.start();
  } catch {
    // Silent
  }
}

export function stopIdleHum() {
  try {
    if (idleGain && audioCtx) {
      idleGain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 1);
    }
    setTimeout(() => {
      try { idleOsc?.stop(); } catch { /* */ }
      idleOsc = null;
      idleGain = null;
    }, 1200);
  } catch {
    idleOsc = null;
    idleGain = null;
  }
}

// ═══════════════════════════════════════════════════════════════
// 🗣️ JARVIS TTS — مأمون speaks!
// ═══════════════════════════════════════════════════════════════

let ttsEnabled = true;
let ttsVoice: SpeechSynthesisVoice | null = null;
let lastSpokenId = '';

export function setTTSEnabled(enabled: boolean) {
  ttsEnabled = enabled;
}

export function isTTSEnabled(): boolean {
  return ttsEnabled;
}

// Find the best available voice for JARVIS-like speech
function getBestVoice(lang: 'ar' | 'en'): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null;

  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;

  // For Arabic: find Arabic voice
  if (lang === 'ar') {
    const arVoice = voices.find(v => v.lang.startsWith('ar'));
    if (arVoice) return arVoice;
  }

  // For English: find a deep/male voice (JARVIS-like)
  if (lang === 'en') {
    // Prefer Google UK English Male (closest to JARVIS)
    const jarvisVoice = voices.find(v =>
      v.name.includes('Google UK English Male') ||
      v.name.includes('Daniel') ||
      v.name.includes('Microsoft David')
    );
    if (jarvisVoice) return jarvisVoice;

    // Fallback: any English male
    const enMale = voices.find(v =>
      v.lang.startsWith('en') && (v.name.includes('Male') || v.name.toLowerCase().includes('david'))
    );
    if (enMale) return enMale;

    // Any English voice
    const enVoice = voices.find(v => v.lang.startsWith('en'));
    if (enVoice) return enVoice;
  }

  // Fallback: any voice
  return voices[0] || null;
}

export function speak(text: string, lang: 'ar' | 'en' = 'ar', messageId?: string) {
  if (!ttsEnabled) return;
  if (typeof window === 'undefined' || !window.speechSynthesis) return;

  // Don't repeat the same message
  const id = messageId || text.slice(0, 50);
  if (id === lastSpokenId) return;
  lastSpokenId = id;

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  // Clean text for speech (remove code blocks, markdown)
  const cleanText = text
    .replace(/```[\s\S]*?```/g, '') // Remove code blocks
    .replace(/`[^`]+`/g, '') // Remove inline code
    .replace(/[#*_~]/g, '') // Remove markdown
    .replace(/\[.*?\]\(.*?\)/g, '') // Remove links
    .replace(/\n{2,}/g, '. ') // Double newline = period
    .replace(/\n/g, ', ') // Single newline = comma
    .trim();

  if (!cleanText) return;

  // Limit length (don't read essays)
  const maxLen = 500;
  const speechText = cleanText.length > maxLen
    ? cleanText.slice(0, maxLen) + '...'
    : cleanText;

  const utterance = new SpeechSynthesisUtterance(speechText);
  const voice = getBestVoice(lang);
  if (voice) utterance.voice = voice;
  utterance.lang = lang === 'ar' ? 'ar-SA' : 'en-US';
  utterance.rate = lang === 'ar' ? 1.0 : 0.95;
  utterance.pitch = lang === 'ar' ? 1.0 : 0.9; // Slightly deeper for JARVIS feel
  utterance.volume = masterVolume;

  // Play a subtle "about to speak" sound
  playTone(600, 0.04, 'sine', 0.02);

  utterance.onend = () => {
    // Subtle end chirp
    playTone(800, 0.03, 'sine', 0.015);
  };

  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

// Preload voices (they load asynchronously)
if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
  };
}
