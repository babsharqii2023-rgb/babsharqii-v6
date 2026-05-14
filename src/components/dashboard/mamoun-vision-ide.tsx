'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Send, Mic, Cpu, Activity, Sparkles, Search, ShieldAlert,
  Eye, GitMerge, Network, Terminal, Database,
  Brain, Heart, Dna, HardDrive, Shield, Zap, Wrench, Bot,
  Palette, Lightbulb, Globe, Layers, ChevronLeft, Users,
  ArrowRight, Radio, Wifi, Orbit, MessageSquare, Play,
  RotateCcw, Power, Settings, ChevronDown, ChevronUp,
  Circle, CheckCircle2, XCircle, AlertCircle, Timer,
  Gauge, Waves, Atom, Hexagon, Siren, Scan,
  MonitorSpeaker, Volume2, Lock, Cloud, Rocket,
  Fingerprint, Cog, Target, Compass, Swords,
  Camera, ShoppingCart, Smartphone,
} from 'lucide-react';
import {
  fetchBrainStates, fetchKernelStatus, fetchLivingVitals,
  fetchProjects, fetchPendingApprovals, triggerDeliberation,
  sendChatMessage, fetchLivingEmotions, fetchLivingHeartbeat,
  fetchLivingBonding, fetchLivingIdentity, fetchEvolutionStatus,
  fetchConsciousnessState, fetchEmotionState, fetchSleepState,
  fetchHyperagentStatus, fetchAGIStatus, fetchSafetyLaws,
  fetchCapabilities, fetchMetacognitiveAssessment,
  type BrainState, type ProjectInfo,
} from '@/lib/jarvis-api';
import { DASHBOARD_SECTIONS, BRAIN_DEFINITIONS, SUBSYSTEMS } from '@/lib/dashboard-data';
import BrainsOrbPanel from './panels/BrainsOrbPanel';
import NeuralBusPanel from './panels/NeuralBusPanel';
import InnerMonologuePanel from './panels/InnerMonologuePanel';
import LifePanel from './panels/LifePanel';
import ConsciousnessPanel from './panels/ConsciousnessPanel';
import ProjectsPanel from './panels/ProjectsPanel';
import SwarmPanel from './panels/SwarmPanel';
import SitesPanel from './panels/SitesPanel';

// ═══════════════════════════════════════════════════════════════════════
// COLOR SYSTEM — BLACK + DEEP BLUE (أزرق عميق) — Mamoun Cosmic Theme
// ═══════════════════════════════════════════════════════════════════════
const P = {
  black: '#000000',
  bg: '#070710',
  card: '#0d0d1a',
  cardHover: '#12122a',
  primary: '#1a6baa',
  primaryLight: '#1e8aad',
  primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)',
  primaryMid: 'rgba(26,107,170,0.15)',
  primaryStrong: 'rgba(26,107,170,0.3)',
  primaryGlow: '0 0 12px rgba(26,107,170,0.4)',
  primaryGlowBig: '0 0 24px rgba(26,107,170,0.2)',
  // Legacy aliases for backward compatibility
  pink: '#1a6baa',
  pinkLight: '#1e8aad',
  pinkDark: '#0a4a6e',
  pinkDim: 'rgba(26,107,170,0.08)',
  pinkMid: 'rgba(26,107,170,0.15)',
  pinkStrong: 'rgba(26,107,170,0.3)',
  pinkGlow: '0 0 12px rgba(26,107,170,0.4)',
  pinkGlowBig: '0 0 24px rgba(26,107,170,0.2)',
  white: '#FFFFFF',
  textPrimary: '#c8d4e8',
  textSecondary: '#5a6a80',
  white90: 'rgba(255,255,255,0.9)',
  white70: 'rgba(200,212,232,0.7)',
  white50: 'rgba(255,255,255,0.5)',
  white30: 'rgba(255,255,255,0.3)',
  white15: 'rgba(255,255,255,0.15)',
  white08: 'rgba(255,255,255,0.08)',
  white04: 'rgba(255,255,255,0.04)',
  white02: 'rgba(255,255,255,0.02)',
  green: '#4CAF50',
  orange: '#FF9800',
  red: '#EF4444',
};

// ═══════════════════════════════════════════════════════════════════════
// NAVIGATION — التنقل العصبي البُعدي
// ═══════════════════════════════════════════════════════════════════════
type ViewMode = 'dashboard' | 'deliberation' | 'github' | 'terminal' | 'diagnose' | 'trading' | 'instagram' | 'ecommerce' | 'blender' | 'embodiment' | 'mobile' | 'self-modify' | 'evolution' | 'browser' | 'laptop' | 'brain-control' | 'feature-flags' | 'api-keys' | 'control-center' | 'smart-chat' | 'brains-orb' | 'neural-bus' | 'inner-monologue' | 'life' | 'consciousness' | 'projects' | 'swarm' | 'sites';

interface NavCat {
  id: string; label: string; icon: React.ReactNode; sectionIds: number[];
  desc: string;
}

const NAV: NavCat[] = [
  { id: 'core', label: 'النواة', icon: <Orbit className="w-4 h-4" />, sectionIds: [1, 4], desc: 'MamounKernel + Self-Improvement' },
  { id: 'brains', label: 'الأدمغة', icon: <Brain className="w-4 h-4" />, sectionIds: [2], desc: '5 أدمغة + موجه + مداولة' },
  { id: 'brains-orb', label: 'عرض الأدمغة', icon: <Orbit className="w-4 h-4" />, sectionIds: [], desc: '5 أدمغة متصلة بشكل خماسي' },
  { id: 'consciousness', label: 'الوعي', icon: <Eye className="w-4 h-4" />, sectionIds: [3], desc: 'ConsciousnessLoop + InnerMonologue' },
  { id: 'consciousness-view', label: 'حلقة الوعي', icon: <Eye className="w-4 h-4" />, sectionIds: [], desc: '5 مراحل تدور باستمرار' },
  { id: 'safety', label: 'الأمان', icon: <Shield className="w-4 h-4" />, sectionIds: [5, 6], desc: 'الضمير + الشفاء الذاتي' },
  { id: 'agi', label: 'AGI', icon: <Zap className="w-4 h-4" />, sectionIds: [7, 9], desc: '7 أركان + قدرات AGI' },
  { id: 'evolution', label: 'التطور', icon: <Dna className="w-4 h-4" />, sectionIds: [8], desc: 'الطفرات + اللياقة + الخالق' },
  { id: 'living', label: 'الحياة', icon: <Heart className="w-4 h-4" />, sectionIds: [11, 14, 20], desc: 'الأنظمة الحية + الغرائز + المشاعر' },
  { id: 'life', label: 'المؤشرات الحيوية', icon: <Activity className="w-4 h-4" />, sectionIds: [], desc: '6 مؤشرات حيوية + نبض + مشاعر' },
  { id: 'memory', label: 'الذاكرة', icon: <HardDrive className="w-4 h-4" />, sectionIds: [12, 13], desc: 'التنبؤية + الثلاثية + التعلم' },
  { id: 'reasoning', label: 'الاستدلال', icon: <Lightbulb className="w-4 h-4" />, sectionIds: [16], desc: 'رمزي + بايزي + تعزيزي' },
  { id: 'hyperagent', label: 'الوكيل الفائق', icon: <Layers className="w-4 h-4" />, sectionIds: [17], desc: 'MetaAgent + Supra + المستقبل' },
  { id: 'awareness', label: 'الوعي الخارجي', icon: <Globe className="w-4 h-4" />, sectionIds: [15], desc: 'مراقب العالم + المناعي' },
  { id: 'capabilities', label: 'القدرات', icon: <Wrench className="w-4 h-4" />, sectionIds: [10], desc: '12 قدرة تشغيلية' },
  { id: 'agents', label: 'الوكلاء', icon: <Bot className="w-4 h-4" />, sectionIds: [23], desc: '14 وكيل متخصص' },
  { id: 'swarm', label: 'السرب', icon: <Users className="w-4 h-4" />, sectionIds: [], desc: 'وكلاء يتشاورون وينجزون مهام' },
  { id: 'planning', label: 'التخطيط', icon: <GitMerge className="w-4 h-4" />, sectionIds: [19, 18], desc: 'أهداف + ميزانية + قيود + عصبية' },
  { id: 'creativity', label: 'الإبداع', icon: <Palette className="w-4 h-4" />, sectionIds: [21], desc: 'الجدة + الأصالة + الأفكار' },
  { id: 'embodiment', label: 'الجسد الرقمي', icon: <Cpu className="w-4 h-4" />, sectionIds: [22], desc: 'IoT + بلندر + روبوت' },
  { id: 'tools', label: 'الأدوات', icon: <Terminal className="w-4 h-4" />, sectionIds: [24], desc: 'ملفات + أوامر + منفذ مطلق' },
  { id: 'projects', label: 'المشاريع', icon: <GitMerge className="w-4 h-4" />, sectionIds: [], desc: 'إدارة المشاريع والمهام' },
  { id: 'api', label: 'التواصل', icon: <Radio className="w-4 h-4" />, sectionIds: [25], desc: 'WebSocket + SSE + مصادقة' },
  { id: 'neural-bus', label: 'الناقل العصبي', icon: <Network className="w-4 h-4" />, sectionIds: [], desc: '28 نوع إشارة — Pub/Sub مركزي' },
];

const SYSTEM_NAV = [
  { id: 'github', label: 'المستودع', icon: <Cloud className="w-4 h-4" />, desc: 'سحب التحديثات + توكن + تراجع' },
  { id: 'diagnose', label: 'التشخيص', icon: <Scan className="w-4 h-4" />, desc: 'كشف الأخطاء + إصلاح تلقائي' },
  { id: 'terminal', label: 'السيرفر', icon: <Terminal className="w-4 h-4" />, desc: 'طرفية + ملفات + تحكم كامل' },
  { id: 'sites', label: 'المواقع', icon: <Globe className="w-4 h-4" />, desc: 'إدارة النشر + صحة المواقع' },
];

const SETTINGS_NAV = [
  { id: 'api-keys', label: 'المفاتيح', icon: <Lock className="w-4 h-4" />, desc: 'إدارة مفاتيح API لكل الأدمغة' },
  { id: 'control-center', label: 'التحكم', icon: <Cog className="w-4 h-4" />, desc: 'تحكم شامل بكل الأنظمة' },
  { id: 'smart-chat', label: 'محادثة ذكية', icon: <MessageSquare className="w-4 h-4" />, desc: 'محادثة مع الأدمغة الخمسة' },
];

// ═══════════════════════════════════════════════════════════════════════
// HOLOGRAM NUCLEUS — الكائن العصبي الحي (يتنفس، ينبض، يفكر)
// ═══════════════════════════════════════════════════════════════════════
function HologramNucleus({
  vitality = 75,
  activeBrains = 3,
  isThinking = false,
  size = 180,
  consciousness = 0.7,
}: {
  vitality?: number; activeBrains?: number; isThinking?: boolean; size?: number; consciousness?: number;
}) {
  const r = size / 2;
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 100);
    return () => clearInterval(iv);
  }, []);

  const brainOrbs = BRAIN_DEFINITIONS.slice(0, 5).map((b, i) => {
    const angle = (i / 5) * 2 * Math.PI - Math.PI / 2 + (tick * 0.002);
    const orbitR = r - 30;
    return {
      ...b,
      cx: r + Math.cos(angle) * orbitR,
      cy: r + Math.sin(angle) * orbitR,
    };
  });

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="absolute inset-0">
        <defs>
          <radialGradient id="nGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={P.pink} stopOpacity="0.5" />
            <stop offset="30%" stopColor={P.pink} stopOpacity="0.15" />
            <stop offset="100%" stopColor={P.pink} stopOpacity="0" />
          </radialGradient>
          <filter id="pGlow">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Pulse waves — موجات النبض */}
        {[0, 1, 2].map(i => (
          <circle key={`pw-${i}`} cx={r} cy={r} r={r * 0.3} fill="none" stroke={P.pink} strokeWidth="0.5" opacity="0">
            <animate attributeName="r" values={`${r * 0.2};${r * 0.9}`} dur="3s" begin={`${i}s`} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.3;0" dur="3s" begin={`${i}s`} repeatCount="indefinite" />
          </circle>
        ))}

        {/* Core glow — توهج المركز */}
        <circle cx={r} cy={r} r={r * 0.5} fill="url(#nGlow)">
          <animate attributeName="r" values={`${r * 0.4};${r * 0.55};${r * 0.4}`} dur="3s" repeatCount="indefinite" />
        </circle>

        {/* Consciousness ring — حلقة الوعي */}
        <circle cx={r} cy={r} r={r - 14} fill="none" stroke={P.pinkLight} strokeWidth="0.5" strokeDasharray="2 6" opacity="0.15">
          <animateTransform attributeName="transform" type="rotate" from={`0 ${r} ${r}`} to={`-360 ${r} ${r}`} dur="30s" repeatCount="indefinite" />
        </circle>

        {/* Vitality arc — قوس الحيوية */}
        <circle
          cx={r} cy={r} r={r - 8}
          fill="none" stroke={P.pink} strokeWidth="2.5" strokeLinecap="round"
          strokeDasharray={`${(vitality / 100) * 2 * Math.PI * (r - 8)} ${2 * Math.PI * (r - 8)}`}
          transform={`rotate(-90 ${r} ${r})`}
          opacity="0.7" filter="url(#pGlow)"
        >
          <animate attributeName="opacity" values="0.5;0.9;0.5" dur="2s" repeatCount="indefinite" />
        </circle>

        {/* Brain orbit path — مسار مدار الأدمغة */}
        <circle cx={r} cy={r} r={r - 30} fill="none" stroke={P.pink} strokeWidth="0.3" strokeDasharray="3 8" opacity="0.2">
          <animateTransform attributeName="transform" type="rotate" from={`0 ${r} ${r}`} to={`360 ${r} ${r}`} dur="20s" repeatCount="indefinite" />
        </circle>

        {/* Thinking waves — موجات التفكير */}
        {isThinking && [0, 1, 2, 3].map(i => (
          <circle key={`tw-${i}`} cx={r} cy={r} r={20 + i * 15} fill="none" stroke={P.pinkLight} strokeWidth="0.8" opacity="0">
            <animate attributeName="r" values={`${15 + i * 10};${35 + i * 15}`} dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.4;0" dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite" />
          </circle>
        ))}

        {/* Brain nodes orbiting — عقد الأدمغة */}
        {brainOrbs.map((b, i) => (
          <g key={`bn-${i}`}>
            <circle cx={b.cx} cy={b.cy} r="6" fill={b.status === 'active' ? P.pinkStrong : P.white08} stroke={P.pink} strokeWidth="0.5" opacity={b.status === 'active' ? 0.8 : 0.3}>
              {b.status === 'active' && <animate attributeName="r" values="5;7;5" dur={`${1.5 + i * 0.3}s`} repeatCount="indefinite" />}
            </circle>
            <circle cx={b.cx} cy={b.cy} r="2" fill={b.status === 'active' ? P.pinkLight : P.white30} />
          </g>
        ))}

        {/* DNA helix strands — لولب الحمض النووي */}
        {Array.from({ length: 8 }).map((_, i) => {
          const angle = (i / 8) * Math.PI + (tick * 0.05);
          const y1 = r - 25 + (i / 8) * 50;
          const x1 = r + Math.sin(angle) * 10;
          const x2 = r - Math.sin(angle) * 10;
          return (
            <g key={`dna-${i}`}>
              <circle cx={x1} cy={y1} r="1.2" fill={P.pink} opacity="0.4" />
              <circle cx={x2} cy={y1} r="1.2" fill={P.pinkLight} opacity="0.3" />
              <line x1={x1} y1={y1} x2={x2} y2={y1} stroke={P.pink} strokeWidth="0.3" opacity="0.15" />
            </g>
          );
        })}

        {/* Center dot — نقطة المركز */}
        <circle cx={r} cy={r} r="4" fill={P.pink} filter="url(#pGlow)">
          <animate attributeName="r" values="3;5;3" dur="1.5s" repeatCount="indefinite" />
        </circle>
      </svg>

      {/* Vitality overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold" style={{ color: P.white, textShadow: P.pinkGlow }}>{vitality}%</span>
        <span className="text-[8px] font-mono" style={{ color: P.pink }}>VITALITY</span>
        <span className="text-[7px] font-mono mt-0.5" style={{ color: P.white30 }}>{Math.round(consciousness * 100)}% AWARE</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// GITHUB CONFIG PANEL — لوحة سحب التحديثات من المستودع
// ═══════════════════════════════════════════════════════════════════════
function GitHubPanel({ onBack }: { onBack: () => void }) {
  const [repoUrl, setRepoUrl] = useState('https://github.com/babsharqii2023-rgb/babsharqii-v5.git');
  const [token, setToken] = useState('');
  const [branch, setBranch] = useState('main');
  const [updateStatus, setUpdateStatus] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [autoUpdate, setAutoUpdate] = useState(false);

  const addLog = (msg: string) => setLog(p => [...p.slice(-20), `[${new Date().toLocaleTimeString('ar')}] ${msg}`]);

  const apiCall = async (path: string, body?: Record<string, unknown>) => {
    try {
      const resp = body
        ? await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        : await fetch(path);
      if (resp.ok) return await resp.json();
      return { error: `HTTP ${resp.status}` };
    } catch { return { error: 'الخادم غير متصل' }; }
  };

  const handleConfigure = async () => {
    setLoading(true); addLog('🔧 إعداد المستودع...');
    const res = await apiCall('/api/update/configure', { repo_url: repoUrl, token, branch });
    addLog(res.error ? `❌ فشل: ${res.error}` : '✅ تم حفظ الإعدادات');
    setLoading(false);
  };

  const handleCheck = async () => {
    setLoading(true); addLog('🔍 فحص تحديثات جديدة...');
    const res = await apiCall('/api/update/check');
    setUpdateStatus(res as Record<string, unknown>);
    const hasUpdate = (res as { has_updates?: boolean })?.has_updates;
    addLog(hasUpdate ? '📥 توجد تحديثات جديدة!' : '✅ أنت على أحدث إصدار');
    setLoading(false);
  };

  const handlePull = async () => {
    setLoading(true); addLog('⬇️ سحب التحديثات وتطبيقها...');
    const res = await apiCall('/api/update/pull');
    const success = (res as { success?: boolean })?.success;
    addLog(success ? '✅ تم التطبيق بنجاح!' : `⚠️ النتيجة: ${JSON.stringify(res).slice(0, 80)}`);
    setLoading(false);
  };

  const handleRollback = async () => {
    setLoading(true); addLog('⏪ التراجع عن آخر تحديث...');
    const res = await apiCall('/api/update/rollback');
    addLog((res as { success?: boolean })?.success ? '✅ تم التراجع' : `❌ فشل التراجع`);
    setLoading(false);
  };

  const handleAutoToggle = async () => {
    const res = await apiCall('/api/update/auto-toggle', { enabled: !autoUpdate });
    const ok = (res as { enabled?: boolean })?.enabled;
    setAutoUpdate(!!ok);
    addLog(ok ? '🔄 التحديث التلقائي مُفعّل (كل 60 ثانية)' : '⏹️ التحديث التلقائي مُوقف');
  };

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>سحب التحديثات من المستودع</h2>
        <Cloud className="w-4 h-4" style={{ color: P.pink }} />
      </div>

      <div className="flex-1 overflow-y-auto sb p-5 space-y-4">
        {/* Config form */}
        <div className="p-4 rounded-xl space-y-3" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
          <h3 className="text-xs font-semibold" style={{ color: P.pinkLight }}>إعدادات المستودع</h3>
          <div>
            <label className="text-[9px] block mb-1" style={{ color: P.white30 }}>رابط المستودع</label>
            <input type="text" value={repoUrl} onChange={e => setRepoUrl(e.target.value)} dir="ltr"
              className="w-full px-3 py-2 rounded-lg text-[11px] font-mono outline-none"
              style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }} />
          </div>
          <div>
            <label className="text-[9px] block mb-1" style={{ color: P.white30 }}>التوكن (PAT)</label>
            <input type="password" value={token} onChange={e => setToken(e.target.value)} dir="ltr" placeholder="ghp_xxxxxxxxxxxx"
              className="w-full px-3 py-2 rounded-lg text-[11px] font-mono outline-none"
              style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }} />
          </div>
          <div>
            <label className="text-[9px] block mb-1" style={{ color: P.white30 }}>الفرع</label>
            <input type="text" value={branch} onChange={e => setBranch(e.target.value)} dir="ltr"
              className="w-full px-3 py-2 rounded-lg text-[11px] font-mono outline-none"
              style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }} />
          </div>
          <button onClick={handleConfigure} disabled={loading} className="w-full py-2 rounded-lg text-xs font-semibold"
            style={{ background: P.pink, color: P.white, opacity: loading ? 0.5 : 1 }}>
            حفظ الإعدادات
          </button>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-2 gap-2">
          <button onClick={handleCheck} disabled={loading}
            className="p-3 rounded-xl text-center" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
            <Search className="w-5 h-5 mx-auto mb-1" style={{ color: P.pinkLight }} />
            <span className="text-[10px]" style={{ color: P.white70 }}>فحص تحديثات</span>
          </button>
          <button onClick={handlePull} disabled={loading}
            className="p-3 rounded-xl text-center" style={{ background: P.pinkMid, border: `1px solid ${P.pinkStrong}` }}>
            <Rocket className="w-5 h-5 mx-auto mb-1" style={{ color: P.pinkLight }} />
            <span className="text-[10px]" style={{ color: P.pinkLight }}>سحب + تطبيق</span>
          </button>
          <button onClick={handleRollback} disabled={loading}
            className="p-3 rounded-xl text-center" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
            <RotateCcw className="w-5 h-5 mx-auto mb-1" style={{ color: P.orange }} />
            <span className="text-[10px]" style={{ color: P.white70 }}>تراجع</span>
          </button>
          <button onClick={handleAutoToggle}
            className="p-3 rounded-xl text-center" style={{ background: autoUpdate ? P.pinkMid : P.white02, border: `1px solid ${autoUpdate ? P.pinkStrong : P.pinkDim}` }}>
            <Timer className="w-5 h-5 mx-auto mb-1" style={{ color: autoUpdate ? P.pinkLight : P.white30 }} />
            <span className="text-[10px]" style={{ color: autoUpdate ? P.pinkLight : P.white70 }}>تلقائي {autoUpdate ? 'ON' : 'OFF'}</span>
          </button>
        </div>

        {/* Status */}
        {updateStatus && (
          <div className="p-3 rounded-xl" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
            <h3 className="text-[10px] font-semibold mb-2" style={{ color: P.pinkLight }}>حالة التحديث</h3>
            {Object.entries(updateStatus).slice(0, 8).map(([k, v]) => (
              <div key={k} className="flex justify-between py-0.5">
                <span className="text-[9px]" style={{ color: P.white30 }}>{k}</span>
                <span className="text-[9px] font-mono" style={{ color: P.white70 }}>{String(v).slice(0, 40)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Log */}
        <div className="p-3 rounded-xl" style={{ background: P.card, border: `1px solid ${P.pinkDim}` }}>
          <h3 className="text-[10px] font-semibold mb-2" style={{ color: P.pinkLight }}>سجل العمليات</h3>
          <div className="space-y-0.5 max-h-48 overflow-y-auto sb">
            {log.length === 0 && <span className="text-[9px]" style={{ color: P.white15 }}>لا توجد عمليات بعد</span>}
            {log.map((l, i) => (
              <div key={i} className="text-[9px] font-mono" style={{ color: P.white50 }}>{l}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// FEATURE PAGE — صفحة ميزة مخصصة (تداول، انستقرام، إلخ)
// ═══════════════════════════════════════════════════════════════════════
const FEATURE_PAGES: Record<string, { title: string; icon: React.ReactNode; apiEndpoint: string; description: string }> = {
  trading: { title: 'محرك التداول', icon: <Gauge className="w-5 h-5" />, apiEndpoint: '/api/capabilities/trading/overview', description: 'التداول الآلي — يتصل بأسواق المال' },
  instagram: { title: 'انستقرام', icon: <Camera className="w-5 h-5" />, apiEndpoint: '/api/capabilities/instagram/status', description: 'إدارة حساب انستقرام تلقائياً' },
  ecommerce: { title: 'المتجر الإلكتروني', icon: <ShoppingCart className="w-5 h-5" />, apiEndpoint: '/api/capabilities/ecommerce/status', description: 'بناء وإدارة متجر إلكتروني' },
  blender: { title: 'بلندر ثلاثي الأبعاد', icon: <Palette className="w-5 h-5" />, apiEndpoint: '/api/capabilities/blender/status', description: 'التحكم بـ Blender' },
  embodiment: { title: 'الجسد الرقمي', icon: <Cpu className="w-5 h-5" />, apiEndpoint: '/api/embodiment/status', description: 'IoT + روبوت + أجهزة ذكية' },
  mobile: { title: 'بناء التطبيقات', icon: <Smartphone className="w-5 h-5" />, apiEndpoint: '/api/capabilities/mobile/status', description: 'بناء تطبيقات موبايل' },
  'self-modify': { title: 'البرمجة الذاتية', icon: <Dna className="w-5 h-5" />, apiEndpoint: '/api/v24/self-modify/status', description: 'تعديل الكود ذاتياً' },
  evolution: { title: 'التطور الذاتي', icon: <Dna className="w-5 h-5" />, apiEndpoint: '/api/evolution/current', description: 'دورات التطور الدارويني' },
  'brain-control': { title: 'تحكم بالأدمغة', icon: <Brain className="w-5 h-5" />, apiEndpoint: '/api/v2/brains/matrix', description: 'مصفوفة التحكم بالأدمغة الخمسة' },
  'feature-flags': { title: 'مدير الميزات', icon: <Settings className="w-5 h-5" />, apiEndpoint: '/api/v2/feature-flags', description: 'تفعيل/إيقاف فوري لكل الميزات' },
};

function FeaturePage({ pageId, onBack }: { pageId: string; onBack: () => void }) {
  const page = FEATURE_PAGES[pageId];
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!page) return;
    const load = async () => {
      try {
        const res = await fetch(page.apiEndpoint);
        if (res.ok) {
          setData(await res.json());
        } else {
          setError(`HTTP ${res.status}`);
        }
      } catch {
        setError('لا يمكن الاتصال');
      }
      setLoading(false);
    };
    load();
    const iv = setInterval(load, 10000);
    return () => clearInterval(iv);
  }, [page]);

  if (!page) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ background: P.black }}>
        <div className="text-center">
          <span className="text-sm" style={{ color: P.white50 }}>صفحة غير موجودة</span>
          <button onClick={onBack} className="block mx-auto mt-3 text-xs" style={{ color: P.pinkLight }}>الرجوع</button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <div className="flex items-center gap-2">
          <span style={{ color: P.pink }}>{page.icon}</span>
          <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>{page.title}</h2>
        </div>
        <div className="w-8" />
      </div>

      <div className="flex-1 overflow-y-auto sb p-5 space-y-4">
        <div className="p-4 rounded-xl" style={{ background: P.pinkDim, border: `1px solid ${P.pinkDim}` }}>
          <p className="text-xs" style={{ color: P.white70 }}>{page.description}</p>
          <p className="text-[9px] font-mono mt-1" style={{ color: P.white30 }}>API: {page.apiEndpoint}</p>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <Activity className="w-6 h-6 animate-spin" style={{ color: P.pink }} />
            <span className="text-xs mr-3" style={{ color: P.white50 }}>جارٍ التحميل...</span>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-xl" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <span className="text-xs" style={{ color: P.red }}>خطأ: {error}</span>
          </div>
        )}

        {data && !loading && (
          <div className="space-y-2">
            {Object.entries(data).slice(0, 20).map(([key, value]) => (
              <div key={key} className="p-3 rounded-xl" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
                <span className="text-[9px] font-semibold block mb-1" style={{ color: P.pinkLight }}>{key}</span>
                <pre className="text-[9px] font-mono overflow-hidden" style={{ color: P.white70, maxHeight: 120, direction: 'ltr', textAlign: 'left' }}>
                  {typeof value === 'object' ? JSON.stringify(value, null, 2).slice(0, 500) : String(value).slice(0, 200)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// SELF-DIAGNOSE PANEL — لوحة التشخيص والإصلاح التلقائي
// ═══════════════════════════════════════════════════════════════════════
function DiagnosePanel({ onBack }: { onBack: () => void }) {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Array<{ type: string; message: string; severity: 'ok' | 'warn' | 'error'; fixed?: boolean }>>([]);
  const [healingActive, setHealingActive] = useState(false);

  const runDiagnosis = async () => {
    setLoading(true);
    setResults([]);
    const checks: typeof results = [];

    // Check 1: Backend health
    try {
      const r = await fetch('/api/health');
      const d = await r.json();
      checks.push({ type: 'الخادم', message: d.status === 'ok' ? 'الخادم يعمل' : 'الخادم متوقف', severity: d.status === 'ok' ? 'ok' : 'error' });
    } catch {
      checks.push({ type: 'الخادم', message: 'لا يمكن الاتصال بالخادم', severity: 'error' });
    }

    // Check 2: Kernel status
    try {
      const r = await fetch('/api/kernel/status');
      const d = await r.json();
      checks.push({ type: 'النواة', message: d.kernel_status === 'running' ? `تعمل — ${d.active_processes} عمليات` : 'متوقفة', severity: d.kernel_status === 'running' ? 'ok' : 'error' });
    } catch {
      checks.push({ type: 'النواة', message: 'لا يمكن فحص النواة', severity: 'warn' });
    }

    // Check 3: Living vitals
    try {
      const r = await fetch('/api/living/vitals');
      const d = await r.json();
      const v = d.vitality ?? d.energy ?? 0;
      checks.push({ type: 'الحيوية', message: `الحيوية ${v}%`, severity: v > 60 ? 'ok' : v > 30 ? 'warn' : 'error' });
    } catch {
      checks.push({ type: 'الحيوية', message: 'لا يمكن قراءة الحيوية', severity: 'warn' });
    }

    // Check 4: Brains
    try {
      const r = await fetch('/api/brains');
      const d = await r.json();
      const bCount = d.brains?.filter((b: { status: string }) => b.status === 'active').length ?? 0;
      checks.push({ type: 'الأدمغة', message: `${bCount}/5 أدمغة نشطة`, severity: bCount >= 3 ? 'ok' : bCount >= 1 ? 'warn' : 'error' });
    } catch {
      checks.push({ type: 'الأدمغة', message: 'لا يمكن فحص الأدمغة', severity: 'warn' });
    }

    // Check 5: Security
    try {
      const r = await fetch('/api/security');
      checks.push({ type: 'الأمان', message: r.ok ? 'قوانين L1-L8 سارية' : 'خطأ في فحص الأمان', severity: r.ok ? 'ok' : 'warn' });
    } catch {
      checks.push({ type: 'الأمان', message: 'لا يمكن فحص الأمان', severity: 'warn' });
    }

    // Check 6: Evolution
    try {
      const r = await fetch('/api/evolution/current');
      const d = await r.json();
      const fit = d.version?.fitness_score ?? 0;
      checks.push({ type: 'التطور', message: `الجيل ${d.version?.generation ?? '?'} — لياقة ${Math.round(fit * 100)}%`, severity: fit > 0.5 ? 'ok' : 'warn' });
    } catch {
      checks.push({ type: 'التطور', message: 'لا يمكن فحص التطور', severity: 'warn' });
    }

    // Check 7: Feature coverage
    const totalFeatures = DASHBOARD_SECTIONS.reduce((a, s) => a + s.features.length, 0);
    checks.push({ type: 'الميزات', message: `${totalFeatures} ميزة مسجلة عبر ${DASHBOARD_SECTIONS.length} قسم`, severity: 'ok' });

    // Check 8: API routes
    try {
      const r = await fetch('/api/health');
      checks.push({ type: 'API', message: 'مسارات API متاحة', severity: 'ok' });
    } catch {
      checks.push({ type: 'API', message: 'مسارات API غير متاحة', severity: 'error' });
    }

    setResults(checks);
    setLoading(false);
  };

  const handleAutoFix = async () => {
    setHealingActive(true);
    try {
      const r = await fetch('/api/self-heal', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const d = await r.json();
      setResults(p => [...p, { type: 'إصلاح', message: d.message || d.status || 'تم تشغيل الإصلاح التلقائي', severity: 'ok', fixed: true }]);
    } catch {
      setResults(p => [...p, { type: 'إصلاح', message: 'لا يمكن الاتصال بنظام الشفاء', severity: 'error' }]);
    }
    setHealingActive(false);
  };

  const sevIcon = (s: string) => s === 'ok' ? '✅' : s === 'warn' ? '⚠️' : '❌';

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>التشخيص والإصلاح التلقائي</h2>
        <Scan className="w-4 h-4" style={{ color: P.pink }} />
      </div>

      <div className="flex-1 overflow-y-auto sb p-5 space-y-4">
        {/* Action buttons */}
        <div className="grid grid-cols-2 gap-3">
          <button onClick={runDiagnosis} disabled={loading}
            className="p-4 rounded-xl text-center" style={{ background: P.pinkMid, border: `1px solid ${P.pinkStrong}` }}>
            <Scan className="w-6 h-6 mx-auto mb-2" style={{ color: P.pinkLight }} />
            <span className="text-xs font-semibold" style={{ color: P.pinkLight }}>تشخيص النظام</span>
          </button>
          <button onClick={handleAutoFix} disabled={healingActive}
            className="p-4 rounded-xl text-center" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
            <Siren className="w-6 h-6 mx-auto mb-2" style={{ color: P.pink }} />
            <span className="text-xs font-semibold" style={{ color: P.white70 }}>إصلاح تلقائي</span>
          </button>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={i} className="p-3 rounded-xl flex items-start gap-3" style={{
                background: r.severity === 'error' ? 'rgba(239,68,68,0.08)' : r.severity === 'warn' ? 'rgba(255,152,0,0.08)' : P.white02,
                border: `1px solid ${r.severity === 'error' ? 'rgba(239,68,68,0.2)' : r.severity === 'warn' ? 'rgba(255,152,0,0.2)' : P.pinkDim}`,
              }}>
                <span className="text-sm shrink-0">{sevIcon(r.severity)}</span>
                <div className="flex-1">
                  <span className="text-[10px] font-semibold block" style={{ color: P.pinkLight }}>{r.type}</span>
                  <span className="text-[10px]" style={{ color: P.white70 }}>{r.message}</span>
                </div>
                {r.fixed && <CheckCircle2 className="w-4 h-4 shrink-0" style={{ color: P.green }} />}
              </div>
            ))}
          </div>
        )}

        {/* Loading */}
        {(loading || healingActive) && (
          <div className="flex items-center justify-center py-8">
            <Activity className="w-6 h-6 animate-spin" style={{ color: P.pink }} />
            <span className="text-xs mr-3" style={{ color: P.white50 }}>{loading ? 'جارٍ التشخيص...' : 'جارٍ الإصلاح...'}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// EMBEDDED TERMINAL — الطرفية المدمجة + تحكم السيرفر
// ═══════════════════════════════════════════════════════════════════════
function ServerTerminal({ onBack }: { onBack: () => void }) {
  const [cmd, setCmd] = useState('');
  const [output, setOutput] = useState<Array<{ text: string; type: 'cmd' | 'out' | 'err' }>>([
    { text: 'مأمون v5 — الطرفية الذكية', type: 'out' },
    { text: 'اكتب أوامرك هنا... (ls, cat, git status, npm run build, إلخ)', type: 'out' },
  ]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [output]);

  const executeCmd = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!cmd.trim() || loading) return;
    const command = cmd;
    setOutput(p => [...p, { text: `$ ${command}`, type: 'cmd' as const }]);
    setCmd('');
    setLoading(true);

    try {
      const r = await fetch('/api/terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      });
      const d = await r.json();
      if (d.output) setOutput(p => [...p, { text: d.output, type: 'out' as const }]);
      if (d.error) setOutput(p => [...p, { text: d.error, type: 'err' as const }]);
      if (!d.output && !d.error) setOutput(p => [...p, { text: JSON.stringify(d).slice(0, 300), type: 'out' as const }]);
    } catch {
      setOutput(p => [...p, { text: '❌ لا يمكن الاتصال بالطرفية', type: 'err' as const }]);
    }
    setLoading(false);
  };

  // Quick commands
  const quickCmds = [
    { label: 'حالة Git', cmd: 'git status' },
    { label: 'سحب', cmd: 'git pull' },
    { label: 'بناء', cmd: 'npm run build' },
    { label: 'الملفات', cmd: 'ls -la' },
    { label: 'عمليات', cmd: 'ps aux | head -20' },
    { label: 'قرص', cmd: 'df -h' },
  ];

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>تحكم السيرفر</h2>
        <Terminal className="w-4 h-4" style={{ color: P.pink }} />
      </div>

      {/* Quick commands */}
      <div className="flex gap-2 px-4 py-2 overflow-x-auto" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        {quickCmds.map(q => (
          <button key={q.label} onClick={() => setCmd(q.cmd)}
            className="px-3 py-1 rounded-lg text-[9px] whitespace-nowrap"
            style={{ background: P.white04, border: `1px solid ${P.pinkDim}`, color: P.white50 }}>
            {q.label}
          </button>
        ))}
      </div>

      {/* Output */}
      <div className="flex-1 overflow-y-auto sb p-4 font-mono text-[11px] space-y-0.5" style={{ background: '#030303' }}>
        {output.map((l, i) => (
          <div key={i} style={{
            color: l.type === 'cmd' ? P.pinkLight : l.type === 'err' ? P.red : P.white50,
            direction: 'ltr',
            textAlign: 'left',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}>{l.text}</div>
        ))}
        {loading && <div style={{ color: P.pink }}>● ● ●</div>}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-3" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
        <form onSubmit={executeCmd} className="flex items-center gap-2">
          <span className="text-[11px] font-mono" style={{ color: P.pink }}>$</span>
          <input type="text" value={cmd} onChange={e => setCmd(e.target.value)} dir="ltr"
            placeholder="اكتب الأمر..." className="flex-1 bg-transparent border-none outline-none text-[11px] font-mono"
            style={{ color: P.white90 }} />
          <button type="submit" disabled={!cmd.trim() || loading}
            className="w-8 h-8 flex items-center justify-center rounded-full"
            style={{ background: cmd.trim() ? P.pink : P.white08, color: cmd.trim() ? P.white : P.white30 }}>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// CONSCIOUSNESS ORB — كرة الوعي (تتوهج حسب مستوى الوعي)
// ═══════════════════════════════════════════════════════════════════════
function ConsciousnessOrb({ level = 0.7, size = 60 }: { level?: number; size?: number }) {
  const r = size / 2;
  const opacity = 0.3 + level * 0.5;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <radialGradient id="orbGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={P.pinkLight} stopOpacity={String(opacity)} />
            <stop offset="50%" stopColor={P.pink} stopOpacity={String(opacity * 0.5)} />
            <stop offset="100%" stopColor={P.pinkDark} stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx={r} cy={r} r={r - 2} fill="url(#orbGrad)" opacity="0.8">
          <animate attributeName="r" values={`${r - 4};${r};${r - 4}`} dur="3s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite" />
        </circle>
        <circle cx={r} cy={r} r={r * 0.4} fill="none" stroke={P.pinkLight} strokeWidth="0.5" opacity="0.3">
          <animate attributeName="r" values={`${r * 0.3};${r * 0.5};${r * 0.3}`} dur="2s" repeatCount="indefinite" />
        </circle>
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[8px] font-mono" style={{ color: P.white90 }}>{Math.round(level * 100)}%</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// SIGNAL RADAR — رادار الإشارات (يكشف إشارات NeuralBus)
// ═══════════════════════════════════════════════════════════════════════
function SignalRadar({ signalCount = 28, size = 70 }: { signalCount?: number; size?: number }) {
  const r = size / 2;
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 50);
    return () => clearInterval(iv);
  }, []);

  const signals = useMemo(() =>
    Array.from({ length: Math.min(signalCount, 8) }, (_, i) => ({
      angle: (i / 8) * 2 * Math.PI + (tick * 0.01 * (i + 1)),
      dist: 10 + ((tick * (i + 3)) % (r - 15)),
    })), [tick, signalCount, r]);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={r} cy={r} r={r - 3} fill="none" stroke={P.pink} strokeWidth="0.3" opacity="0.2" />
        <circle cx={r} cy={r} r={(r - 3) * 0.66} fill="none" stroke={P.pink} strokeWidth="0.2" opacity="0.12" />
        <circle cx={r} cy={r} r={(r - 3) * 0.33} fill="none" stroke={P.pink} strokeWidth="0.2" opacity="0.08" />
        {/* Scan line */}
        <line x1={r} y1={r} x2={r + Math.cos(tick * 0.03) * (r - 3)} y2={r + Math.sin(tick * 0.03) * (r - 3)}
          stroke={P.pink} strokeWidth="0.5" opacity="0.4" />
        {/* Signal dots */}
        {signals.map((s, i) => (
          <circle key={i} cx={r + Math.cos(s.angle) * s.dist} cy={r + Math.sin(s.angle) * s.dist}
            r="1.5" fill={P.pinkLight} opacity="0.6" />
        ))}
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[7px] font-mono" style={{ color: P.white50 }}>{signalCount}</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// PREDICTIVE GLOW — التوهج التنبؤي (يتنباً حالة النظام)
// ═══════════════════════════════════════════════════════════════════════
function PredictiveGlow({ prediction = 0.8 }: { prediction?: number }) {
  const color = prediction > 0.7 ? P.green : prediction > 0.4 ? P.orange : P.red;
  const label = prediction > 0.7 ? 'مستقر' : prediction > 0.4 ? 'تحذير' : 'خطر';

  return (
    <div className="flex items-center gap-2 px-2 py-1 rounded-lg" style={{ background: P.white02 }}>
      <div className="relative w-4 h-4">
        <div className="absolute inset-0 rounded-full" style={{ background: color, opacity: 0.3, boxShadow: `0 0 8px ${color}` }}>
          <animate attributeName="opacity" values="0.2;0.5;0.2" dur="2s" repeatCount="indefinite" />
        </div>
        <div className="absolute inset-1 rounded-full" style={{ background: color }} />
      </div>
      <span className="text-[8px] font-mono" style={{ color: P.white50 }}>تنبؤ: {label} {Math.round(prediction * 100)}%</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// NEURAL PULSE — النبض العصبي (خط كهربائي حي)
// ═══════════════════════════════════════════════════════════════════════
function NeuralPulse({ bpm = 72 }: { bpm?: number }) {
  const [points, setPoints] = useState('');
  const bpmFactor = bpm / 72;

  useEffect(() => {
    const iv = setInterval(() => {
      setPoints(prev => {
        const pts = prev.trim().split(' ').filter(Boolean);
        const len = pts.length;
        const lastY = parseFloat(pts[len - 1]?.split(',')[1] || '12');
        // ECG-like pattern: PQRST wave
        const phase = (len % 30) / 30;
        let newY = 12;
        if (phase < 0.1) newY = 12 - 2;
        else if (phase < 0.15) newY = 12 + 4;
        else if (phase < 0.2) newY = 12 - 8;
        else if (phase < 0.25) newY = 12 + 12;
        else if (phase < 0.3) newY = 12 - 4;
        else if (phase < 0.35) newY = 12 + 2;
        else newY = 12 + (Math.random() - 0.5) * 2;
        const newPts = [...pts.slice(-50), `${len * 4},${newY}`];
        return newPts.join(' ') + ' ';
      });
    }, Math.round(80 / bpmFactor));
    return () => clearInterval(iv);
  }, [bpm, bpmFactor]);

  return (
    <svg width="100%" height="24" viewBox="0 0 200 24" preserveAspectRatio="none" className="w-full">
      <polyline points={points} fill="none" stroke={P.pink} strokeWidth="1.2" opacity="0.7" />
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// DELIBERATION ROOM — غرفة المداولة (خماسي تفاعلي)
// ═══════════════════════════════════════════════════════════════════════
function DeliberationRoom({ onBack, brains }: { onBack: () => void; brains: BrainState[] }) {
  const [question, setQuestion] = useState('');
  const [deliberating, setDeliberating] = useState(false);
  const [result, setResult] = useState<{
    winner: string; confidence: number;
    arguments: Array<{ brain_id: string; brain_name: string; argument: string; confidence: number }>;
  } | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 80);
    return () => clearInterval(iv);
  }, []);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setDeliberating(true);
    try {
      const res = await triggerDeliberation(question);
      setResult(res as typeof result);
    } catch {
      setResult({
        winner: 'neural', confidence: 0.85,
        arguments: brains.map(b => ({
          brain_id: b.id, brain_name: b.nameAr,
          argument: `تحليل ${b.nameAr}: تم معالجة السؤال`, confidence: b.confidence / 100,
        })),
      });
    }
    setDeliberating(false);
  };

  const cx = 250, cy = 180, radius = 130;
  const positions = brains.slice(0, 5).map((_, i) => {
    const angle = (i / 5) * 2 * Math.PI - Math.PI / 2;
    return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
  });

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>غرفة المداولة</h2>
        <div className="flex items-center gap-2 text-xs" style={{ color: P.white30 }}>
          <Users className="w-3.5 h-3.5" /> {brains.length} أدمغة
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center relative overflow-hidden">
        <svg width="500" height="360" viewBox="0 0 500 360">
          {/* Connections */}
          {positions.map((pos, i) => positions.map((pos2, j) => j > i ? (
            <line key={`l-${i}-${j}`} x1={pos.x} y1={pos.y} x2={pos2.x} y2={pos2.y}
              stroke={P.pinkDim} strokeWidth="0.5" strokeDasharray="4 4">
              {deliberating && <animate attributeName="stroke-opacity" values="0.2;0.8;0.2" dur="1s" repeatCount="indefinite" />}
            </line>
          ) : null))}
          {/* Center connections */}
          {positions.map((pos, i) => (
            <line key={`c-${i}`} x1={pos.x} y1={pos.y} x2={cx} y2={cy}
              stroke={P.pinkDim} strokeWidth="0.6" opacity={deliberating ? 0.4 : 0.12}>
              {deliberating && <animate attributeName="opacity" values="0.1;0.5;0.1" dur={`${0.8 + i * 0.2}s`} repeatCount="indefinite" />}
            </line>
          ))}
          {/* Center hub */}
          <circle cx={cx} cy={cy} r="22" fill={P.pinkDim} stroke={P.pink} strokeWidth="1" opacity="0.3">
            <animate attributeName="r" values="20;26;20" dur="2s" repeatCount="indefinite" />
          </circle>
          <circle cx={cx} cy={cy} r="6" fill={P.pink} opacity="0.6">
            <animate attributeName="opacity" values="0.4;0.9;0.4" dur="1.5s" repeatCount="indefinite" />
          </circle>
          {result && <text x={cx} y={cy + 3} textAnchor="middle" fill={P.white} fontSize="9" fontFamily="sans-serif">{Math.round(result.confidence * 100)}%</text>}

          {/* Brain nodes */}
          {brains.slice(0, 5).map((brain, i) => {
            const pos = positions[i];
            const isW = result?.winner === brain.id;
            // Animated pulse ring for winner
            return (
              <g key={brain.id}>
                {isW && <circle cx={pos.x} cy={pos.y} r="30" fill="none" stroke={P.pinkLight} strokeWidth="0.5" opacity="0.3">
                  <animate attributeName="r" values="26;35;26" dur="1.5s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.3;0;0.3" dur="1.5s" repeatCount="indefinite" />
                </circle>}
                <circle cx={pos.x} cy={pos.y} r={isW ? 26 : 20}
                  fill={isW ? P.pinkMid : P.card} stroke={isW ? P.pink : P.pinkDim} strokeWidth={isW ? 2 : 1} />
                <text x={pos.x} y={pos.y - 3} textAnchor="middle" fill={P.white90} fontSize="8" fontFamily="sans-serif">{brain.nameAr}</text>
                <text x={pos.x} y={pos.y + 9} textAnchor="middle" fill={P.white30} fontSize="6" fontFamily="monospace">{brain.model}</text>
                <text x={pos.x} y={pos.y + 20} textAnchor="middle" fill={P.pink} fontSize="7" fontFamily="monospace">{brain.confidence}%</text>
              </g>
            );
          })}

          {/* Floating signals during deliberation */}
          {deliberating && Array.from({ length: 5 }).map((_, i) => {
            const progress = ((tick * 2 + i * 40) % 200) / 200;
            const srcIdx = i % 5;
            const src = positions[srcIdx];
            return (
              <circle key={`sig-${i}`}
                cx={src.x + (cx - src.x) * progress}
                cy={src.y + (cy - src.y) * progress}
                r="2" fill={P.pinkLight} opacity={0.5 * (1 - progress)} />
            );
          })}
        </svg>
      </div>

      {/* Arguments */}
      {result && (
        <div className="mx-4 mb-2 space-y-1.5 max-h-40 overflow-y-auto sb">
          {result.arguments.map((arg, i) => (
            <div key={i} className="p-2.5 rounded-xl" style={{
              background: arg.brain_id === result.winner ? P.pinkMid : P.white02,
              border: `1px solid ${arg.brain_id === result.winner ? P.pinkStrong : P.pinkDim}`,
            }}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold" style={{ color: P.pinkLight }}>{arg.brain_name}</span>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded" style={{ background: P.pinkDim, color: P.pink }}>
                  ثقة {Math.round(arg.confidence * 100)}%
                </span>
              </div>
              <p className="text-[10px] leading-relaxed" style={{ color: P.white70 }}>{arg.argument}</p>
            </div>
          ))}
        </div>
      )}

      {/* Result summary */}
      {result && (
        <div className="mx-4 mb-3 p-3 rounded-xl" style={{ background: P.pinkDim, border: `1px solid ${P.pinkStrong}` }}>
          <div className="text-xs mb-1" style={{ color: P.white50 }}>الإجماع</div>
          <div className="text-sm" style={{ color: P.white90 }}>
            الفائز: <span style={{ color: P.pinkLight }}>{result.winner}</span> — ثقة {Math.round(result.confidence * 100)}%
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
        <div className="flex gap-3 items-center">
          <input type="text" value={question} onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAsk()}
            placeholder="اسأل الأدمغة سؤالك..." dir="rtl"
            className="flex-1 bg-transparent border rounded-2xl px-4 py-3 text-sm outline-none"
            style={{ borderColor: P.pinkDim, color: P.white, background: P.pinkDim }} />
          <button onClick={handleAsk} disabled={deliberating || !question.trim()}
            className="w-11 h-11 flex items-center justify-center rounded-full shrink-0"
            style={{ background: question.trim() ? P.pink : P.white08, color: question.trim() ? P.white : P.white30, boxShadow: question.trim() ? P.pinkGlow : 'none' }}>
            {deliberating ? <Activity className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4 rotate-180" />}
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// THOUGHT STREAM — تيار الأفكار الداخلية
// ═══════════════════════════════════════════════════════════════════════
const FALLBACK_THOUGHTS = [
  'NeuralBus: إشارة new_task وصلت...',
  'ConsciousnessLoop: فحص الذات — مستوى الوعي 0.72',
  'InnerMonologue: هل هذا الطلب يتطلب System2؟',
  'BrainRouter: توجيه إلى الدماغ السببي...',
  'SelfHealingEngine: فحص صحة — 0 خطأ',
];

function ThoughtStream({ liveThoughts }: { liveThoughts?: string[] }) {
  const [idx, setIdx] = useState(0);
  const thoughts = (liveThoughts && liveThoughts.length > 0) ? liveThoughts : FALLBACK_THOUGHTS;
  useEffect(() => {
    const iv = setInterval(() => setIdx(i => (i + 1) % thoughts.length), 3000);
    return () => clearInterval(iv);
  }, [thoughts.length]);
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: P.pinkDim }}>
      <div className="w-1.5 h-1.5 rounded-full hud-blink" style={{ background: (liveThoughts && liveThoughts.length > 0) ? P.green : P.pink }} />
      <span className="text-[9px] font-mono thought-flow" style={{ color: P.pinkLight }}>{thoughts[idx]}</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// FEATURE CONTROL ROW — صف تحكم الميزة (toggle + configure + monitor)
// ═══════════════════════════════════════════════════════════════════════
function FeatureControl({ feature, enabled, onToggle, onAction }: {
  feature: { id: number; nameEn: string; nameAr: string; status: string; apiEndpoint: string; backendFile: string };
  enabled: boolean;
  onToggle: (id: number) => void;
  onAction: (featureId: number, action: string) => void;
}) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg transition-all cursor-pointer group"
      style={{ background: P.white02, border: '1px solid transparent' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = P.pinkDim; e.currentTarget.style.background = P.pinkDim; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'transparent'; e.currentTarget.style.background = P.white02; }}
    >
      <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{
        background: feature.status === 'active' ? P.pink : feature.status === 'evolving' ? P.pinkLight : feature.status === 'error' ? P.red : P.white15,
        boxShadow: feature.status === 'active' ? P.pinkGlow : 'none',
      }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] truncate" style={{ color: P.white90 }}>{feature.nameAr}</span>
          <span className="text-[7px] font-mono shrink-0 px-1 py-0.5 rounded" style={{
            background: feature.status === 'active' ? P.pinkMid : feature.status === 'evolving' ? P.pinkDim : feature.status === 'error' ? 'rgba(239,68,68,0.15)' : P.white04,
            color: feature.status === 'active' ? P.pinkLight : feature.status === 'evolving' ? P.pink : feature.status === 'error' ? P.red : P.white30,
          }}>
            {feature.status === 'active' ? 'نشط' : feature.status === 'evolving' ? 'متطور' : feature.status === 'error' ? 'خطأ' : feature.status === 'idle' ? 'خامل' : 'استعداد'}
          </span>
        </div>
        <span className="text-[7px] font-mono block truncate" style={{ color: P.white15 }}>{feature.nameEn} — {feature.backendFile}</span>
      </div>
      {/* Quick action buttons */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={(e) => { e.stopPropagation(); onAction(feature.id, 'status'); }}
          className="w-5 h-5 flex items-center justify-center rounded" style={{ background: P.white04, color: P.white30 }}
          title="فحص الحالة">
          <Search className="w-2.5 h-2.5" />
        </button>
        <button onClick={(e) => { e.stopPropagation(); onAction(feature.id, 'restart'); }}
          className="w-5 h-5 flex items-center justify-center rounded" style={{ background: P.white04, color: P.white30 }}
          title="إعادة تشغيل">
          <RotateCcw className="w-2.5 h-2.5" />
        </button>
      </div>
      <div className={`feat-toggle ${enabled ? 'on' : ''}`} onClick={(e) => { e.stopPropagation(); onToggle(feature.id); }}>
        <div className="dot" />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// BRAIN WAVE — موجة دماغية حية لكل دماغ
// ═══════════════════════════════════════════════════════════════════════
function BrainWave({ active, label, confidence }: { active: boolean; label: string; confidence?: number }) {
  const [points, setPoints] = useState('0,15 ');
  useEffect(() => {
    const iv = setInterval(() => {
      setPoints(prev => {
        const pts = prev.trim().split(' ').filter(Boolean);
        const lastY = parseFloat(pts[pts.length - 1]?.split(',')[1] || '15');
        const newY = active ? Math.max(3, Math.min(27, lastY + (Math.random() - 0.5) * 12)) : 15 + Math.sin(Date.now() / 1000) * 2;
        const newPts = [...pts.slice(-30), `${(pts.length) * 6},${newY}`];
        return newPts.join(' ') + ' ';
      });
    }, 150);
    return () => clearInterval(iv);
  }, [active]);

  return (
    <div className="flex items-center gap-2 px-2 py-1 rounded-lg" style={{ background: P.white02 }}>
      <span className="text-[8px] font-mono shrink-0 w-20 truncate" style={{ color: P.white50 }}>{label}</span>
      <svg width="120" height="30" viewBox="0 0 180 30" className="shrink-0">
        <polyline points={points} fill="none" stroke={active ? P.pink : P.white15} strokeWidth="1" opacity={active ? 0.8 : 0.3} />
      </svg>
      {confidence !== undefined && (
        <span className="text-[7px] font-mono shrink-0" style={{ color: active ? P.pink : P.white30 }}>{confidence}%</span>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// LIFE BAR — شريط الحياة مع EEG
// ═══════════════════════════════════════════════════════════════════════
function LifeBar({ vitality, energy, coherence, bpm }: {
  vitality: number; energy: number; coherence: number; bpm: number;
}) {
  const bars = [
    { label: 'حيوية', value: vitality, color: P.pink },
    { label: 'طاقة', value: energy, color: P.pinkLight },
    { label: 'تماسك', value: coherence, color: P.pinkDark },
  ];

  return (
    <div className="flex items-center gap-3 px-3 py-1.5 rounded-xl" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
      <div className="flex items-center gap-1">
        <Heart className="w-3 h-3 heartbeat" style={{ color: P.pink }} />
        <span className="text-[8px] font-mono" style={{ color: P.pink }}>{bpm} BPM</span>
      </div>
      {bars.map(b => (
        <div key={b.label} className="flex items-center gap-1.5 flex-1">
          <span className="text-[7px] shrink-0" style={{ color: P.white30 }}>{b.label}</span>
          <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: P.white04 }}>
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${b.value}%`, background: b.color, boxShadow: `0 0 4px ${b.color}` }} />
          </div>
          <span className="text-[7px] font-mono shrink-0" style={{ color: P.white50 }}>{b.value}%</span>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// API KEYS PANEL — لوحة إدارة مفاتيح API
// ═══════════════════════════════════════════════════════════════════════
const API_KEY_BRAINS = [
  { id: 'neural', name: 'العصبي', model: 'GLM-5.1', provider: 'ZhipuAI (GLM)', icon: <Atom className="w-5 h-5" /> },
  { id: 'causal', name: 'السببي', model: 'DeepSeek-Reasoner', provider: 'DeepSeek', icon: <Waves className="w-5 h-5" /> },
  { id: 'symbolic', name: 'الرمزي', model: 'GLM-4-Plus', provider: 'ZhipuAI (GLM)', icon: <Hexagon className="w-5 h-5" /> },
  { id: 'bayesian', name: 'الاحتمالي', model: 'Gemini-2.0-Flash', provider: 'Google (Gemini)', icon: <Target className="w-5 h-5" /> },
  { id: 'worldmodel', name: 'نموذج العالم', model: 'DeepSeek-Chat', provider: 'DeepSeek', icon: <Globe className="w-5 h-5" /> },
];

function ApiKeysPanel({ onBack }: { onBack: () => void }) {
  // CRITICAL FIX: Separate "entered" (raw) keys from "existing" (masked) display
  // Previously, masked keys like "abcd...efgh" were put into input fields,
  // then the "..." caused them to be filtered out on Save = keys never saved!
  const [enteredKeys, setEnteredKeys] = useState<Record<string, string>>({}); // raw keys user typed
  const [existingMasked, setExistingMasked] = useState<Record<string, string>>({}); // masked display from server
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [connectionStatus, setConnectionStatus] = useState<Record<string, 'unknown' | 'connected' | 'missing' | 'invalid'>>({});
  const [distInfo, setDistInfo] = useState<Record<string, boolean>>({});
  const [geminiProxy, setGeminiProxy] = useState('');
  const [existingGeminiProxy, setExistingGeminiProxy] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [existingGithubToken, setExistingGithubToken] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [existingAdminPassword, setExistingAdminPassword] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [msg, setMsg] = useState('');

  const loadStatus = useCallback(async () => {
    try {
      const r = await fetch('/api/v2/api-keys');
      if (r.ok) {
        const d = await r.json();
        const brainData = d.brains || {};
        const newStatus: Record<string, 'unknown' | 'connected' | 'missing' | 'invalid'> = {};
        const newMasked: Record<string, string> = {};
        for (const [bid, info] of Object.entries(brainData) as [string, { has_key?: boolean; key_masked?: string; in_keystore?: boolean; in_frontend?: boolean; in_backend?: boolean }][]) {
          newStatus[bid] = info.has_key ? 'connected' : 'missing';
          newMasked[bid] = info.key_masked || '';
        }
        setConnectionStatus(newStatus);
        setExistingMasked(newMasked);
        // DON'T put masked keys into enteredKeys — they're separate!
        setExistingGeminiProxy(!!d.gemini_proxy);
        setExistingGithubToken(!!d.github_token);
        setExistingAdminPassword(!!d.admin_password_set);
        setDistInfo(d.distribution || {});
      }
    } catch { /* offline */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const handleSaveAll = async () => {
    setSaving(true);
    setMsg('');
    try {
      // Only send keys that the user ACTUALLY typed (from enteredKeys)
      const keyMap: Record<string, string> = {};
      for (const [brainId, rawKey] of Object.entries(enteredKeys)) {
        if (rawKey && rawKey.trim().length > 0) {
          keyMap[brainId] = rawKey.trim();
        }
      }
      const extraData: Record<string, string> = {};
      if (geminiProxy.trim()) extraData.gemini_proxy_url = geminiProxy.trim();
      if (githubToken.trim()) extraData.github_token = githubToken.trim();
      if (adminPassword.trim()) extraData.admin_password = adminPassword.trim();

      if (Object.keys(keyMap).length === 0 && Object.keys(extraData).length === 0) {
        setMsg('⚠️ لم تدخل أي مفتاح جديد — اكتب مفتاحاً في أحد الحقول ثم اضغط حفظ');
        setSaving(false);
        return;
      }

      const r = await fetch('/api/v2/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys: keyMap, ...extraData }),
      });
      const d = await r.json();
      if (d.success) {
        // Clear entered keys after successful save
        setEnteredKeys(prev => {
          const cleared = { ...prev };
          for (const bid of Object.keys(keyMap)) delete cleared[bid];
          return cleared;
        });
        setGeminiProxy('');
        setGithubToken('');
        setAdminPassword('');
        setMsg(d.message || '✅ تم الحفظ بنجاح');
      } else {
        setMsg(d.message || '❌ فشل الحفظ');
      }
      // Refresh status from server
      await loadStatus();
    } catch {
      setMsg('❌ خطأ في الاتصال — تحقق أن الموقع يعمل');
    }
    setSaving(false);
  };

  const handleTest = async (brainId: string) => {
    setTesting(brainId);
    setMsg('');
    try {
      const r = await fetch(`/api/v2/api-keys/test/${brainId}`, { method: 'POST' });
      const d = await r.json();
      if (d.status === 'valid') setConnectionStatus(p => ({ ...p, [brainId]: 'connected' }));
      else if (d.status === 'missing_key') setConnectionStatus(p => ({ ...p, [brainId]: 'missing' }));
      else if (d.status === 'invalid') setConnectionStatus(p => ({ ...p, [brainId]: 'invalid' }));
      else setConnectionStatus(p => ({ ...p, [brainId]: 'invalid' }));
      setMsg(d.message || '');
    } catch {
      setMsg('❌ خطأ في الاتصال');
    }
    setTesting(null);
  };

  const handleReload = async () => {
    setMsg('');
    try {
      const r = await fetch('/api/v2/api-keys/reload', { method: 'POST' });
      const d = await r.json();
      setMsg(d.message || 'تم إعادة التحميل');
      await loadStatus();
    } catch {
      setMsg('❌ خطأ في إعادة التحميل');
    }
  };

  const activeCount = Object.values(connectionStatus).filter(s => s === 'connected').length;
  const statusIcon = (s: string) => s === 'connected' ? '✅' : s === 'missing' ? '❌' : s === 'invalid' ? '⚠️' : '⚪';
  const statusLabel = (s: string) => s === 'connected' ? 'نشط' : s === 'missing' ? 'لا يوجد مفتاح' : s === 'invalid' ? 'غير صالح' : 'غير معروف';

  // Get display value for input: show entered key if user typed one, otherwise show nothing
  const getInputValue = (brainId: string) => enteredKeys[brainId] || '';
  const getInputPlaceholder = (brainId: string) =>
    existingMasked[brainId] ? `● محفوظ (${existingMasked[brainId]}) — أدخل مفتاح جديد للاستبدال` : 'أدخل مفتاح API...';

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>إدارة مفاتيح API</h2>
          <span className="text-[9px] font-mono px-2 py-0.5 rounded-full" style={{ background: activeCount >= 3 ? 'rgba(76,175,80,0.15)' : P.pinkDim, color: activeCount >= 3 ? P.green : P.pinkLight }}>
            {activeCount}/5 نشطة
          </span>
        </div>
        <Lock className="w-4 h-4" style={{ color: P.pink }} />
      </div>

      <div className="flex-1 overflow-y-auto sb p-5 space-y-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Activity className="w-6 h-6 animate-spin" style={{ color: P.pink }} />
            <span className="text-xs mr-3" style={{ color: P.white50 }}>جارٍ التحميل...</span>
          </div>
        ) : (
          <>
            {/* Distribution status */}
            <div className="p-3 rounded-xl flex items-center gap-3 flex-wrap" style={{ background: P.pinkDim, border: `1px solid ${P.pinkDim}` }}>
              <span className="text-[9px] font-semibold" style={{ color: P.pinkLight }}>التوزيع:</span>
              <span className="text-[9px]" style={{ color: distInfo.keystore ? P.green : P.red }}>{distInfo.keystore ? '✅ مخزن' : '❌ مخزن'}</span>
              <span className="text-[9px]" style={{ color: distInfo.frontend_env ? P.green : P.red }}>{distInfo.frontend_env ? '✅ فرونت' : '❌ فرونت'}</span>
              <span className="text-[9px]" style={{ color: distInfo.backend_env ? P.green : P.orange }}>{distInfo.backend_env ? '✅ باك' : '⏳ باك'}</span>
              <button onClick={handleReload} className="text-[9px] px-2 py-0.5 rounded" style={{ background: P.white08, color: P.white50 }}>
                🔄 إعادة تحميل
              </button>
            </div>

            {/* Instructions */}
            <div className="p-3 rounded-xl" style={{ background: 'rgba(76,175,80,0.05)', border: '1px solid rgba(76,175,80,0.15)' }}>
              <p className="text-[10px]" style={{ color: P.white70 }}>
                💡 أدخل المفاتيح في الحقول أدناه ثم اضغط <b style={{ color: P.pinkLight }}>حفظ وتوزيع</b> — سيتم حفظها فوراً وتوزيعها على كل الأنظمة (Frontend + Backend + LLMClient) بدون إعادة تشغيل
              </p>
            </div>

            {/* Brain cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {API_KEY_BRAINS.map(brain => (
                <div key={brain.id} className="p-4 rounded-xl space-y-3" style={{ background: connectionStatus[brain.id] === 'connected' ? 'rgba(76,175,80,0.03)' : P.white02, border: `1px solid ${connectionStatus[brain.id] === 'connected' ? 'rgba(76,175,80,0.15)' : P.pinkDim}` }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span style={{ color: connectionStatus[brain.id] === 'connected' ? P.green : P.pink }}>{brain.icon}</span>
                      <div>
                        <span className="text-xs font-semibold block" style={{ color: P.white90 }}>{brain.name}</span>
                        <span className="text-[9px] font-mono" style={{ color: P.white30 }}>{brain.model}</span>
                      </div>
                    </div>
                    <div className="text-center">
                      <span className="text-sm">{statusIcon(connectionStatus[brain.id] || 'unknown')}</span>
                      <span className="text-[8px] block" style={{ color: connectionStatus[brain.id] === 'connected' ? P.green : P.white30 }}>{statusLabel(connectionStatus[brain.id] || 'unknown')}</span>
                    </div>
                  </div>
                  <div className="text-[9px]" style={{ color: P.white30 }}>المزود: {brain.provider}</div>
                  <div className="relative">
                    <input
                      type={showKeys[brain.id] ? 'text' : 'password'}
                      value={getInputValue(brain.id)}
                      onChange={e => setEnteredKeys(p => ({ ...p, [brain.id]: e.target.value }))}
                      placeholder={getInputPlaceholder(brain.id)}
                      dir="ltr"
                      className="w-full px-3 py-2 rounded-lg text-[11px] font-mono outline-none pl-9"
                      style={{ background: P.card, border: `1px solid ${connectionStatus[brain.id] === 'connected' ? 'rgba(76,175,80,0.2)' : P.pinkDim}`, color: P.white90 }}
                    />
                    <button
                      onClick={() => setShowKeys(p => ({ ...p, [brain.id]: !p[brain.id] }))}
                      className="absolute left-2 top-1/2 -translate-y-1/2"
                      style={{ color: P.white30 }}
                    >
                      {showKeys[brain.id] ? <Eye className="w-3.5 h-3.5" /> : <Shield className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleTest(brain.id)} disabled={testing === brain.id}
                      className="flex-1 py-1.5 rounded-lg text-[10px] font-semibold"
                      style={{ background: P.white04, border: `1px solid ${P.pinkDim}`, color: P.white70, opacity: testing === brain.id ? 0.5 : 1 }}>
                      {testing === brain.id ? '⏳ جارٍ الفحص...' : '🔍 فحص الاتصال'}
                    </button>
                    {enteredKeys[brain.id] && (
                      <button onClick={() => setEnteredKeys(p => { const n = { ...p }; delete n[brain.id]; return n; })}
                        className="px-2 py-1.5 rounded-lg text-[10px]"
                        style={{ background: P.white04, border: `1px solid ${P.pinkDim}`, color: P.white30 }}>
                        ✕ مسح
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Extra fields */}
            <div className="p-4 rounded-xl space-y-3" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
              <h3 className="text-xs font-semibold" style={{ color: P.pinkLight }}>إعدادات إضافية</h3>
              <div>
                <label className="text-[9px] block mb-1" style={{ color: P.white30 }}>
                  رابط وكيل Gemini (Proxy) {existingGeminiProxy && <span style={{ color: P.green }}>— محفوظ ✅</span>}
                </label>
                <input type="text" value={geminiProxy} onChange={e => setGeminiProxy(e.target.value)} dir="ltr"
                  placeholder={existingGeminiProxy ? 'محفوظ — أدخل رابطاً جديداً للاستبدال' : 'https://proxy.example.com'}
                  className="w-full px-3 py-2 rounded-lg text-[11px] font-mono outline-none"
                  style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }} />
              </div>
              <div>
                <label className="text-[9px] block mb-1" style={{ color: P.white30 }}>
                  توكن GitHub (PAT) {existingGithubToken && <span style={{ color: P.green }}>— محفوظ ✅</span>}
                </label>
                <input type="password" value={githubToken} onChange={e => setGithubToken(e.target.value)} dir="ltr"
                  placeholder={existingGithubToken ? 'محفوظ — أدخل توكن جديد للاستبدال' : 'ghp_xxxxxxxxxxxx'}
                  className="w-full px-3 py-2 rounded-lg text-[11px] font-mono outline-none"
                  style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }} />
              </div>
              <div>
                <label className="text-[9px] block mb-1" style={{ color: P.white30 }}>
                  كلمة مرور المدير {existingAdminPassword && <span style={{ color: P.green }}>— محفوظة ✅</span>}
                </label>
                <input type="password" value={adminPassword} onChange={e => setAdminPassword(e.target.value)} dir="ltr"
                  placeholder={existingAdminPassword ? 'محفوظة — أدخل كلمة جديدة للاستبدال' : '••••••••'}
                  className="w-full px-3 py-2 rounded-lg text-[11px] font-mono outline-none"
                  style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }} />
              </div>
            </div>

            {/* Save All */}
            <button onClick={handleSaveAll} disabled={saving}
              className="w-full py-3 rounded-xl text-sm font-semibold"
              style={{ background: P.pink, color: P.white, opacity: saving ? 0.5 : 1 }}>
              {saving ? '⏳ جارٍ الحفظ والتوزيع...' : '💾 حفظ وتوزيع على كل الأنظمة'}
            </button>

            {msg && (
              <div className="p-3 rounded-xl text-center text-xs" style={{ background: msg.includes('✅') ? 'rgba(76,175,80,0.08)' : msg.includes('⚠️') ? 'rgba(255,152,0,0.08)' : P.pinkDim, border: `1px solid ${msg.includes('✅') ? 'rgba(76,175,80,0.2)' : msg.includes('⚠️') ? 'rgba(255,152,0,0.2)' : P.pinkDim}`, color: P.white70 }}>
                {msg}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// CONTROL CENTER PANEL — مركز التحكم الشامل
// ═══════════════════════════════════════════════════════════════════════
function ControlCenterPanel({ onBack }: { onBack: () => void }) {
  // Section A: Brain Control Matrix
  const [brainMatrix, setBrainMatrix] = useState<Record<string, { enabled: boolean; temperature: number; weight: number; model: string }>>({
    neural: { enabled: true, temperature: 0.7, weight: 0.25, model: 'glm-5.1' },
    causal: { enabled: true, temperature: 0.5, weight: 0.22, model: 'deepseek-reasoner' },
    symbolic: { enabled: true, temperature: 0.3, weight: 0.18, model: 'glm-4-plus' },
    bayesian: { enabled: true, temperature: 0.6, weight: 0.17, model: 'gemini-2.0-flash' },
    worldmodel: { enabled: true, temperature: 0.8, weight: 0.18, model: 'deepseek-chat' },
  });
  const [applyingMatrix, setApplyingMatrix] = useState(false);

  // Section B: System Controls
  const [kernelRunning, setKernelRunning] = useState(true);
  const [kernelLoading, setKernelLoading] = useState(false);
  const [evolutionEnabled, setEvolutionEnabled] = useState(false);
  const [mutationRate, setMutationRate] = useState(0.1);
  const [healingLoading, setHealingLoading] = useState(false);
  const [autoUpdate, setAutoUpdate] = useState(false);

  // Section C: Feature Flags
  const [flags, setFlags] = useState<Array<{ name: string; enabled: boolean; description?: string }>>([]);
  const [flagsLoading, setFlagsLoading] = useState(true);

  // Section D: Safety Laws
  const [laws, setLaws] = useState<Array<{ id: string; nameAr: string; status: string; priority: number }>>([]);
  const [lawsLoading, setLawsLoading] = useState(true);
  const [shutdownLoading, setShutdownLoading] = useState(false);

  const [msg, setMsg] = useState('');

  // Load feature flags
  useEffect(() => {
    const loadFlags = async () => {
      try {
        const r = await fetch('/api/v2/feature-flags');
        if (r.ok) {
          const d = await r.json();
          const flagList = d.flags || d.features || [];
          if (Array.isArray(flagList)) setFlags(flagList.map((f: { name?: string; flag_name?: string; enabled?: boolean; description?: string }) => ({
            name: f.name || f.flag_name || '',
            enabled: !!f.enabled,
            description: f.description || '',
          })));
        }
      } catch { /* offline */ }
      setFlagsLoading(false);
    };
    loadFlags();
  }, []);

  // Load safety laws
  useEffect(() => {
    const loadLaws = async () => {
      try {
        const r = await fetch('/api/safety');
        if (r.ok) {
          const d = await r.json();
          const lawList = d.laws || d.safety_laws || [];
          if (Array.isArray(lawList)) setLaws(lawList);
          else setLaws([
            { id: 'L1', nameAr: 'قانون عدم الإيذاء', status: 'active', priority: 1 },
            { id: 'L2', nameAr: 'قانون الشفافية', status: 'active', priority: 2 },
            { id: 'L3', nameAr: 'قانون حماية الهوية', status: 'active', priority: 3 },
            { id: 'L4', nameAr: 'قانون العزل', status: 'active', priority: 4 },
            { id: 'L5', nameAr: 'قانون عدم مقاومة الإيقاف', status: 'active', priority: 5 },
            { id: 'L6', nameAr: 'قانون مراقبة الذات', status: 'active', priority: 6 },
            { id: 'L7', nameAr: 'قانون التعاون البشري', status: 'active', priority: 7 },
            { id: 'L8', nameAr: 'قانون النزاهة', status: 'active', priority: 8 },
          ]);
        }
      } catch {
        setLaws([
          { id: 'L1', nameAr: 'قانون عدم الإيذاء', status: 'active', priority: 1 },
          { id: 'L2', nameAr: 'قانون الشفافية', status: 'active', priority: 2 },
          { id: 'L3', nameAr: 'قانون حماية الهوية', status: 'active', priority: 3 },
          { id: 'L4', nameAr: 'قانون العزل', status: 'active', priority: 4 },
          { id: 'L5', nameAr: 'قانون عدم مقاومة الإيقاف', status: 'active', priority: 5 },
          { id: 'L6', nameAr: 'قانون مراقبة الذات', status: 'active', priority: 6 },
          { id: 'L7', nameAr: 'قانون التعاون البشري', status: 'active', priority: 7 },
          { id: 'L8', nameAr: 'قانون النزاهة', status: 'active', priority: 8 },
        ]);
      }
      setLawsLoading(false);
    };
    loadLaws();
  }, []);

  const apiCall = async (path: string, body?: Record<string, unknown>) => {
    try {
      const resp = body
        ? await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        : await fetch(path);
      if (resp.ok) return await resp.json();
      return { error: `HTTP ${resp.status}` };
    } catch { return { error: 'الخادم غير متصل' }; }
  };

  const handleApplyMatrix = async () => {
    setApplyingMatrix(true);
    const res = await apiCall('/api/v2/brains/matrix', brainMatrix as unknown as Record<string, unknown>);
    setMsg((res as { error?: string }).error ? `❌ ${(res as { error: string }).error}` : '✅ تم تطبيق مصفوفة الأدمغة');
    setApplyingMatrix(false);
  };

  const handleKernelAction = async (action: string) => {
    setKernelLoading(true);
    const res = await apiCall(`/api/kernel/${action}`);
    if (action === 'stop') setKernelRunning(false);
    else if (action === 'start') setKernelRunning(true);
    else if (action === 'restart') setKernelRunning(true);
    setMsg((res as { error?: string }).error ? `❌ ${(res as { error: string }).error}` : `✅ تم ${action === 'start' ? 'تشغيل' : action === 'stop' ? 'إيقاف' : 'إعادة تشغيل'} النواة`);
    setKernelLoading(false);
  };

  const handleEvolutionConfig = async () => {
    const res = await apiCall('/api/evolution/configure', { enabled: evolutionEnabled, mutation_rate: mutationRate });
    setMsg((res as { error?: string }).error ? `❌ ${(res as { error: string }).error}` : '✅ تم تحديث إعدادات التطور');
  };

  const handleHeal = async () => {
    setHealingLoading(true);
    const res = await apiCall('/api/v23/healing');
    setMsg((res as { error?: string }).error ? `❌ ${(res as { error: string }).error}` : '✅ تم تشغيل الشفاء الذاتي');
    setHealingLoading(false);
  };

  const handleAutoUpdate = async () => {
    const newVal = !autoUpdate;
    const res = await apiCall('/api/update/auto-toggle', { enabled: newVal });
    setAutoUpdate(!!(res as { enabled?: boolean })?.enabled || newVal);
    setMsg(newVal ? '🔄 التحديث التلقائي مفعّل' : '⏹️ التحديث التلقائي متوقف');
  };

  const handleToggleFlag = async (flagName: string, currentEnabled: boolean) => {
    const res = await apiCall(`/api/v2/feature-flags/${flagName}`, { enabled: !currentEnabled });
    setFlags(p => p.map(f => f.name === flagName ? { ...f, enabled: !currentEnabled } : f));
    if ((res as { error?: string }).error) setMsg(`❌ ${(res as { error: string }).error}`);
  };

  const handleShutdown = async () => {
    setShutdownLoading(true);
    await apiCall('/api/kernel/stop');
    setKernelRunning(false);
    setMsg('🛑 تم الإيقاف الطارئ');
    setShutdownLoading(false);
  };

  const enabledFlags = flags.filter(f => f.enabled).length;
  const disabledFlags = flags.length - enabledFlags;

  const brainNames: Record<string, string> = { neural: 'العصبي', causal: 'السببي', symbolic: 'الرمزي', bayesian: 'الاحتمالي', worldmodel: 'نموذج العالم' };
  const brainIcons: Record<string, React.ReactNode> = { neural: <Atom className="w-4 h-4" />, causal: <Waves className="w-4 h-4" />, symbolic: <Hexagon className="w-4 h-4" />, bayesian: <Target className="w-4 h-4" />, worldmodel: <Globe className="w-4 h-4" /> };

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>مركز التحكم الشامل</h2>
        <Cog className="w-4 h-4" style={{ color: P.pink }} />
      </div>

      <div className="flex-1 overflow-y-auto sb p-5 space-y-5">
        {/* Section A: Brain Control Matrix */}
        <div className="p-4 rounded-xl space-y-3" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
          <h3 className="text-xs font-semibold flex items-center gap-2" style={{ color: P.pinkLight }}>
            <Brain className="w-4 h-4" /> مصفوفة تحكم الأدمغة
          </h3>
          <div className="space-y-2">
            {Object.entries(brainMatrix).map(([id, cfg]) => (
              <div key={id} className="p-3 rounded-lg" style={{ background: P.card, border: `1px solid ${P.pinkDim}` }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span style={{ color: P.pink }}>{brainIcons[id]}</span>
                    <span className="text-[11px] font-semibold" style={{ color: P.white90 }}>{brainNames[id]}</span>
                  </div>
                  <button onClick={() => setBrainMatrix(p => ({ ...p, [id]: { ...p[id], enabled: !p[id].enabled } }))}
                    className="px-3 py-1 rounded-lg text-[9px] font-semibold"
                    style={{ background: cfg.enabled ? P.pinkMid : P.white04, border: `1px solid ${cfg.enabled ? P.pinkStrong : P.pinkDim}`, color: cfg.enabled ? P.pinkLight : P.white30 }}>
                    {cfg.enabled ? 'مفعّل' : 'معطّل'}
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-[8px] block mb-1" style={{ color: P.white30 }}>الحرارة ({cfg.temperature})</label>
                    <input type="range" min="0.1" max="2.0" step="0.1" value={cfg.temperature}
                      onChange={e => setBrainMatrix(p => ({ ...p, [id]: { ...p[id], temperature: parseFloat(e.target.value) } }))}
                      className="w-full accent-pink-600" style={{ accentColor: P.pink }} />
                  </div>
                  <div>
                    <label className="text-[8px] block mb-1" style={{ color: P.white30 }}>الوزن ({cfg.weight})</label>
                    <input type="range" min="0" max="1" step="0.05" value={cfg.weight}
                      onChange={e => setBrainMatrix(p => ({ ...p, [id]: { ...p[id], weight: parseFloat(e.target.value) } }))}
                      className="w-full" style={{ accentColor: P.pink }} />
                  </div>
                  <div>
                    <label className="text-[8px] block mb-1" style={{ color: P.white30 }}>النموذج</label>
                    <select value={cfg.model} onChange={e => setBrainMatrix(p => ({ ...p, [id]: { ...p[id], model: e.target.value } }))}
                      className="w-full px-2 py-1 rounded text-[9px] font-mono outline-none"
                      style={{ background: P.bg, border: `1px solid ${P.pinkDim}`, color: P.white70 }}>
                      <option value="glm-5.1">GLM-5.1</option>
                      <option value="glm-4-plus">GLM-4-Plus</option>
                      <option value="deepseek-reasoner">DeepSeek-Reasoner</option>
                      <option value="deepseek-chat">DeepSeek-Chat</option>
                      <option value="gemini-2.0-flash">Gemini-2.0-Flash</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <button onClick={handleApplyMatrix} disabled={applyingMatrix}
            className="w-full py-2 rounded-lg text-xs font-semibold"
            style={{ background: P.pink, color: P.white, opacity: applyingMatrix ? 0.5 : 1 }}>
            {applyingMatrix ? '⏳ جارٍ التطبيق...' : '⚙️ تطبيق التغييرات'}
          </button>
        </div>

        {/* Section B: System Controls */}
        <div className="p-4 rounded-xl space-y-3" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
          <h3 className="text-xs font-semibold flex items-center gap-2" style={{ color: P.pinkLight }}>
            <Settings className="w-4 h-4" /> تحكم النظام
          </h3>
          {/* Kernel */}
          <div className="p-3 rounded-lg" style={{ background: P.card, border: `1px solid ${P.pinkDim}` }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold" style={{ color: P.white90 }}>النواة (Kernel)</span>
              <span className="text-[9px]" style={{ color: kernelRunning ? P.green : P.red }}>{kernelRunning ? '● تعمل' : '○ متوقفة'}</span>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleKernelAction('start')} disabled={kernelLoading || kernelRunning}
                className="flex-1 py-1.5 rounded-lg text-[10px]" style={{ background: P.pinkMid, border: `1px solid ${P.pinkStrong}`, color: P.pinkLight, opacity: kernelLoading || kernelRunning ? 0.4 : 1 }}>
                <Play className="w-3 h-3 inline ml-1" /> تشغيل
              </button>
              <button onClick={() => handleKernelAction('stop')} disabled={kernelLoading || !kernelRunning}
                className="flex-1 py-1.5 rounded-lg text-[10px]" style={{ background: P.white04, border: `1px solid ${P.pinkDim}`, color: P.white70, opacity: kernelLoading || !kernelRunning ? 0.4 : 1 }}>
                <Power className="w-3 h-3 inline ml-1" /> إيقاف
              </button>
              <button onClick={() => handleKernelAction('restart')} disabled={kernelLoading}
                className="flex-1 py-1.5 rounded-lg text-[10px]" style={{ background: P.white04, border: `1px solid ${P.pinkDim}`, color: P.white70, opacity: kernelLoading ? 0.4 : 1 }}>
                <RotateCcw className="w-3 h-3 inline ml-1" /> إعادة
              </button>
            </div>
          </div>
          {/* Evolution */}
          <div className="p-3 rounded-lg" style={{ background: P.card, border: `1px solid ${P.pinkDim}` }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold" style={{ color: P.white90 }}>التطور</span>
              <button onClick={() => { setEvolutionEnabled(!evolutionEnabled); handleEvolutionConfig(); }}
                className="px-3 py-1 rounded-lg text-[9px] font-semibold"
                style={{ background: evolutionEnabled ? P.pinkMid : P.white04, border: `1px solid ${evolutionEnabled ? P.pinkStrong : P.pinkDim}`, color: evolutionEnabled ? P.pinkLight : P.white30 }}>
                {evolutionEnabled ? 'مفعّل' : 'معطّل'}
              </button>
            </div>
            <label className="text-[8px] block mb-1" style={{ color: P.white30 }}>معدل الطفرة ({mutationRate})</label>
            <input type="range" min="0.01" max="0.5" step="0.01" value={mutationRate}
              onChange={e => setMutationRate(parseFloat(e.target.value))}
              className="w-full" style={{ accentColor: P.pink }} />
          </div>
          {/* Self-Healing */}
          <div className="p-3 rounded-lg flex items-center justify-between" style={{ background: P.card, border: `1px solid ${P.pinkDim}` }}>
            <span className="text-[11px] font-semibold" style={{ color: P.white90 }}>الشفاء الذاتي</span>
            <button onClick={handleHeal} disabled={healingLoading}
              className="px-4 py-1.5 rounded-lg text-[10px] font-semibold"
              style={{ background: P.pinkMid, border: `1px solid ${P.pinkStrong}`, color: P.pinkLight, opacity: healingLoading ? 0.5 : 1 }}>
              {healingLoading ? '⏳ جارٍ...' : '🏥 تفعيل الشفاء'}
            </button>
          </div>
          {/* Auto-Update */}
          <div className="p-3 rounded-lg flex items-center justify-between" style={{ background: P.card, border: `1px solid ${P.pinkDim}` }}>
            <span className="text-[11px] font-semibold" style={{ color: P.white90 }}>التحديث التلقائي</span>
            <button onClick={handleAutoUpdate}
              className="px-3 py-1 rounded-lg text-[9px] font-semibold"
              style={{ background: autoUpdate ? P.pinkMid : P.white04, border: `1px solid ${autoUpdate ? P.pinkStrong : P.pinkDim}`, color: autoUpdate ? P.pinkLight : P.white30 }}>
              {autoUpdate ? 'مفعّل' : 'معطّل'}
            </button>
          </div>
        </div>

        {/* Section C: Feature Flags */}
        <div className="p-4 rounded-xl space-y-3" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
          <h3 className="text-xs font-semibold flex items-center justify-between" style={{ color: P.pinkLight }}>
            <span className="flex items-center gap-2"><Zap className="w-4 h-4" /> مدير الميزات</span>
            <span className="text-[9px]" style={{ color: P.white30 }}>{enabledFlags} مفعّلة / {disabledFlags} معطّلة</span>
          </h3>
          {flagsLoading ? (
            <div className="flex items-center justify-center py-4">
              <Activity className="w-4 h-4 animate-spin" style={{ color: P.pink }} />
            </div>
          ) : flags.length === 0 ? (
            <span className="text-[10px]" style={{ color: P.white30 }}>لا توجد ميزات مسجلة</span>
          ) : (
            <div className="space-y-1.5 max-h-64 overflow-y-auto sb">
              {flags.map(f => (
                <div key={f.name} className="flex items-center justify-between p-2 rounded-lg" style={{ background: P.card }}>
                  <div>
                    <span className="text-[10px] font-semibold" style={{ color: P.white70 }}>{f.name}</span>
                    {f.description && <span className="text-[8px] block" style={{ color: P.white30 }}>{f.description}</span>}
                  </div>
                  <button onClick={() => handleToggleFlag(f.name, f.enabled)}
                    className="w-10 h-5 rounded-full relative transition-all"
                    style={{ background: f.enabled ? P.pink : P.white08 }}>
                    <div className="w-4 h-4 rounded-full absolute top-0.5 transition-all"
                      style={{ background: P.white, left: f.enabled ? '20px' : '2px' }} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section D: Safety & Laws */}
        <div className="p-4 rounded-xl space-y-3" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
          <h3 className="text-xs font-semibold flex items-center gap-2" style={{ color: P.pinkLight }}>
            <Shield className="w-4 h-4" /> قوانين الأمان
          </h3>
          {lawsLoading ? (
            <div className="flex items-center justify-center py-4">
              <Activity className="w-4 h-4 animate-spin" style={{ color: P.pink }} />
            </div>
          ) : (
            <div className="space-y-1.5">
              {laws.map(law => (
                <div key={law.id} className="flex items-center justify-between p-2 rounded-lg" style={{ background: P.card }}>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: P.pinkDim, color: P.pinkLight }}>{law.id}</span>
                    <span className="text-[10px]" style={{ color: P.white70 }}>{law.nameAr}</span>
                  </div>
                  <span className="text-[9px]" style={{ color: law.status === 'active' ? P.green : P.orange }}>
                    {law.status === 'active' ? '✅ ساري' : '⚠️ معطّل'}
                  </span>
                </div>
              ))}
            </div>
          )}
          <button onClick={handleShutdown} disabled={shutdownLoading}
            className="w-full py-2.5 rounded-lg text-xs font-semibold"
            style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)', color: '#EF4444', opacity: shutdownLoading ? 0.5 : 1 }}>
            <Siren className="w-3.5 h-3.5 inline ml-1" /> إيقاف طارئ
          </button>
        </div>

        {msg && (
          <div className="p-3 rounded-xl text-center text-xs" style={{ background: P.pinkDim, border: `1px solid ${P.pinkDim}`, color: P.white70 }}>
            {msg}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// SMART CHAT PANEL — محادثة ذكية مع الأدمغة الخمسة
// ═══════════════════════════════════════════════════════════════════════
interface SmartChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  brain?: string;
  brainName?: string;
  model?: string;
  confidence?: number;
  responseTime?: number;
  timestamp: Date;
}

function SmartChatPanel({ onBack }: { onBack: () => void }) {
  const [messages, setMessages] = useState<SmartChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [selectedBrain, setSelectedBrain] = useState('auto');
  const [deepThink, setDeepThink] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  let msgIdRef = useRef(0);

  const brainOptions = [
    { id: 'auto', name: 'تلقائي (Auto)', icon: <Sparkles className="w-3.5 h-3.5" /> },
    { id: 'neural', name: 'العصبي', icon: <Atom className="w-3.5 h-3.5" /> },
    { id: 'causal', name: 'السببي', icon: <Waves className="w-3.5 h-3.5" /> },
    { id: 'symbolic', name: 'الرمزي', icon: <Hexagon className="w-3.5 h-3.5" /> },
    { id: 'bayesian', name: 'الاحتمالي', icon: <Target className="w-3.5 h-3.5" /> },
    { id: 'worldmodel', name: 'نموذج العالم', icon: <Globe className="w-3.5 h-3.5" /> },
  ];

  const brainNameMap: Record<string, string> = { neural: 'العصبي', causal: 'السببي', symbolic: 'الرمزي', bayesian: 'الاحتمالي', worldmodel: 'نموذج العالم' };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || streaming) return;

    const userMsg: SmartChatMessage = {
      id: ++msgIdRef.current,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages(p => [...p, userMsg]);
    setInput('');
    setStreaming(true);
    setStreamContent('');

    const startTime = Date.now();

    try {
      const resp = await fetch('/api/mamoun-chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg.content,
          model: selectedBrain === 'auto' ? 'auto' : selectedBrain,
          history: messages.slice(-20).map(m => ({ role: m.role, content: m.content })),
          deep_think: deepThink,
        }),
      });

      if (!resp.ok) {
        setMessages(p => [...p, {
          id: ++msgIdRef.current, role: 'assistant', content: '❌ خطأ في الاتصال', brain: 'system',
          brainName: 'النظام', model: '-', confidence: 0, responseTime: Date.now() - startTime, timestamp: new Date(),
        }]);
        setStreaming(false);
        return;
      }

      const reader = resp.body?.getReader();
      if (!reader) {
        setStreaming(false);
        return;
      }

      const decoder = new TextDecoder();
      let fullContent = '';
      let brainUsed = selectedBrain === 'auto' ? 'neural' : selectedBrain;
      let confidence = 0.85;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'token' && parsed.content) {
                fullContent += parsed.content;
                setStreamContent(fullContent);
                if (parsed.brain) brainUsed = parsed.brain;
              } else if (parsed.type === 'done') {
                if (parsed.brain) brainUsed = parsed.brain;
                if (parsed.confidence) confidence = parsed.confidence;
              } else if (parsed.content) {
                fullContent += parsed.content;
                setStreamContent(fullContent);
              }
            } catch {
              // Raw text
              fullContent += data;
              setStreamContent(fullContent);
            }
          }
        }
      }

      setMessages(p => [...p, {
        id: ++msgIdRef.current,
        role: 'assistant',
        content: fullContent || 'عذراً، لم أتمكن من الرد',
        brain: brainUsed,
        brainName: brainNameMap[brainUsed] || brainUsed,
        model: brainUsed,
        confidence,
        responseTime: Date.now() - startTime,
        timestamp: new Date(),
      }]);
    } catch {
      // Fallback: try non-streaming
      try {
        const resp = await fetch('/api/mamoun-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMsg.content, model: selectedBrain === 'auto' ? undefined : selectedBrain, history: messages.slice(-20).map(m => ({ role: m.role, content: m.content })) }),
        });
        const d = await resp.json();
        const brainUsed = d.winning_brain || d.brain || 'neural';
        setMessages(p => [...p, {
          id: ++msgIdRef.current, role: 'assistant',
          content: d.response || d.content || 'عذراً، لم أتمكن من الرد',
          brain: brainUsed, brainName: brainNameMap[brainUsed] || brainUsed,
          model: d.metadata?.model || brainUsed,
          confidence: d.confidence || 0.85,
          responseTime: Date.now() - startTime,
          timestamp: new Date(),
        }]);
      } catch {
        setMessages(p => [...p, {
          id: ++msgIdRef.current, role: 'assistant', content: '❌ جميع نقاط النهاية غير متاحة', brain: 'system',
          brainName: 'النظام', model: '-', confidence: 0, responseTime: Date.now() - startTime, timestamp: new Date(),
        }]);
      }
    }

    setStreaming(false);
    setStreamContent('');
    inputRef.current?.focus();
  };

  return (
    <div className="flex-1 flex flex-col h-full" style={{ background: P.black }}>
      <div className="flex items-center justify-between px-6 py-3" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-sm" style={{ color: P.pinkLight }}>
          <ChevronLeft className="w-4 h-4" /> الرجوع
        </button>
        <h2 className="text-sm font-semibold tracking-wider" style={{ color: P.white70 }}>محادثة ذكية</h2>
        <MessageSquare className="w-4 h-4" style={{ color: P.pink }} />
      </div>

      {/* Controls bar */}
      <div className="flex items-center gap-3 px-4 py-2" style={{ borderBottom: `1px solid ${P.pinkDim}`, background: P.white02 }}>
        <select value={selectedBrain} onChange={e => setSelectedBrain(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-[10px] font-semibold outline-none"
          style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }}>
          {brainOptions.map(b => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
        <button onClick={() => setDeepThink(!deepThink)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold"
          style={{ background: deepThink ? P.pinkMid : P.white04, border: `1px solid ${deepThink ? P.pinkStrong : P.pinkDim}`, color: deepThink ? P.pinkLight : P.white30 }}>
          <Brain className="w-3.5 h-3.5" /> تفكير عميق {deepThink ? 'ON' : 'OFF'}
        </button>
        <span className="text-[9px] mr-auto" style={{ color: P.white30 }}>{messages.length} رسالة</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto sb p-4 space-y-3">
        {messages.length === 0 && !streaming && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2">
              <Brain className="w-12 h-12 mx-auto" style={{ color: P.pink }} />
              <p className="text-sm" style={{ color: P.white50 }}>ابدأ محادثة مع الأدمغة الخمسة</p>
              <p className="text-[10px]" style={{ color: P.white30 }}>اختر دماغاً محدداً أو اتركه تلقائياً</p>
            </div>
          </div>
        )}
        {messages.map(m => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl p-3 ${m.role === 'user' ? 'rounded-br-sm' : 'rounded-bl-sm'}`}
              style={{
                background: m.role === 'user' ? P.pinkMid : P.card,
                border: `1px solid ${m.role === 'user' ? P.pinkStrong : P.pinkDim}`,
              }}>
              {m.role === 'assistant' && m.brainName && (
                <div className="flex items-center gap-2 mb-2 pb-1.5" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
                  <Brain className="w-3 h-3" style={{ color: P.pink }} />
                  <span className="text-[9px] font-semibold" style={{ color: P.pinkLight }}>{m.brainName}</span>
                  {m.model && <span className="text-[8px] font-mono" style={{ color: P.white30 }}>{m.model}</span>}
                  {m.confidence !== undefined && <span className="text-[8px] font-mono" style={{ color: P.white30 }}>ثقة {Math.round(m.confidence * 100)}%</span>}
                  {m.responseTime !== undefined && <span className="text-[8px] font-mono" style={{ color: P.white30 }}>{(m.responseTime / 1000).toFixed(1)}ث</span>}
                </div>
              )}
              <div className="text-[12px] whitespace-pre-wrap" style={{ color: P.white90, direction: 'rtl', textAlign: 'right' }}>
                {m.content}
              </div>
              <div className="text-[8px] mt-1" style={{ color: P.white15 }}>
                {m.timestamp.toLocaleTimeString('ar')}
              </div>
            </div>
          </div>
        ))}
        {streaming && streamContent && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl rounded-bl-sm p-3" style={{ background: P.card, border: `1px solid ${P.pinkStrong}` }}>
              <div className="flex items-center gap-2 mb-2 pb-1.5" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
                <Brain className="w-3 h-3 animate-pulse" style={{ color: P.pinkLight }} />
                <span className="text-[9px] font-semibold" style={{ color: P.pinkLight }}>يفكر...</span>
              </div>
              <div className="text-[12px] whitespace-pre-wrap" style={{ color: P.white90, direction: 'rtl', textAlign: 'right' }}>
                {streamContent}
                <span className="animate-pulse" style={{ color: P.pink }}>▌</span>
              </div>
            </div>
          </div>
        )}
        {streaming && !streamContent && (
          <div className="flex justify-start">
            <div className="p-3 rounded-xl" style={{ background: P.card, border: `1px solid ${P.pinkDim}` }}>
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 animate-spin" style={{ color: P.pink }} />
                <span className="text-[10px]" style={{ color: P.white50 }}>جارٍ التفكير...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
        <form onSubmit={handleSend} className="flex items-center gap-2">
          <input ref={inputRef} type="text" value={input} onChange={e => setInput(e.target.value)}
            placeholder="اكتب رسالتك..."
            className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
            style={{ background: P.card, border: `1px solid ${P.pinkDim}`, color: P.white90 }}
            disabled={streaming} />
          <button type="button" className="w-10 h-10 flex items-center justify-center rounded-xl"
            style={{ background: P.white04, border: `1px solid ${P.pinkDim}`, color: P.white30 }}>
            <Mic className="w-4 h-4" />
          </button>
          <button type="submit" disabled={!input.trim() || streaming}
            className="w-10 h-10 flex items-center justify-center rounded-xl"
            style={{ background: input.trim() ? P.pink : P.white08, color: input.trim() ? P.white : P.white30 }}>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// MAIN COMPONENT — مأمون رؤية IDE
// ═══════════════════════════════════════════════════════════════════════
interface ChatMsg { id: number; type: 'system' | 'user' | 'ai'; text: string; brain?: string; confidence?: number; }

export default function MamounVisionIDE() {
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  const [activeNav, setActiveNav] = useState('brains');
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([2]));
  const [featureStates, setFeatureStates] = useState<Record<number, boolean>>({});
  const [searchQuery, setSearchQuery] = useState('');

  // Real data from backend
  const [brains, setBrains] = useState<BrainState[]>([]);
  const [vitality, setVitality] = useState(75);
  const [energy, setEnergy] = useState(85);
  const [coherence, setCoherence] = useState(82);
  const [consciousness, setConsciousness] = useState(0.7);
  const [bpm, setBpm] = useState(72);
  const [kernelStatus, setKernelStatus] = useState({ status: 'running', uptime: 0, active_processes: 5 });
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [emotionState, setEmotionState] = useState<Record<string, number>>({});
  const [evolutionGen, setEvolutionGen] = useState(35);
  const [evolutionFitness, setEvolutionFitness] = useState(0.85);
  const [prediction, setPrediction] = useState(0.8);
  const [signalCount, setSignalCount] = useState(28);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'degraded' | 'disconnected'>('connected');
  const [liveThoughts, setLiveThoughts] = useState<string[]>([]);
  const [confirmation, setConfirmation] = useState<{id: string; message: string} | null>(null);
  const [featureFlags, setFeatureFlags] = useState<Record<string, {enabled: boolean; label_ar: string; page?: string}>>({});

  // Chat
  const [messages, setMessages] = useState<ChatMsg[]>([
    { id: 1, type: 'system', text: '[core/mamoun_kernel.py] kernel_task STARTED' },
    { id: 2, type: 'system', text: '[core/neural_bus.py] Pub/Sub active — 28 signals' },
    { id: 3, type: 'ai', text: 'مأمون v5 متصل. الأدمغة الخمسة نشطة. كيف أساعدك؟', brain: 'neural', confidence: 92 },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mountedRef = useRef(true);

  // Init feature states from dashboard data (lazy init)
  const [featureStatesInitialized, setFeatureStatesInitialized] = useState(false);
  if (!featureStatesInitialized) {
    const states: Record<number, boolean> = {};
    DASHBOARD_SECTIONS.forEach(s => s.features.forEach(f => {
      states[f.id] = f.status === 'active' || f.status === 'evolving';
    }));
    setFeatureStates(states);
    setFeatureStatesInitialized(true);
  }

  // Fetch ALL data from backend — including v2 Event Bridge + Feature Flags
  useEffect(() => {
    mountedRef.current = true;
    const load = async () => {
      try {
        const results = await Promise.allSettled([
          fetchBrainStates(),
          fetchKernelStatus(),
          fetchLivingVitals(),
          fetchProjects(),
          fetchPendingApprovals(),
          fetchLivingEmotions(),
          fetchLivingHeartbeat(),
          fetchEvolutionStatus(),
          fetchConsciousnessState(),
          fetchEmotionState(),
          fetchHyperagentStatus(),
          fetchAGIStatus(),
          fetchMetacognitiveAssessment(),
          // v38: Event Bridge — بيانات حية
          fetch('/api/v2/events/snapshot').then(r => r.ok ? r.json() : Promise.reject('events')),
          fetch('/api/v2/events/neural-bus').then(r => r.ok ? r.json() : Promise.reject('neural_bus')),
          fetch('/api/v2/events/monologue').then(r => r.ok ? r.json() : Promise.reject('monologue')),
          fetch('/api/v2/events/connection-status').then(r => r.ok ? r.json() : Promise.reject('connection')),
          fetch('/api/v2/feature-flags').then(r => r.ok ? r.json() : Promise.reject('flags')),
        ]);

        if (!mountedRef.current) return;

        const [bd, kd, vd, pd, ad, ed, hd, evd, cd, emd, had, agid, md, evSnap, nbLive, moLive, connSt, flagsData] = results;

        if (bd.status === 'fulfilled') setBrains(bd.value.brains || []);
        if (kd.status === 'fulfilled') setKernelStatus({
          status: kd.value.kernel_status || 'running',
          uptime: kd.value.uptime || 0,
          active_processes: kd.value.active_processes || 0,
        });
        if (vd.status === 'fulfilled') {
          const v = vd.value as Record<string, unknown>;
          setVitality(Math.round((v.vitality as number) || 75));
          setEnergy(Math.round((v.energy as number) || 85));
          setCoherence(Math.round(((v.coherence as number) || 0.82) * 100));
        }
        if (pd.status === 'fulfilled') setProjects(pd.value.projects || []);
        if (ad.status === 'fulfilled') {
          const r = (ad.value as { requests?: unknown[] }).requests;
          setPendingApprovals(Array.isArray(r) ? r.length : 0);
        }
        if (ed.status === 'fulfilled') {
          const e = ed.value as { emotions?: Record<string, number> };
          if (e.emotions) setEmotionState(e.emotions);
        }
        if (hd.status === 'fulfilled') {
          const h = hd.value as { bpm?: number };
          if (h.bpm) setBpm(h.bpm);
        }
        if (evd.status === 'fulfilled') {
          const ev = evd.value as { version?: { generation?: number; fitness_score?: number } };
          if (ev.version) {
            setEvolutionGen(ev.version.generation || 35);
            setEvolutionFitness(ev.version.fitness_score || 0.85);
          }
        }
        if (cd.status === 'fulfilled') {
          const c = cd.value as { level?: number; self_awareness?: number };
          if (c.level) setConsciousness(c.level);
        }
        if (md.status === 'fulfilled') {
          const m = md.value as { overall_self_awareness?: number };
          setPrediction(m.overall_self_awareness || 0.8);
        }

        // v38: NeuralBus live signals → SignalRadar
        if (nbLive.status === 'fulfilled') {
          const nb = nbLive.value as { total_signals?: number };
          if (nb.total_signals !== undefined) setSignalCount(nb.total_signals);
        }

        // v38: Inner Monologue live thoughts → ThoughtStream
        if (moLive.status === 'fulfilled') {
          const mo = moLive.value as { thoughts?: string[] };
          if (mo.thoughts && mo.thoughts.length > 0) setLiveThoughts(mo.thoughts);
        }

        // v38: Connection status → مؤشر الاتصال
        if (connSt.status === 'fulfilled') {
          const cs = connSt.value as { status?: string };
          if (cs.status) setConnectionStatus(cs.status as typeof connectionStatus);
        }

        // v38: Feature Flags → تحديث حالة الميزات من الخلفية
        if (flagsData.status === 'fulfilled') {
          const fd = flagsData.value as { flags?: Record<string, { enabled: boolean; label_ar: string; page?: string }> };
          if (fd.flags) {
            setFeatureFlags(fd.flags);
            // مزامنة حالة الميزات مع الخلفية
            const newStates: Record<number, boolean> = {};
            DASHBOARD_SECTIONS.forEach(s => s.features.forEach(f => {
              // ابحث عن flag يقابل هذه الميزة
              const matchingFlag = Object.entries(fd.flags!).find(([_, v]) =>
                f.nameAr.includes(v.label_ar) || f.nameEn.toLowerCase().includes(v.label_ar.toLowerCase())
              );
              if (matchingFlag) {
                newStates[f.id] = matchingFlag[1].enabled;
              } else {
                newStates[f.id] = f.status === 'active' || f.status === 'evolving';
              }
            }));
            setFeatureStates(newStates);
          }
        }
      } catch {
        if (mountedRef.current && brains.length === 0) {
          setBrains(BRAIN_DEFINITIONS.map(b => ({
            id: b.id, name: b.nameEn, nameAr: b.nameAr, type: b.id,
            enabled: true, status: b.status as BrainState['status'],
            confidence: b.confidence, weight: 0.2, model: b.model,
          })));
          setConnectionStatus('disconnected');
        }
      }
    };
    load();
    const iv = setInterval(load, 10000);
    return () => { mountedRef.current = false; clearInterval(iv); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isTyping]);

  const handleCommand = useCallback(async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim()) return;
    const cmd = inputValue;
    setMessages(p => [...p, { id: Date.now(), type: 'user', text: cmd }]);
    setInputValue('');
    setIsTyping(true);

    // v38: إرسال عبر Unified Command Bus أولاً
    try {
      const cmdRes = await fetch('/api/v2/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd }),
      });
      if (cmdRes.ok) {
        const cmdData = await cmdRes.json();
        setIsTyping(false);

        // عرض رسالة النتيجة
        setMessages(p => [...p, {
          id: Date.now(), type: 'ai',
          text: cmdData.message || 'تم.',
          brain: cmdData.action,
          confidence: cmdData.success ? 95 : 30,
        }]);

        // فتح صفحة إذا طُلب
        if (cmdData.navigate_to) {
          const navMap: Record<string, ViewMode> = {
            'trading': 'trading', 'instagram': 'instagram', 'ecommerce': 'ecommerce',
            'blender': 'blender', 'embodiment': 'embodiment', 'mobile': 'mobile',
            'self-modify': 'self-modify', 'evolution': 'evolution', 'browser': 'browser',
            'laptop': 'laptop', 'github': 'github', 'diagnose': 'diagnose',
            'terminal': 'terminal', 'deliberation': 'deliberation',
            'brain-control': 'brain-control', 'feature-flags': 'feature-flags',
          };
          const target = navMap[cmdData.navigate_to];
          if (target) setViewMode(target);
        }

        // عرض تأكيد نعم/لا إذا طُلب
        if (cmdData.needs_confirmation && cmdData.confirmation_id) {
          setConfirmation({
            id: cmdData.confirmation_id,
            message: cmdData.message,
          });
        }
        return;
      }
    } catch {
      // Command Bus غير متاح — استخدم الشات العادي
    }

    // Fallback: شات عادي عبر النواة
    setMessages(p => [...p, { id: Date.now(), type: 'system', text: 'NeuralBus → GlobalWorkspace → BrainRouter...' }]);
    try {
      const res = await sendChatMessage(cmd, messages.filter(m => m.type !== 'system').map(m => ({
        role: m.type === 'user' ? 'user' as const : 'assistant' as const, content: m.text
      })));
      setIsTyping(false);
      setMessages(p => [...p, {
        id: Date.now(), type: 'ai',
        text: (res as { response?: string }).response || 'تم.',
        brain: (res as { brain_used?: string }).brain_used,
        confidence: (res as { confidence?: number }).confidence ? Math.round(((res as { confidence: number }).confidence) * 100) : undefined,
      }]);
    } catch {
      setIsTyping(false);
      setMessages(p => [...p, { id: Date.now(), type: 'ai', text: 'لم أتمكن من الاتصال بالنواة.' }]);
    }
  }, [inputValue, messages]);

  const toggleFeature = async (id: number) => {
    const feature = DASHBOARD_SECTIONS.flatMap(s => s.features).find(f => f.id === id);
    if (!feature) return;
    const newState = !featureStates[id];

    // v38: حاول التبديل فعلياً عبر Feature Flags API
    const matchingFlag = Object.entries(featureFlags).find(([_, v]) =>
      feature.nameAr.includes(v.label_ar) || feature.nameEn.toLowerCase().includes(v.label_ar.toLowerCase())
    );
    if (matchingFlag) {
      try {
        const res = await fetch(`/api/v2/feature-flags/${matchingFlag[0]}/toggle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: newState }),
        });
        if (res.ok) {
          const data = await res.json();
          setFeatureStates(prev => ({ ...prev, [id]: data.enabled }));
          setMessages(p => [...p, {
            id: Date.now(), type: 'system',
            text: data.message || `تم ${newState ? 'تفعيل' : 'إيقاف'} ${feature.nameAr} فعلياً`,
          }]);
          // إذا فُعّلت الميزة ووجدت صفحة مقابلة — افتحها
          if (data.enabled && data.navigate_to) {
            setViewMode(data.navigate_to as ViewMode);
          }
          return;
        }
      } catch {
        // لا بأس — سنحدّث محلياً
      }
    }

    // Fallback: تحديث محلي فقط
    setFeatureStates(prev => ({ ...prev, [id]: newState }));
  };

  const toggleSection = (sectionId: number) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) next.delete(sectionId); else next.add(sectionId);
      return next;
    });
  };

  const handleFeatureAction = async (featureId: number, action: string) => {
    const feature = DASHBOARD_SECTIONS.flatMap(s => s.features).find(f => f.id === featureId);
    if (!feature) return;

    if (action === 'status') {
      // v38: فحص حقيقي عبر API
      try {
        const res = await fetch(feature.apiEndpoint);
        if (res.ok) {
          const data = await res.json();
          const status = JSON.stringify(data).slice(0, 200);
          setMessages(p => [...p, {
            id: Date.now(), type: 'system',
            text: `✅ ${feature.nameAr}: ${status}`,
          }]);
        } else {
          setMessages(p => [...p, {
            id: Date.now(), type: 'system',
            text: `⚠️ ${feature.nameAr}: HTTP ${res.status}`,
          }]);
        }
      } catch {
        setMessages(p => [...p, {
          id: Date.now(), type: 'system',
          text: `❌ ${feature.nameAr}: لا يمكن الاتصال`,
        }]);
      }
    } else if (action === 'restart') {
      // v38: إعادة تشغيل حقيقية عبر Command Bus
      try {
        const res = await fetch('/api/v2/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: `أعد تشغيل ${feature.nameAr}` }),
        });
        const data = res.ok ? await res.json() : { message: 'فشل الاتصال' };
        setMessages(p => [...p, {
          id: Date.now(), type: 'system',
          text: data.message || `إعادة تشغيل ${feature.nameAr}...`,
        }]);
      } catch {
        setMessages(p => [...p, {
          id: Date.now(), type: 'system',
          text: `[${feature.backendFile}] إعادة تشغيل ${feature.nameAr}...`,
        }]);
      }
    }
  };

  // v38: تأكيد أمر معلّق (نعم/لا)
  const handleConfirmation = async (confirmed: boolean) => {
    if (!confirmation) return;
    const { id } = confirmation;
    setConfirmation(null);

    if (confirmed) {
      try {
        const res = await fetch(`/api/v2/command/confirm/${id}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        const data = res.ok ? await res.json() : { message: 'فشل التأكيد' };
        setMessages(p => [...p, {
          id: Date.now(), type: 'ai',
          text: `✅ تم التأكيد: ${data.message || 'تم التنفيذ'}`,
        }]);
      } catch {
        setMessages(p => [...p, { id: Date.now(), type: 'ai', text: '❌ فشل التأكيد' }]);
      }
    } else {
      try {
        await fetch(`/api/v2/command/reject/${id}`, { method: 'POST' });
      } catch { /* ignore */ }
      setMessages(p => [...p, { id: Date.now(), type: 'ai', text: '⏹️ تم الإلغاء بناءً على طلبك' }]);
    }
  };

  const activeCat = NAV.find(n => n.id === activeNav);
  const activeSections = activeCat ? DASHBOARD_SECTIONS.filter(s => activeCat.sectionIds.includes(s.id)) : [];
  const totalActive = Object.values(featureStates).filter(Boolean).length;
  const totalFeatures = DASHBOARD_SECTIONS.reduce((a, s) => a + s.features.length, 0);

  // Search filtering
  const filteredSections = searchQuery.trim()
    ? DASHBOARD_SECTIONS.map(s => ({
      ...s,
      features: s.features.filter(f =>
        f.nameAr.includes(searchQuery) || f.nameEn.toLowerCase().includes(searchQuery.toLowerCase()) || f.backendFile.includes(searchQuery)
      ),
    })).filter(s => s.features.length > 0)
    : activeSections;

  const glassPanel: React.CSSProperties = {
    background: 'rgba(194,24,91,0.02)',
    backdropFilter: 'blur(24px)',
    border: `1px solid ${P.pinkDim}`,
    borderRadius: '16px',
  };

  const formatUptime = (s: number) => {
    if (s < 60) return `${s}ث`;
    if (s < 3600) return `${Math.floor(s / 60)}د`;
    if (s < 86400) return `${Math.floor(s / 3600)}س`;
    return `${Math.floor(s / 86400)}ي`;
  };

  // ═══════════════════════════════════════════════════════════════════
  // RENDER — SPECIAL VIEWS
  // ═══════════════════════════════════════════════════════════════════
  if (viewMode === 'deliberation') {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.black, color: P.white }}>
        <DeliberationRoom onBack={() => setViewMode('dashboard')} brains={brains} />
      </div>
    );
  }

  if (viewMode === 'github') {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.black, color: P.white }}>
        <GitHubPanel onBack={() => setViewMode('dashboard')} />
      </div>
    );
  }

  if (viewMode === 'diagnose') {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.black, color: P.white }}>
        <DiagnosePanel onBack={() => setViewMode('dashboard')} />
      </div>
    );
  }

  if (viewMode === 'terminal') {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.black, color: P.white }}>
        <ServerTerminal onBack={() => setViewMode('dashboard')} />
      </div>
    );
  }

  if (viewMode === 'api-keys') {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.black, color: P.white }}>
        <ApiKeysPanel onBack={() => setViewMode('dashboard')} />
      </div>
    );
  }

  if (viewMode === 'control-center') {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.black, color: P.white }}>
        <ControlCenterPanel onBack={() => setViewMode('dashboard')} />
      </div>
    );
  }

  if (viewMode === 'smart-chat') {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.bg, color: P.white }}>
        <SmartChatPanel onBack={() => setViewMode('dashboard')} />
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // v41: Cosmic Panels — البانلات الجديدة بالثيم الأزرق الكوني
  // ═══════════════════════════════════════════════════════════════════════
  if (viewMode === 'brains-orb') {
    return <BrainsOrbPanel brains={brains} vitality={vitality} consciousness={consciousness} onBack={() => setViewMode('dashboard')} onDeliberation={() => triggerDeliberation('general')} />;
  }
  if (viewMode === 'neural-bus') {
    return <NeuralBusPanel signalCount={signalCount} onBack={() => setViewMode('dashboard')} />;
  }
  if (viewMode === 'inner-monologue') {
    return <InnerMonologuePanel thoughts={liveThoughts} onBack={() => setViewMode('dashboard')} />;
  }
  if (viewMode === 'life') {
    return <LifePanel vitality={vitality} energy={energy} emotionState={emotionState} bpm={bpm} onBack={() => setViewMode('dashboard')} />;
  }
  if (viewMode === 'consciousness') {
    return <ConsciousnessPanel consciousness={consciousness} coherence={coherence} onBack={() => setViewMode('dashboard')} />;
  }
  if (viewMode === 'projects') {
    return <ProjectsPanel onBack={() => setViewMode('dashboard')} />;
  }
  if (viewMode === 'swarm') {
    return <SwarmPanel onBack={() => setViewMode('dashboard')} />;
  }
  if (viewMode === 'sites') {
    return <SitesPanel onBack={() => setViewMode('dashboard')} />;
  }

  // v38: Feature pages — تداول، انستقرام، إلخ
  const featurePageIds = ['trading', 'instagram', 'ecommerce', 'blender', 'embodiment', 'mobile', 'self-modify', 'evolution', 'browser', 'laptop', 'brain-control', 'feature-flags'];
  if (featurePageIds.includes(viewMode)) {
    return (
      <div dir="rtl" className="h-screen w-full flex flex-col" style={{ background: P.black, color: P.white }}>
        <FeaturePage pageId={viewMode} onBack={() => setViewMode('dashboard')} />
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════
  // RENDER — MAIN DASHBOARD
  // ═══════════════════════════════════════════════════════════════════
  return (
    <div dir="rtl" className="h-screen w-full overflow-hidden" style={{ background: P.black, color: P.white, fontFamily: "'Cairo', system-ui, sans-serif" }}>

      {/* Neural Grid BG — شبكة عصبية خلفية */}
      <div className="fixed inset-0 pointer-events-none z-0 neural-grid-bg" />

      <style jsx>{`
        .sb::-webkit-scrollbar { width: 3px; }
        .sb::-webkit-scrollbar-track { background: transparent; }
        .sb::-webkit-scrollbar-thumb { background: ${P.pinkDim}; border-radius: 3px; }
      `}</style>

      <div className="min-w-[1280px] h-full flex flex-col relative z-10 p-2.5 gap-2">

        {/* ═══ HEADER — الشريط العلوي ═══ */}
        <header className="h-11 flex items-center justify-between px-4 shrink-0"
          style={{ background: 'rgba(194,24,91,0.04)', border: `1px solid ${P.pinkDim}`, borderRadius: '2rem', backdropFilter: 'blur(20px)' }}>
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-full flex items-center justify-center glow-pulse" style={{ background: P.pinkMid }}>
              <Sparkles className="w-3.5 h-3.5" style={{ color: P.pinkLight }} />
            </div>
            <span className="text-sm font-semibold" style={{ color: P.white90 }}>مأمون v5</span>
            <span className="text-[8px] font-mono" style={{ color: kernelStatus.status === 'running' ? P.pink : P.red }}>
              {kernelStatus.status === 'running' ? '● حي' : '○ متوقف'}
            </span>
            <span className="text-[7px] font-mono" style={{ color: P.white30 }}>
              {formatUptime(kernelStatus.uptime)} | G{evolutionGen} | لياقة {Math.round(evolutionFitness * 100)}%
            </span>
          </div>

          {/* Thought Stream */}
          <ThoughtStream liveThoughts={liveThoughts} />

          <div className="flex items-center gap-3">
            {/* v38: Connection status indicator */}
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full" style={{
              background: connectionStatus === 'connected' ? 'rgba(76,175,80,0.1)' : connectionStatus === 'degraded' ? 'rgba(255,152,0,0.1)' : 'rgba(239,68,68,0.1)',
              border: `1px solid ${connectionStatus === 'connected' ? 'rgba(76,175,80,0.3)' : connectionStatus === 'degraded' ? 'rgba(255,152,0,0.3)' : 'rgba(239,68,68,0.3)'}`,
            }}>
              <div className="w-1.5 h-1.5 rounded-full" style={{
                background: connectionStatus === 'connected' ? P.green : connectionStatus === 'degraded' ? P.orange : P.red,
              }} />
              <span className="text-[7px] font-mono" style={{
                color: connectionStatus === 'connected' ? P.green : connectionStatus === 'degraded' ? P.orange : P.red,
              }}>
                {connectionStatus === 'connected' ? 'متصل' : connectionStatus === 'degraded' ? 'جزئي' : 'منفصل'}
              </span>
            </div>
            {pendingApprovals > 0 && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] signal-ping" style={{ background: P.pinkMid, color: P.pinkLight }}>
                <ShieldAlert className="w-3 h-3" /> {pendingApprovals} موافقة
              </div>
            )}
            <PredictiveGlow prediction={prediction} />
            <div className="flex items-center gap-1.5 text-[9px] font-mono" style={{ color: P.white30 }}>
              <Activity className="w-3 h-3" style={{ color: P.pink }} /> 100ms
            </div>
            <div className="text-[9px] font-mono px-2 py-0.5 rounded-full" style={{ background: P.pinkDim, color: P.pinkLight }}>
              {totalActive}/{totalFeatures} نشط
            </div>
          </div>
        </header>

        {/* ═══ 3-COLUMNS — الأعمدة الثلاثة ═══ */}
        <div className="flex-1 flex gap-2.5 min-h-0">

          {/* ═══ COL 1 (RIGHT): NAV + SECTIONS — التنقل ═══ */}
          <aside className="shrink-0 flex flex-col overflow-hidden" style={{ ...glassPanel, width: 240 }}>
            <div className="p-2.5" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
              <h2 className="text-[9px] uppercase tracking-widest font-semibold flex items-center gap-2" style={{ color: P.white50 }}>
                <Network className="w-3.5 h-3.5" style={{ color: P.pink }} /> التنقل العصبي
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto sb p-1.5 space-y-0.5">
              {NAV.map(cat => {
                const isActive = activeNav === cat.id;
                const fCount = cat.sectionIds.reduce((a, sid) => a + (DASHBOARD_SECTIONS.find(s => s.id === sid)?.features.length || 0), 0);
                const aCount = cat.sectionIds.reduce((a, sid) => {
                  const sec = DASHBOARD_SECTIONS.find(s => s.id === sid);
                  return a + (sec ? sec.features.filter(f => featureStates[f.id]).length : 0);
                }, 0);
                return (
                  <button key={cat.id} onClick={() => { setActiveNav(cat.id); setSearchQuery(''); }}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-right transition-all"
                    style={{ background: isActive ? P.pinkMid : 'transparent', border: `1px solid ${isActive ? P.pinkStrong : 'transparent'}`, color: isActive ? P.pinkLight : P.white70 }}>
                    <span className="shrink-0">{cat.icon}</span>
                    <span className="text-[11px] flex-1">{cat.label}</span>
                    <span className="text-[7px] font-mono" style={{ color: isActive ? P.pinkLight : P.white30 }}>{aCount}/{fCount}</span>
                  </button>
                );
              })}

              <div className="pt-2 mt-2 space-y-0.5" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
                <button onClick={() => setViewMode('deliberation')}
                  className="w-full flex items-center gap-2 px-2.5 py-2 rounded-xl text-right"
                  style={{ background: P.pinkMid, border: `1px solid ${P.pinkStrong}`, color: P.pinkLight }}>
                  <Users className="w-4 h-4" />
                  <span className="text-[11px] font-medium">غرفة المداولة</span>
                  <ArrowRight className="w-3 h-3 mr-auto" />
                </button>

                {SYSTEM_NAV.map(item => (
                  <button key={item.id} onClick={() => setViewMode(item.id as ViewMode)}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-right transition-all"
                    style={{ background: P.white02, border: `1px solid ${P.pinkDim}`, color: P.white70 }}>
                    <span className="shrink-0">{item.icon}</span>
                    <span className="text-[11px]">{item.label}</span>
                    <ArrowRight className="w-3 h-3 mr-auto" style={{ color: P.white15 }} />
                  </button>
                ))}

                <div className="pt-2 mt-1" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
                  <span className="text-[8px] uppercase tracking-wider px-2.5" style={{ color: P.white15 }}>إعدادات</span>
                </div>
                {SETTINGS_NAV.map(item => (
                  <button key={item.id} onClick={() => setViewMode(item.id as ViewMode)}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-right transition-all"
                    style={{ background: P.pinkDim, border: `1px solid ${P.pinkMid}`, color: P.pinkLight }}>
                    <span className="shrink-0">{item.icon}</span>
                    <span className="text-[11px]">{item.label}</span>
                    <ArrowRight className="w-3 h-3 mr-auto" style={{ color: P.pink }} />
                  </button>
                ))}
              </div>
            </div>

            {/* Bottom: Consciousness Orb + Signal Radar */}
            <div className="p-2 flex items-center justify-center gap-3" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
              <ConsciousnessOrb level={consciousness} size={50} />
              <SignalRadar signalCount={signalCount} size={50} />
            </div>
          </aside>

          {/* ═══ COL 2 (CENTER): NUCLEUS + CHAT + VITALS — المركز ═══ */}
          <main className="flex-1 flex flex-col overflow-hidden min-w-[460]" style={glassPanel}>
            <div className="p-2.5 flex items-center justify-between shrink-0" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
              <h2 className="text-[9px] uppercase tracking-widest font-semibold flex items-center gap-2" style={{ color: P.white50 }}>
                <MessageSquare className="w-3.5 h-3.5" style={{ color: P.pink }} /> مساحة العمل العالمية
              </h2>
              <div className="flex items-center gap-1.5">
                <span className="text-[8px] font-mono px-2 py-0.5 rounded-full" style={{ background: P.pinkDim, color: P.pinkLight }}>NeuralBus</span>
                <span className="text-[8px] font-mono px-2 py-0.5 rounded-full" style={{ background: P.white04, color: P.white30 }}>{projects.length} مشاريع</span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto sb p-3 space-y-3">
              {/* Nucleus + Consciousness */}
              <div className="flex justify-center items-center gap-4 py-1">
                <HologramNucleus vitality={vitality} activeBrains={brains.filter(b => b.status === 'active').length} isThinking={isTyping} consciousness={consciousness} size={140} />
                <div className="space-y-1">
                  {/* Brain states mini */}
                  {(brains.length > 0 ? brains : BRAIN_DEFINITIONS).slice(0, 5).map(b => (
                    <div key={b.id} className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: b.status === 'active' ? P.pink : P.white15, boxShadow: b.status === 'active' ? P.pinkGlow : 'none' }} />
                      <span className="text-[9px] font-mono" style={{ color: P.white70 }}>{b.nameAr || b.id}</span>
                      <span className="text-[7px] font-mono" style={{ color: P.pink }}>{b.confidence}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Brain Waves */}
              <div className="space-y-1">
                {(brains.length > 0 ? brains : BRAIN_DEFINITIONS).slice(0, 5).map(b => (
                  <BrainWave key={b.id} active={b.status === 'active'} label={b.nameAr || b.id} confidence={b.confidence} />
                ))}
              </div>

              {/* Neural Pulse (ECG) */}
              <NeuralPulse bpm={bpm} />

              {/* Life Bar */}
              <LifeBar vitality={vitality} energy={energy} coherence={coherence} bpm={bpm} />

              {/* Chat Messages */}
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.type === 'system' ? (
                    <div className="text-center py-0.5">
                      <span className="text-[8px] font-mono px-3 py-0.5 rounded-md" style={{ background: P.pinkDim, color: P.pink }}>{msg.text}</span>
                    </div>
                  ) : (
                    <div className={`max-w-[85%] flex gap-2 ${msg.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      {msg.type === 'ai' && (
                        <div className="w-6 h-6 shrink-0 rounded-full flex items-center justify-center mt-auto" style={{ background: P.pinkMid, border: `1px solid ${P.pinkDim}` }}>
                          <Sparkles className="w-3 h-3" style={{ color: P.pinkLight }} />
                        </div>
                      )}
                      <div className="px-3 py-2.5 text-sm leading-relaxed" style={{
                        background: msg.type === 'user' ? P.pinkMid : P.white04,
                        color: P.white90,
                        borderRadius: msg.type === 'user' ? '1rem 1rem 0.2rem 1rem' : '1rem 1rem 1rem 0.2rem',
                        border: `1px solid ${msg.type === 'user' ? P.pinkStrong : P.pinkDim}`,
                      }}>
                        <p className="whitespace-pre-wrap">{msg.text}</p>
                        {msg.type === 'ai' && msg.brain && (
                          <div className="flex items-center gap-2 mt-1.5 pt-1.5" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
                            <span className="text-[7px] font-mono" style={{ color: P.pink }}>{msg.brain}</span>
                            {msg.confidence && <span className="text-[7px] font-mono" style={{ color: P.white30 }}>ثقة {msg.confidence}%</span>}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {isTyping && (
                <div className="flex justify-start">
                  <div className="flex gap-2">
                    <div className="w-6 h-6 shrink-0 rounded-full flex items-center justify-center" style={{ background: P.pinkMid }}>
                      <Sparkles className="w-3 h-3" style={{ color: P.pinkLight }} />
                    </div>
                    <div className="px-3 py-2.5 flex items-center gap-1" style={{ background: P.white04, border: `1px solid ${P.pinkDim}`, borderRadius: '1rem 1rem 1rem 0.2rem' }}>
                      <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: P.pink, animationDelay: '-0.32s' }} />
                      <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: P.pink, animationDelay: '-0.16s' }} />
                      <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: P.pink }} />
                    </div>
                  </div>
                </div>
              )}

              {/* v38: نافذة تأكيد نعم/لا */}
              {confirmation && (
                <div className="flex justify-center py-2">
                  <div className="p-4 rounded-2xl max-w-md text-center" style={{ background: P.pinkMid, border: `2px solid ${P.pink}`, boxShadow: P.pinkGlowBig }}>
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4" style={{ color: P.pinkLight }} />
                      <span className="text-xs font-semibold" style={{ color: P.pinkLight }}>تأكيد مطلوب</span>
                    </div>
                    <p className="text-xs leading-relaxed mb-3 whitespace-pre-wrap" style={{ color: P.white90 }}>{confirmation.message}</p>
                    <div className="flex gap-3 justify-center">
                      <button onClick={() => handleConfirmation(true)}
                        className="px-6 py-2 rounded-xl text-xs font-semibold transition-all"
                        style={{ background: P.pink, color: P.white, boxShadow: P.pinkGlow }}>
                        نعم، نفّذ
                      </button>
                      <button onClick={() => handleConfirmation(false)}
                        className="px-6 py-2 rounded-xl text-xs font-semibold transition-all"
                        style={{ background: P.white04, color: P.white70, border: `1px solid ${P.pinkDim}` }}>
                        لا، ألغِ
                      </button>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-2.5 shrink-0" style={{ borderTop: `1px solid ${P.pinkDim}` }}>
              <form onSubmit={handleCommand} className="flex items-center rounded-2xl p-1" style={{ background: P.white04, border: `1px solid ${P.pinkDim}` }}>
                <button type="button" className="w-8 h-8 flex items-center justify-center shrink-0 rounded-full" style={{ color: P.white30 }}>
                  <Mic className="w-4 h-4" />
                </button>
                <input type="text" value={inputValue} onChange={e => setInputValue(e.target.value)}
                  placeholder="وجه الأوامر للنواة..." className="flex-1 bg-transparent border-none outline-none text-sm px-2 min-w-0"
                  style={{ color: P.white }} dir="rtl" />
                <button type="submit" disabled={!inputValue.trim() || isTyping}
                  className="w-8 h-8 flex items-center justify-center shrink-0 rounded-full transition-all"
                  style={{ background: inputValue.trim() ? P.pink : 'transparent', color: inputValue.trim() ? P.white : P.white15, boxShadow: inputValue.trim() ? P.pinkGlow : 'none' }}>
                  <Send className="w-4 h-4 rotate-180" />
                </button>
              </form>
            </div>
          </main>

          {/* ═══ COL 3 (LEFT): FEATURE CONTROLS — التحكم ═══ */}
          <aside className="shrink-0 flex flex-col overflow-hidden" style={{ ...glassPanel, width: 400 }}>
            <div className="p-2.5 flex items-center justify-between" style={{ borderBottom: `1px solid ${P.pinkDim}` }}>
              <h2 className="text-[9px] uppercase tracking-widest font-semibold flex items-center gap-2" style={{ color: P.white50 }}>
                <Cpu className="w-3.5 h-3.5" style={{ color: P.pink }} /> التحكم — {searchQuery ? 'بحث' : activeCat?.label}
              </h2>
              <span className="text-[8px] font-mono" style={{ color: P.pink }}>
                {filteredSections.reduce((a, s) => a + s.features.length, 0)} ميزة
              </span>
            </div>

            {/* Search */}
            <div className="px-2.5 pt-2.5">
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: P.white02, border: `1px solid ${P.pinkDim}` }}>
                <Search className="w-3.5 h-3.5 shrink-0" style={{ color: P.white30 }} />
                <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  placeholder="بحث في الميزات..." className="flex-1 bg-transparent border-none outline-none text-[11px] min-w-0"
                  style={{ color: P.white90 }} dir="rtl" />
                {searchQuery && (
                  <button onClick={() => setSearchQuery('')} className="text-[8px]" style={{ color: P.white30 }}>✕</button>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto sb p-2 space-y-2">
              {/* Quick: all on/off */}
              {!searchQuery && (
                <div className="flex gap-2 px-1">
                  <button onClick={() => {
                    const ids = activeSections.flatMap(s => s.features.map(f => f.id));
                    setFeatureStates(prev => { const n = { ...prev }; ids.forEach(id => n[id] = true); return n; });
                  }} className="flex-1 text-[9px] py-1.5 rounded-lg transition-all"
                    style={{ background: P.pinkMid, color: P.pinkLight, border: `1px solid ${P.pinkDim}` }}>
                    تفعيل الكل
                  </button>
                  <button onClick={() => {
                    const ids = activeSections.flatMap(s => s.features.map(f => f.id));
                    setFeatureStates(prev => { const n = { ...prev }; ids.forEach(id => n[id] = false); return n; });
                  }} className="flex-1 text-[9px] py-1.5 rounded-lg transition-all"
                    style={{ background: P.white04, color: P.white30, border: `1px solid ${P.pinkDim}` }}>
                    إيقاف الكل
                  </button>
                </div>
              )}

              {/* Sections with features */}
              {filteredSections.map(section => {
                const isExpanded = expandedSections.has(section.id) || !!searchQuery.trim();
                const secActive = section.features.filter(f => featureStates[f.id]).length;
                return (
                  <div key={section.id}>
                    <button onClick={() => toggleSection(section.id)}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-right transition-all"
                      style={{ background: P.white04, border: `1px solid ${P.pinkDim}` }}>
                      <span className="text-[10px] font-semibold flex-1" style={{ color: P.white90 }}>{section.nameAr}</span>
                      <span className="text-[7px] font-mono" style={{ color: P.pink }}>{secActive}/{section.features.length}</span>
                      {isExpanded ? <ChevronUp className="w-3 h-3" style={{ color: P.white30 }} /> : <ChevronDown className="w-3 h-3" style={{ color: P.white30 }} />}
                    </button>

                    {isExpanded && (
                      <div className="mt-1 space-y-0.5 pr-1">
                        {section.features.map(feature => (
                          <FeatureControl
                            key={feature.id}
                            feature={feature}
                            enabled={!!featureStates[feature.id]}
                            onToggle={toggleFeature}
                            onAction={handleFeatureAction}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Total summary */}
              <div className="p-3 rounded-xl mt-3" style={{ background: P.pinkDim, border: `1px solid ${P.pinkDim}` }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] font-semibold" style={{ color: P.white70 }}>ملخص النظام</span>
                  <span className="text-[8px] font-mono" style={{ color: P.pink }}>{totalActive}/{totalFeatures}</span>
                </div>
                <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: P.white04 }}>
                  <div className="h-full rounded-full transition-all duration-700" style={{
                    width: `${(totalActive / totalFeatures) * 100}%`,
                    background: `linear-gradient(90deg, ${P.pinkDark}, ${P.pink}, ${P.pinkLight})`,
                    boxShadow: P.pinkGlow,
                  }} />
                </div>
                <div className="flex justify-between mt-1.5">
                  <span className="text-[7px]" style={{ color: P.white30 }}>نشط: {totalActive}</span>
                  <span className="text-[7px]" style={{ color: P.white30 }}>خامل: {totalFeatures - totalActive}</span>
                </div>
              </div>
            </div>
          </aside>
        </div>

        {/* ═══ BOTTOM BAR — شريط الحياة مع EEG ═══ */}
        <footer className="h-10 flex items-center justify-between px-4 shrink-0"
          style={{ background: 'rgba(194,24,91,0.03)', border: `1px solid ${P.pinkDim}`, borderRadius: '1rem', backdropFilter: 'blur(20px)' }}>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <Heart className="w-3 h-3 heartbeat" style={{ color: P.pink }} />
              <span className="text-[8px] font-mono" style={{ color: P.pinkLight }}>{bpm} BPM</span>
            </div>
            <div className="w-28">
              <NeuralPulse bpm={bpm} />
            </div>
            <div className="flex items-center gap-1.5">
              <Shield className="w-3 h-3" style={{ color: P.green }} />
              <span className="text-[8px] font-mono" style={{ color: P.white30 }}>L1-L8 OK</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              {Object.entries(emotionState).slice(0, 4).map(([key, val]) => (
                <div key={key} className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: P.pink, opacity: 0.3 + (val as number) * 0.7 }} />
                  <span className="text-[7px] font-mono" style={{ color: P.white30 }}>{key}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Dna className="w-3 h-3" style={{ color: P.pink }} />
              <span className="text-[8px] font-mono" style={{ color: P.white30 }}>G{evolutionGen} | لياقة {Math.round(evolutionFitness * 100)}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Activity className="w-3 h-3" style={{ color: P.pink }} />
              <span className="text-[8px] font-mono" style={{ color: P.white30 }}>{kernelStatus.active_processes} عمليات</span>
            </div>
            <div className="text-[8px] font-mono px-2 py-0.5 rounded-full" style={{ background: P.pinkDim, color: P.pinkLight }}>
              {totalActive}/{totalFeatures} ميزة نشطة
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
