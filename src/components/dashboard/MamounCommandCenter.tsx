// ═══════════════════════════════════════════════════════════════════════════════
// العقل الخارق — SuperMind Command Center
// مأمون v61 — Three-Panel Layout with 3D Brain Network
//
// Layout: Chat (30%) | ContextScreen (40%) | BrainNetwork (30%)
// Features: SuperMindRouter, Three.js 3D Brain, GSAP, Framer Motion,
//           Web Audio API, SSE Streaming, RTL Arabic
// ═══════════════════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import gsap from 'gsap';
import { useAppStore } from '@/lib/store';
import { fetchBrainStates, fetchLivingVitals, fetchProjects, fetchKernelStatus, type BrainState } from '@/lib/jarvis-api';
import { routeIntent, type SuperMindRoute } from '@/lib/super-mind-router';
import { useBrainSound } from '@/hooks/useBrainSound';
import { useSSEStream } from '@/hooks/useSSEStream';
import BrainNetwork from '@/components/brain/BrainNetwork';
import ContextScreen from '@/components/brain/ContextScreen';
import ThinkingAnimation from '@/components/chat/ThinkingAnimation';
import ChatCard from '@/components/chat/ChatCard';

// ═══════════════════════════════════════════════════════════════════════════════
// الثيم الكوني الموسع — Extended Cosmic Theme
// ═══════════════════════════════════════════════════════════════════════════════

const T = {
  bg: '#080810',
  chatBg: '#0d0d1a',
  primary: '#0d7bb5',
  accent: '#0a9b8a',
  neural: '#0a4a6e',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  bubble: '#1a1a1a',
  white: '#ffffff',

  primaryDim: 'rgba(13,123,181,0.08)',
  primaryMid: 'rgba(13,123,181,0.15)',
  primaryStrong: 'rgba(13,123,181,0.3)',
  primaryGlow: '0 0 12px rgba(13,123,181,0.4)',
  primaryGlowBig: '0 0 24px rgba(13,123,181,0.2)',

  accentDim: 'rgba(10,155,138,0.08)',
  accentMid: 'rgba(10,155,138,0.15)',
  accentStrong: 'rgba(10,155,138,0.3)',
  accentGlow: '0 0 12px rgba(10,155,138,0.4)',

  white90: 'rgba(255,255,255,0.9)',
  white70: 'rgba(200,208,224,0.7)',
  white50: 'rgba(255,255,255,0.5)',
  white30: 'rgba(255,255,255,0.3)',
  white15: 'rgba(255,255,255,0.15)',
  white08: 'rgba(255,255,255,0.08)',
  white04: 'rgba(255,255,255,0.04)',

  green: '#4CAF50',
  orange: '#FF9800',
  red: '#EF4444',

  // Brain colors
  brainNeural: '#00e5ff',
  brainCausal: '#ff9100',
  brainSymbolic: '#448aff',
  brainBayesian: '#69f0ae',
  brainWorldModel: '#ffd740',
};

// ═══════════════════════════════════════════════════════════════════════════════
// المكون الرئيسي — SuperMind Command Center
// ═══════════════════════════════════════════════════════════════════════════════

export default function MamounCommandCenter() {
  // ─── Store ────────────────────────────────────────────────────
  const messages = useAppStore((s) => s.messages);
  const isThinking = useAppStore((s) => s.isThinking);
  const sendMessage = useAppStore((s) => s.sendMessage);
  const addMessage = useAppStore((s) => s.addMessage);
  const setThinking = useAppStore((s) => s.setThinking);
  const clearChat = useAppStore((s) => s.clearChat);
  const updateDeliberationData = useAppStore((s) => s.updateDeliberationData);
  const defaultModel = useAppStore((s) => s.defaultModel);
  const isConscious = useAppStore((s) => s.isConscious);
  const currentIntent = useAppStore((s) => s.currentIntent);
  const setCurrentIntent = useAppStore((s) => s.setCurrentIntent);
  const activeScreen = useAppStore((s) => s.activeScreen);
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);
  const setScreenProps = useAppStore((s) => s.setScreenProps);
  const soundEnabled = useAppStore((s) => s.soundEnabled);
  const soundVolume = useAppStore((s) => s.soundVolume);
  const soundMode = useAppStore((s) => s.soundMode);

  // ─── Local State ──────────────────────────────────────────────
  const [inputText, setInputText] = useState('');
  const [tick, setTick] = useState(0);
  const [brainData, setBrainData] = useState<BrainState[]>([]);
  const [vitality, setVitality] = useState(75);
  const [consciousness, setConsciousness] = useState(0.7);
  const [signalCount, setSignalCount] = useState(0);
  const [activeBrains, setActiveBrains] = useState<string[]>(['neural']);
  const [currentRoute, setCurrentRoute] = useState<SuperMindRoute | null>(null);
  const [brainConfidences, setBrainConfidences] = useState<Record<string, number>>({});
  const [screenAnimation, setScreenAnimation] = useState('fadeIn');
  const [screenPropsData, setScreenPropsData] = useState<Record<string, unknown>>({});

  // ─── Refs ─────────────────────────────────────────────────────
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatPanelRef = useRef<HTMLDivElement>(null);
  const contextPanelRef = useRef<HTMLDivElement>(null);
  const brainPanelRef = useRef<HTMLDivElement>(null);

  // ─── Hooks ────────────────────────────────────────────────────
  const brainSound = useBrainSound({
    enabled: soundEnabled,
    volume: soundVolume,
    mode: soundMode as 'immersive' | 'ambient' | 'minimal',
  });
  const sseStream = useSSEStream();

  // ─── Animation Tick ───────────────────────────────────────────
  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 50);
    return () => clearInterval(iv);
  }, []);

  // ─── Fetch Live Data ──────────────────────────────────────────
  useEffect(() => {
    const load = async () => {
      try {
        const [brainsRes, vitalsRes, projectsRes, kernelRes] = await Promise.allSettled([
          fetchBrainStates(),
          fetchLivingVitals(),
          fetchProjects(),
          fetchKernelStatus(),
        ]);

        if (brainsRes.status === 'fulfilled' && brainsRes.value?.brains?.length) {
          setBrainData(brainsRes.value.brains);
          // Update confidences
          const confs: Record<string, number> = {};
          for (const b of brainsRes.value.brains) {
            confs[b.id] = b.confidence;
          }
          setBrainConfidences(confs);
        }
        if (vitalsRes.status === 'fulfilled') {
          const d = vitalsRes.value as Record<string, unknown>;
          setVitality(Math.round((d.vitality as number) || 75));
        }
        if (kernelRes.status === 'fulfilled') {
          const d = kernelRes.value as unknown as Record<string, unknown>;
          if (d?.kernel_status) setConsciousness(0.7);
        }
      } catch { /* fallback */ }
    };
    load();
    const iv = setInterval(load, 8000);
    return () => clearInterval(iv);
  }, []);

  // ─── Signal Counter ───────────────────────────────────────────
  useEffect(() => {
    const iv = setInterval(() => setSignalCount(s => s + Math.floor(Math.random() * 3)), 2000);
    return () => clearInterval(iv);
  }, []);

  // ─── Scroll Messages ─────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ─── GSAP Panel Transitions ──────────────────────────────────
  useEffect(() => {
    if (chatPanelRef.current) {
      gsap.fromTo(chatPanelRef.current,
        { opacity: 0, x: -20 },
        { opacity: 1, x: 0, duration: 0.5, ease: 'power2.out' }
      );
    }
    if (contextPanelRef.current) {
      gsap.fromTo(contextPanelRef.current,
        { opacity: 0, y: 15 },
        { opacity: 1, y: 0, duration: 0.6, delay: 0.1, ease: 'power2.out' }
      );
    }
    if (brainPanelRef.current) {
      gsap.fromTo(brainPanelRef.current,
        { opacity: 0, x: 20 },
        { opacity: 1, x: 0, duration: 0.5, delay: 0.2, ease: 'power2.out' }
      );
    }
  }, []);

  // ─── Sound preference sync ────────────────────────────────────
  useEffect(() => {
    brainSound.updatePreferences({
      enabled: soundEnabled,
      volume: soundVolume,
      mode: soundMode as 'immersive' | 'ambient' | 'minimal',
    });
  }, [soundEnabled, soundVolume, soundMode, brainSound]);

  // ─── Handle Self-Update Intent ─────────────────────────────────
  const handleSelfUpdate = useCallback(async () => {
    setThinking(true);
    setActiveBrains(['neural', 'causal', 'symbolic']);
    brainSound.playEvent('brain.activate', { brainId: 'neural' });

    addMessage({
      id: `update-start-${Date.now()}`,
      role: 'assistant',
      content: '🔄 جاري فحص التحديثات من GitHub...',
      timestamp: Date.now(),
      confidence: 0.9,
    });

    try {
      // Step 1: Check for updates
      const checkRes = await fetch('/api/update/check');
      const checkData = await checkRes.json();

      if (checkData.status === 'up_to_date') {
        addMessage({
          id: `update-uptodate-${Date.now()}`,
          role: 'assistant',
          content: '✅ النظام محدث بالفعل — لا توجد تحديثات جديدة.',
          timestamp: Date.now(),
          confidence: 1,
          brain: 'causal',
        });
        brainSound.playEvent('operation.complete');
        setThinking(false);
        setActiveBrains(['neural']);
        return;
      }

      const newCommits = checkData.new_commits || 0;
      addMessage({
        id: `update-found-${Date.now()}`,
        role: 'assistant',
        content: `📡 تم العثور على ${newCommits} تحديث جديد. جاري السحب والمراجعة...`,
        timestamp: Date.now(),
        confidence: 0.95,
        brain: 'neural',
      });

      // Step 2: Pull and apply updates
      const pullRes = await fetch('/api/update/pull', { method: 'POST' });
      const pullData = await pullRes.json();

      if (pullData.status === 'success') {
        addMessage({
          id: `update-success-${Date.now()}`,
          role: 'assistant',
          content: `✅ تم التحديث بنجاح! Commit: ${pullData.new_commit || 'unknown'} — الوقت: ${pullData.elapsed_seconds || '?'} ثانية\n${pullData.had_local_changes ? '⚠️ كانت هناك تعديلات محلية تم حفظها.' : ''}${pullData.conflicts_resolved ? '🔧 تم حل تعارضات تلقائياً.' : ''}`,
          timestamp: Date.now(),
          confidence: 1,
          brain: 'neural',
          metadata: { type: 'update', data: pullData },
        });
        brainSound.playEvent('operation.complete');
      } else if (pullData.status === 'up_to_date') {
        addMessage({
          id: `update-uptodate2-${Date.now()}`,
          role: 'assistant',
          content: '✅ النظام محدث بالفعل.',
          timestamp: Date.now(),
          confidence: 1,
          brain: 'causal',
        });
      } else {
        addMessage({
          id: `update-fail-${Date.now()}`,
          role: 'assistant',
          content: `❌ فشل التحديث: ${pullData.error || pullData.message || 'خطأ غير معروف'}`,
          timestamp: Date.now(),
          confidence: 0.5,
          brain: 'causal',
        });
        brainSound.playEvent('operation.error');
      }
    } catch (err) {
      addMessage({
        id: `update-err-${Date.now()}`,
        role: 'assistant',
        content: '❌ فشل الاتصال بخادم التحديثات. تأكد من أن الباك إند يعمل.',
        timestamp: Date.now(),
        confidence: 0.3,
        brain: 'causal',
      });
      brainSound.playEvent('operation.error');
    }
    setThinking(false);
    setActiveBrains(['neural']);
  }, [addMessage, setThinking, brainSound]);

  // ─── Handle Send ──────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = inputText.trim();
    if (!text) return;

    // Resume audio context on user interaction
    brainSound.resume();

    // 1. Route intent via SuperMindRouter
    const route = routeIntent(text);
    setCurrentRoute(route);
    setCurrentIntent(route.intent);

    // 2. Play intent detected sound
    brainSound.playEvent('intent.detected', { brainId: route.activatedBrains[0] });

    // 3. Activate brains for this intent
    setActiveBrains(route.activatedBrains);
    for (const brainId of route.activatedBrains) {
      brainSound.playBrainActivation(brainId);
    }

    // 4. Update context screen if intent has one
    if (route.screenComponent) {
      setScreenAnimation(route.animation);
      setActiveScreen(route.screenComponent);
      setScreenPropsData({ intent: route.intent, message: text });
      setScreenProps({ intent: route.intent, message: text });
      brainSound.playEvent('screen.transition');
    }

    // 5. Send message to store
    sendMessage(text);
    setInputText('');

    // 6. GSAP ripple animation on brain panel
    if (brainPanelRef.current) {
      gsap.fromTo(brainPanelRef.current,
        { boxShadow: '0 0 0px rgba(13,123,181,0)' },
        {
          boxShadow: '0 0 30px rgba(13,123,181,0.3)',
          duration: 0.3,
          yoyo: true,
          repeat: 1,
          ease: 'power2.inOut',
        }
      );
    }

    // 7. Handle special intents directly
    if (route.intent === 'update.pull') {
      handleSelfUpdate();
      return;
    }

    // 8. Call /api/super-mind/chat (with fallback to /api/mamoun-chat)
    try {
      const chatHistory = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      // Try SuperMind endpoint first
      let response: Response;
      try {
        response = await fetch('/api/super-mind/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            model: defaultModel,
            intent: route.intent,
            activated_brains: route.activatedBrains,
            context: {},
          }),
        });
      } catch {
        // Fallback to mamoun-chat
        response = await fetch('/api/mamoun-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, model: defaultModel, context: {} }),
        });
      }

      if (response.ok) {
        const data = await response.json();

        addMessage({
          id: data.id || `resp-${Date.now()}`,
          role: 'assistant',
          content: data.content || 'لم أتمكن من معالجة طلبك.',
          timestamp: Date.now(),
          brain: data.brain || data.winning_brain,
          confidence: data.confidence,
          isRealDeliberation: !!(data.brain_responses || data.consensus_level),
          metadata: {
            ...data.metadata,
            brain_responses: data.brain_responses,
            consensus_level: data.consensus_level,
            cjs: data.cjs,
            conflict_detected: data.conflict_detected,
            mirror_reflection: data.mirror_reflection,
            source: data.source,
            intent: route.intent,
          },
        });

        // Update deliberation data
        if (data.brain_responses || data.consensus_level !== undefined) {
          updateDeliberationData({
            brainResponses: data.brain_responses,
            consensusLevel: data.consensus_level,
            cjs: data.cjs,
            conflictDetected: data.conflict_detected,
            mirrorReflection: data.mirror_reflection,
            queryType: data.query_type,
            winner: data.brain || data.winning_brain,
          });
        }

        // Update brain confidences from response
        if (data.brain_responses) {
          const newConfs: Record<string, number> = { ...brainConfidences };
          for (const [bid, resp] of Object.entries(data.brain_responses) as [string, any][]) {
            if (resp?.confidence) newConfs[bid] = resp.confidence;
          }
          setBrainConfidences(newConfs);
        }

        // Update screen props with response data
        if (route.screenComponent && data) {
          setScreenPropsData(prev => ({ ...prev, responseData: data }));
          setScreenProps({ intent: route.intent, message: text, responseData: data });
        }

        brainSound.playEvent('operation.complete');
      } else {
        addMessage({
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: 'عذراً، حدث خطأ في الاتصال.',
          timestamp: Date.now(),
          confidence: 0.1,
        });
        brainSound.playEvent('operation.error');
      }
    } catch {
      addMessage({
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'عذراً، لم أتمكن من الاتصال بالخادم.',
        timestamp: Date.now(),
        confidence: 0.1,
      });
      brainSound.playEvent('operation.error');
    }
    setThinking(false);
    setActiveBrains(['neural']);
  }, [
    inputText, messages, defaultModel, brainConfidences,
    sendMessage, addMessage, setThinking, updateDeliberationData,
    brainSound, setCurrentIntent, setActiveScreen, setScreenProps,
    handleSelfUpdate,
  ]);

  // ─── Handle Key Down ─────────────────────────────────────────
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // ─── Handle Brain Click ──────────────────────────────────────
  const handleBrainClick = useCallback((brainId: string) => {
    brainSound.playBrainActivation(brainId);
    setActiveBrains(prev =>
      prev.includes(brainId) ? prev.filter(b => b !== brainId) : [...prev, brainId]
    );
  }, [brainSound]);

  // ─── Handle Chat Action ──────────────────────────────────────
  const handleChatAction = useCallback((action: string, messageId: string) => {
    if (action === 'copy') {
      const msg = messages.find(m => m.id === messageId);
      if (msg) {
        navigator.clipboard.writeText(msg.content).catch(() => {});
      }
    }
  }, [messages]);

  // ─── Handle Context Screen Back ──────────────────────────────
  const handleScreenBack = useCallback(() => {
    setActiveScreen(null);
    setCurrentIntent(null);
    setScreenAnimation('fadeIn');
    brainSound.playEvent('screen.transition');
  }, [setActiveScreen, setCurrentIntent, brainSound]);

  // ─── Format Time ─────────────────────────────────────────────
  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  };

  // ─── Breathing Animation ─────────────────────────────────────
  const breathe = 1 + 0.03 * Math.sin(tick * 0.07);

  // ═══════════════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════════════
  return (
    <div dir="rtl" className="supermind-root" style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', width: '100vw',
      background: T.bg, color: T.text,
      fontFamily: "'Cairo', 'Tajawal', 'Space Grotesk', system-ui, sans-serif",
      overflow: 'hidden',
    }}>
      {/* ─── Main Three-Panel Area (responsive) ─── */}
      <div style={{
        display: 'flex', flex: 1, minHeight: 0,
        flexDirection: 'row',
      }} className="supermind-panels">

        {/* ═══════ Panel 1: Chat (30%) ═══════ */}
        <div ref={chatPanelRef} className="supermind-chat-panel" style={{
          width: '30%', minWidth: 240, maxWidth: 440,
          display: 'flex', flexDirection: 'column',
          background: T.chatBg,
          borderLeft: `1px solid ${T.white08}`,
        }}>
          {/* Chat Header */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 14px',
            borderBottom: `1px solid ${T.white08}`,
            background: T.chatBg,
          }}>
            <motion.div
              animate={{
                boxShadow: isConscious ? T.accentGlow : 'none',
              }}
              style={{
                width: 8, height: 8, borderRadius: '50%',
                background: isConscious ? T.accent : T.red,
              }}
            />
            <span style={{ fontSize: 13, fontWeight: 700, color: T.white }}>العقل الخارق</span>
            <span style={{ fontSize: 9, color: T.textDim, flex: 1 }}>مأمون v61</span>

            {/* Sound Toggle */}
            <button
              onClick={() => useAppStore.getState().soundEnabled !== undefined && useAppStore.setState({ soundEnabled: !useAppStore.getState().soundEnabled })}
              style={{
                background: 'transparent', border: 'none',
                color: soundEnabled ? T.accent : T.textDim,
                cursor: 'pointer', fontSize: 12,
              }}
              title={soundEnabled ? 'كتم الصوت' : 'تشغيل الصوت'}
            >
              {soundEnabled ? '🔊' : '🔇'}
            </button>

            <button onClick={clearChat} style={{
              background: T.primaryDim, border: `1px solid ${T.white08}`,
              color: T.textDim, borderRadius: 6, padding: '2px 8px',
              cursor: 'pointer', fontSize: 9,
            }}>
              مسح
            </button>
          </div>

          {/* Intent Badge */}
          <AnimatePresence>
            {currentRoute && currentRoute.intent !== 'default' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                style={{
                  padding: '6px 14px',
                  background: T.primaryDim,
                  borderBottom: `1px solid ${T.white08}`,
                  display: 'flex', alignItems: 'center', gap: 6,
                  overflow: 'hidden',
                }}
              >
                <span style={{ fontSize: 12 }}>{currentRoute.icon}</span>
                <span style={{ fontSize: 10, color: T.primary, fontWeight: 600 }}>
                  {currentRoute.labelAr}
                </span>
                <span style={{ fontSize: 8, color: T.textDim }}>
                  ثقة: {Math.round(currentRoute.confidence * 100)}%
                </span>
                <button
                  onClick={() => { setCurrentIntent(null); setCurrentRoute(null); setActiveScreen(null); }}
                  style={{
                    background: 'transparent', border: 'none',
                    color: T.textDim, cursor: 'pointer', fontSize: 10,
                    marginRight: 'auto',
                  }}
                >
                  ✕
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages Area */}
          <div style={{
            flex: 1, overflowY: 'auto', padding: '8px 12px',
            display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', padding: 20, color: T.textDim, fontSize: 11 }}>
                <motion.div
                  animate={{ scale: breathe }}
                  style={{ fontSize: 32, marginBottom: 8 }}
                >
                  ⚡
                </motion.div>
                <div style={{ fontSize: 16, fontWeight: 700, color: T.primary, marginBottom: 6 }}>العقل الخارق</div>
                <div style={{ lineHeight: 1.8 }}>
                  أنا أتحكم بكل شيء: الباك إند، الفرونت إند، الأدمغة، GitHub، البحث، الإصلاح
                </div>
                <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'center' }}>
                  {['أرني المشاريع', 'إحصائيات الموقع', 'أصلح الأخطاء', 'ابحث عن...', 'أنشئ أداة', 'افتح الطرفية', 'حدث نفسك'].map(cmd => (
                    <button
                      key={cmd}
                      onClick={() => { setInputText(cmd); }}
                      style={{
                        background: T.primaryDim, border: `1px solid ${T.white08}`,
                        borderRadius: 8, padding: '3px 8px', fontSize: 9,
                        color: T.primary, cursor: 'pointer',
                      }}
                    >
                      {cmd}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <ChatCard
                key={msg.id}
                message={msg}
                onAction={handleChatAction}
              />
            ))}

            {/* Thinking Animation */}
            <AnimatePresence>
              {isThinking && (
                <ThinkingAnimation
                  activeBrains={activeBrains}
                  tick={tick}
                />
              )}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </div>

          {/* Input Field */}
          <div style={{
            padding: '8px 12px',
            borderTop: `1px solid ${T.white08}`,
          }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="اكتب رسالتك هنا..."
                dir="rtl"
                style={{
                  flex: 1,
                  background: T.primaryDim,
                  border: `1px solid ${T.accent}`,
                  borderRadius: 12,
                  padding: '10px 14px',
                  color: T.white,
                  fontSize: 12,
                  outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
              <motion.button
                onClick={handleSend}
                disabled={isThinking || !inputText.trim()}
                whileHover={inputText.trim() ? { scale: 1.05 } : {}}
                whileTap={inputText.trim() ? { scale: 0.95 } : {}}
                style={{
                  width: 36, height: 36,
                  borderRadius: '50%',
                  background: inputText.trim() ? T.primary : T.primaryDim,
                  border: 'none',
                  color: T.white,
                  cursor: inputText.trim() ? 'pointer' : 'default',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14,
                  opacity: inputText.trim() ? 1 : 0.4,
                }}
              >
                ➤
              </motion.button>
            </div>
          </div>

          {/* Status Bar */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '5px 14px',
            borderTop: `1px solid ${T.white04}`,
            fontSize: 9, color: T.textDim,
          }}>
            <span>🧠 {brainData.length || 5}</span>
            <span>⚡ {vitality}%</span>
            <span>📡 {signalCount}</span>
            {currentRoute && currentRoute.intent !== 'default' && (
              <span style={{ color: T.primary, fontWeight: 600 }}>
                {currentRoute.icon} {currentRoute.labelAr}
              </span>
            )}
          </div>
        </div>

        {/* ═══════ Panel 2: Context Screen (40%) ═══════ */}
        <div ref={contextPanelRef} className="supermind-context-panel" style={{
          width: '40%',
          display: 'flex', flexDirection: 'column',
          background: T.bg,
          borderLeft: `1px solid ${T.white08}`,
          overflow: 'hidden',
        }}>
          <ContextScreen
            activeScreen={activeScreen}
            animation={screenAnimation}
            screenProps={screenPropsData}
            onBack={handleScreenBack}
          />
        </div>

        {/* ═══════ Panel 3: Brain Network (30%) ═══════ */}
        <div ref={brainPanelRef} className="supermind-brain-panel" style={{
          width: '30%',
          display: 'flex', flexDirection: 'column',
          background: T.bg,
          overflow: 'hidden',
        }}>
          {/* Brain Network Header */}
          <div style={{
            padding: '10px 14px',
            borderBottom: `1px solid ${T.white08}`,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: T.white }}>🧠 شبكة الأدمغة</span>
            <span style={{ fontSize: 9, color: T.textDim, flex: 1 }}>ثلاثي الأبعاد</span>
            <div style={{
              fontSize: 8, color: T.accent,
              background: T.accentDim,
              padding: '2px 6px',
              borderRadius: 4,
            }}>
              {activeBrains.length} نشط
            </div>
          </div>

          {/* 3D Brain Network */}
          <div style={{ flex: 1, position: 'relative' }}>
            <BrainNetwork
              activeBrains={activeBrains}
              brainConfidences={brainConfidences}
              onBrainClick={handleBrainClick}
              vitality={vitality}
            />
          </div>

          {/* Brain Status Mini Cards */}
          <div style={{
            padding: '6px 10px',
            borderTop: `1px solid ${T.white08}`,
            display: 'flex', flexDirection: 'column', gap: 3,
            maxHeight: 120,
            overflowY: 'auto',
          }}>
            {brainData.length > 0 ? brainData.map(brain => {
              const isActive = activeBrains.includes(brain.id);
              const colors: Record<string, string> = {
                neural: T.brainNeural,
                causal: T.brainCausal,
                symbolic: T.brainSymbolic,
                bayesian: T.brainBayesian,
                world_model: T.brainWorldModel,
              };
              const color = colors[brain.id] || T.primary;
              return (
                <div key={brain.id} style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '3px 6px',
                  background: isActive ? `${color}10` : 'transparent',
                  borderRadius: 4,
                  border: isActive ? `1px solid ${color}30` : '1px solid transparent',
                }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: color,
                    opacity: isActive ? 1 : 0.4,
                  }} />
                  <span style={{
                    fontSize: 9, color: isActive ? color : T.textDim,
                    fontWeight: isActive ? 600 : 400, flex: 1,
                  }}>
                    {brain.nameAr || brain.name}
                  </span>
                  {brain.confidence > 0 && (
                    <span style={{ fontSize: 8, color: T.textDim }}>
                      {Math.round(brain.confidence * 100)}%
                    </span>
                  )}
                </div>
              );
            }) : (
              <div style={{ fontSize: 9, color: T.textDim, textAlign: 'center', padding: 8 }}>
                في انتظار بيانات الأدمغة...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ─── Bottom Bar ─── */}
      <div style={{
        height: 32, display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        background: T.chatBg,
        borderTop: `1px solid ${T.white08}`,
        fontSize: 9, color: T.textDim,
      }}>
        <div style={{ display: 'flex', gap: 12 }}>
          <span>مأمون v61 — العقل الخارق</span>
          <span style={{ color: isConscious ? T.accent : T.red }}>
            {isConscious ? '● واعي' : '○ نائم'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <span>⚡ حيوية: {vitality}%</span>
          <span>🧠 وعي: {Math.round(consciousness * 100)}%</span>
          <span>📡 إشارات: {signalCount}</span>
        </div>
      </div>
    </div>
  );
}
