'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useAppStore } from '@/lib/store';
import { fetchBrainStates, fetchLivingVitals, fetchProjects, fetchKernelStatus, type BrainState } from '@/lib/jarvis-api';
import BrainsOrbPanel from '@/components/dashboard/panels/BrainsOrbPanel';
import NeuralBusPanel from '@/components/dashboard/panels/NeuralBusPanel';
import InnerMonologuePanel from '@/components/dashboard/panels/InnerMonologuePanel';
import LifePanel from '@/components/dashboard/panels/LifePanel';
import ConsciousnessPanel from '@/components/dashboard/panels/ConsciousnessPanel';
import ProjectsPanel from '@/components/dashboard/panels/ProjectsPanel';
import SwarmPanel from '@/components/dashboard/panels/SwarmPanel';
import SitesPanel from '@/components/dashboard/panels/SitesPanel';
import ReactMarkdown from 'react-markdown';

// ═══════════════════════════════════════════════════════════════════════════════
// الثيم الكوني — مطابق للموكاب
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

  ring1Color: '#0a9b8a',
  ring2Color: '#0d7bb5',
  ring3Color: '#1e8aad',
  ring4Color: '#0a4a6e',
  ring5Color: '#5a6a80',
};

// ═══════════════════════════════════════════════════════════════════════════════
// تعريف العقد المدارية — 5 حلقات
// ═══════════════════════════════════════════════════════════════════════════════
interface OrbitalNode {
  id: string;
  nameAr: string;
  icon: string;
  ring: number;
  color: string;
  panel: string;
  apiPath?: string;
}

const ORBITAL_NODES: OrbitalNode[] = [
  // الحلقة 1 — الأدمغة الخمسة
  { id: 'neural', nameAr: 'العصبي', icon: '🧠', ring: 1, color: T.ring1Color, panel: 'brains' },
  { id: 'causal', nameAr: 'السببي', icon: '🔗', ring: 1, color: '#2196F3', panel: 'brains' },
  { id: 'symbolic', nameAr: 'الرمزي', icon: '⬡', ring: 1, color: '#0a4a6e', panel: 'brains' },
  { id: 'bayesian', nameAr: 'البيزي', icon: '🎯', ring: 1, color: '#1565C0', panel: 'brains' },
  { id: 'worldmodel', nameAr: 'العالمي', icon: '🌐', ring: 1, color: '#0D47A1', panel: 'brains' },

  // الحلقة 2 — الركائز السبعة
  { id: 'memory', nameAr: 'الذاكرة العرضية', icon: '💾', ring: 2, color: T.ring2Color, panel: 'agi', apiPath: '/api/agi/memory' },
  { id: 'emotions', nameAr: 'المشاعر العميقة', icon: '💖', ring: 2, color: T.ring2Color, panel: 'life' },
  { id: 'embodiment', nameAr: 'الجسد الرقمي', icon: '🤖', ring: 2, color: T.ring2Color, panel: 'agi', apiPath: '/api/embodiment' },
  { id: 'learning', nameAr: 'التعلم من مثال', icon: '📚', ring: 2, color: T.ring2Color, panel: 'agi', apiPath: '/api/agi/learn' },
  { id: 'planning', nameAr: 'التخطيط المقيد', icon: '📋', ring: 2, color: T.ring2Color, panel: 'agi', apiPath: '/api/agi/plan' },
  { id: 'creativity', nameAr: 'الإبداع الأصيل', icon: '💡', ring: 2, color: T.ring2Color, panel: 'agi', apiPath: '/api/creativity' },
  { id: 'bonding', nameAr: 'التعاون البشري', icon: '👥', ring: 2, color: T.ring2Color, panel: 'life' },

  // الحلقة 3 — القدرات الاثنا عشر
  { id: 'code', nameAr: 'البرمجة', icon: '⌨️', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'content', nameAr: 'إنشاء المحتوى', icon: '✍️', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'business', nameAr: 'تحليل الأعمال', icon: '📊', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'sites', nameAr: 'التحكم بالمواقع', icon: '🌍', ring: 3, color: T.ring3Color, panel: 'sites' },
  { id: 'tools', nameAr: 'الأدوات', icon: '🔧', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'reflection', nameAr: 'التأمل الذاتي', icon: '🪞', ring: 3, color: T.ring3Color, panel: 'consciousness' },
  { id: 'social', nameAr: 'وسائل التواصل', icon: '📱', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'blender', nameAr: 'بلندر 3D', icon: '🎨', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'trading', nameAr: 'التداول', icon: '📈', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'browser', nameAr: 'المتصفح', icon: '🖥️', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'laptop', nameAr: 'اللابتوب', icon: '💻', ring: 3, color: T.ring3Color, panel: 'capability' },
  { id: 'ecommerce', nameAr: 'المتجر', icon: '🛒', ring: 3, color: T.ring3Color, panel: 'capability' },

  // الحلقة 4 — الأنظمة الحية الستة
  { id: 'vitals', nameAr: 'المؤشرات الحيوية', icon: '💓', ring: 4, color: T.ring4Color, panel: 'life' },
  { id: 'emotional_mem', nameAr: 'الذاكرة العاطفية', icon: '🧠', ring: 4, color: T.ring4Color, panel: 'life' },
  { id: 'deep_bond', nameAr: 'الارتباط العميق', icon: '🤝', ring: 4, color: T.ring4Color, panel: 'life' },
  { id: 'reflexes', nameAr: 'ردود الفعل', icon: '⚡', ring: 4, color: T.ring4Color, panel: 'life' },
  { id: 'autonomic', nameAr: 'الجهاز التلقائي', icon: '🫀', ring: 4, color: T.ring4Color, panel: 'life' },
  { id: 'monologue', nameAr: 'الحوار الداخلي', icon: '💭', ring: 4, color: T.ring4Color, panel: 'monologue' },

  // الحلقة 5 — الأنظمة/المشاريع
  { id: 'neuralbus', nameAr: 'الناقل العصبي', icon: '📡', ring: 5, color: T.ring5Color, panel: 'neuralbus' },
  { id: 'swarm', nameAr: 'السرب', icon: '🐝', ring: 5, color: T.ring5Color, panel: 'swarm' },
  { id: 'consciousness_sys', nameAr: 'الوعي', icon: '👁️', ring: 5, color: T.ring5Color, panel: 'consciousness' },
  { id: 'projects', nameAr: 'المشاريع', icon: '📁', ring: 5, color: T.ring5Color, panel: 'projects' },
  { id: 'deploy', nameAr: 'النشر', icon: '🚀', ring: 5, color: T.ring5Color, panel: 'sites' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// حلقة مدارية واحدة (مكون فرعي)
// ═══════════════════════════════════════════════════════════════════════════════
interface OrbitalRingProps {
  nodes: OrbitalNode[];
  radius: number;
  centerX: number;
  centerY: number;
  tick: number;
  selectedNode: string | null;
  hoveredNode: string | null;
  winnerNode: string;
  onNodeClick: (id: string) => void;
  onNodeHover: (id: string | null) => void;
  speedFactor: number;
  ringColor: string;
}

function OrbitalRing({
  nodes, radius, centerX, centerY, tick,
  selectedNode, hoveredNode, winnerNode,
  onNodeClick, onNodeHover, speedFactor, ringColor,
}: OrbitalRingProps) {
  const angleStep = (2 * Math.PI) / nodes.length;

  return (
    <g>
      {/* حلقة المدار */}
      <circle
        cx={centerX} cy={centerY} r={radius}
        fill="none" stroke={ringColor} strokeWidth={0.5}
        strokeOpacity={0.15}
        strokeDasharray="4 8"
      />

      {/* العقد */}
      {nodes.map((node, i) => {
        const angle = tick * speedFactor + i * angleStep - Math.PI / 2;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);

        const isSelected = selectedNode === node.id;
        const isHovered = hoveredNode === node.id;
        const isWinner = winnerNode === node.id;
        const pulse = isSelected ? 1.2 : isWinner ? 1 + 0.08 * Math.sin(tick * 3) : 1;
        const nodeRadius = isSelected ? 16 : isHovered ? 14 : 12;

        return (
          <g key={node.id} onClick={() => onNodeClick(node.id)}
             onMouseEnter={() => onNodeHover(node.id)}
             onMouseLeave={() => onNodeHover(null)}
             style={{ cursor: 'pointer' }}>

            {/* خيط متوهج من المركز للعقدة */}
            <line
              x1={centerX} y1={centerY} x2={x} y2={y}
              stroke={isSelected ? node.color : ringColor}
              strokeWidth={isSelected ? 1.5 : 0.5}
              strokeOpacity={isSelected ? 0.5 : isHovered ? 0.25 : 0.08}
            />

            {/* جسيم ضوئي على الخيط */}
            {(isSelected || isWinner) && (
              <circle
                cx={centerX + (x - centerX) * (0.5 + 0.3 * Math.sin(tick * 4))}
                cy={centerY + (y - centerY) * (0.5 + 0.3 * Math.sin(tick * 4))}
                r={2} fill={node.color} opacity={0.6 + 0.4 * Math.sin(tick * 5)}
              />
            )}

            {/* هالة العقدة المختارة */}
            {isSelected && (
              <circle cx={x} cy={y} r={nodeRadius + 8}
                fill="none" stroke={node.color} strokeWidth={2}
                strokeOpacity={0.3 + 0.2 * Math.sin(tick * 3)} />
            )}

            {/* هالة الفائز */}
            {isWinner && !isSelected && (
              <circle cx={x} cy={y} r={nodeRadius + 6 * pulse}
                fill="none" stroke={T.primary} strokeWidth={1.5}
                strokeOpacity={0.3 + 0.3 * Math.sin(tick * 2)} />
            )}

            {/* الدائرة الأساسية */}
            <circle cx={x} cy={y} r={nodeRadius * pulse}
              fill={isSelected ? `${node.color}40` : isHovered ? `${node.color}20` : `${node.color}10`}
              stroke={isSelected ? node.color : isHovered ? node.color : ringColor}
              strokeWidth={isSelected ? 2 : 1}
              strokeOpacity={isSelected ? 0.8 : isHovered ? 0.5 : 0.3}
            />

            {/* الأيقونة */}
            <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="central"
              fontSize={isSelected ? 14 : 11} style={{ pointerEvents: 'none' }}>
              {node.icon}
            </text>

            {/* الاسم (يظهر عند التحويم أو الاختيار) */}
            {(isSelected || isHovered) && (
              <text x={x} y={y + nodeRadius + 12} textAnchor="middle"
                fill={T.white90} fontSize={9} fontWeight="600"
                style={{ pointerEvents: 'none' }}>
                {node.nameAr}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// المكون الرئيسي — مركز مأمون المداري
// ═══════════════════════════════════════════════════════════════════════════════
export default function MamounCommandCenter() {
  // ─── State ────────────────────────────────────────────────────
  const messages = useAppStore((s) => s.messages);
  const isThinking = useAppStore((s) => s.isThinking);
  const sendMessage = useAppStore((s) => s.sendMessage);
  const addMessage = useAppStore((s) => s.addMessage);
  const setThinking = useAppStore((s) => s.setThinking);
  const clearChat = useAppStore((s) => s.clearChat);
  const updateDeliberationData = useAppStore((s) => s.updateDeliberationData);
  const defaultModel = useAppStore((s) => s.defaultModel);
  const isConscious = useAppStore((s) => s.isConscious);

  const [inputText, setInputText] = useState('');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [winnerIndex, setWinnerIndex] = useState(0);
  const [brainData, setBrainData] = useState<BrainState[]>([]);
  const [vitality, setVitality] = useState(75);
  const [consciousness, setConsciousness] = useState(0.7);
  const [signalCount, setSignalCount] = useState(0);
  const [projectCount, setProjectCount] = useState(0);
  const [ripple, setRipple] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ─── نبض الأنيميشن ─────────────────────────────────────────
  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 50);
    return () => clearInterval(iv);
  }, []);

  // ─── دوران الدماغ الفائز ──────────────────────────────────
  useEffect(() => {
    const iv = setInterval(() => setWinnerIndex(w => (w + 1) % 5), 4000);
    return () => clearInterval(iv);
  }, []);

  // ─── جلب البيانات الحية ───────────────────────────────────
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
        }
        if (vitalsRes.status === 'fulfilled') {
          const d = vitalsRes.value as Record<string, unknown>;
          setVitality(Math.round((d.vitality as number) || 75));
        }
        if (projectsRes.status === 'fulfilled' && projectsRes.value?.projects?.length) {
          setProjectCount(projectsRes.value.projects.length);
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

  // ─── عداد إشارات الناقل ────────────────────────────────────
  useEffect(() => {
    const iv = setInterval(() => setSignalCount(s => s + Math.floor(Math.random() * 3)), 2000);
    return () => clearInterval(iv);
  }, []);

  // ─── رسم الخيوط العصبية (Canvas) ──────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const w = canvas.width = canvas.offsetWidth || 800;
    const h = canvas.height = canvas.offsetHeight || 600;

    ctx.fillStyle = 'transparent';
    ctx.clearRect(0, 0, w, h);

    const threads = 20;
    for (let i = 0; i < threads; i++) {
      const x1 = Math.random() * w;
      const y1 = Math.random() * h;
      const x2 = Math.random() * w;
      const y2 = Math.random() * h;
      const opacity = 0.02 + 0.04 * Math.sin(tick * 0.02 + i);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.bezierCurveTo(
        x1 + (x2 - x1) * 0.3, y1 + (y2 - y1) * 0.1,
        x1 + (x2 - x1) * 0.7, y1 + (y2 - y1) * 0.9,
        x2, y2
      );
      ctx.strokeStyle = `rgba(10,74,110,${opacity})`;
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }

    for (let i = 0; i < 8; i++) {
      const x = (Math.sin(tick * 0.01 + i * 2.1) * 0.4 + 0.5) * w;
      const y = (Math.cos(tick * 0.008 + i * 1.7) * 0.4 + 0.5) * h;
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(13,123,181,${0.2 + 0.15 * Math.sin(tick * 0.04 + i)})`;
      ctx.fill();
    }
  }, [tick]);

  // ─── تمرير الرسائل ────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ─── تحديد العقدة المختارة ────────────────────────────────
  const selectedPanel = useMemo(() => {
    if (!selectedNode) return 'brains';
    const node = ORBITAL_NODES.find(n => n.id === selectedNode);
    return node?.panel || 'brains';
  }, [selectedNode]);

  // ─── تحديد الدماغ الفائز ──────────────────────────────────
  const winnerNodeId = useMemo(() => {
    const ring1 = ORBITAL_NODES.filter(n => n.ring === 1);
    return ring1[winnerIndex % ring1.length]?.id || 'neural';
  }, [winnerIndex]);

  // ─── إرسال الرسالة ────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = inputText.trim();
    if (!text) return;
    sendMessage(text);
    setInputText('');

    // تموج من المركز
    setRipple(Date.now());

    // تحديد العقدة المناسبة بناءً على النص
    const lower = text.toLowerCase();
    if (lower.includes('دماغ') || lower.includes('عصبي') || lower.includes('فكر')) {
      setSelectedNode('neural');
    } else if (lower.includes('مشروع') || lower.includes('بناء') || lower.includes('طور')) {
      setSelectedNode('projects');
    } else if (lower.includes('حالة') || lower.includes('صحة') || lower.includes('حيوية')) {
      setSelectedNode('vitals');
    } else if (lower.includes('وعي') || lower.includes('إدراك')) {
      setSelectedNode('consciousness_sys');
    } else if (lower.includes('ناقل') || lower.includes('إشارة')) {
      setSelectedNode('neuralbus');
    } else if (lower.includes('سرب') || lower.includes('وكيل')) {
      setSelectedNode('swarm');
    }

    try {
      const chatHistory = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await fetch('/api/mamoun-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, model: defaultModel, context: {} }),
      });

      if (response.ok) {
        const data = await response.json();
        addMessage({
          id: data.id || `resp-${Date.now()}`,
          role: 'assistant',
          content: data.content || 'لم أتمكن من معالجة طلبك.',
          timestamp: Date.now(),
          brain: data.brain || data.winning_brain,
          confidence: data.confidence,
          metadata: {
            ...data.metadata,
            brain_responses: data.brain_responses,
            consensus_level: data.consensus_level,
            cjs: data.cjs,
            conflict_detected: data.conflict_detected,
            mirror_reflection: data.mirror_reflection,
            source: data.source,
          },
        });

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
      } else {
        addMessage({
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: 'عذراً، حدث خطأ في الاتصال.',
          timestamp: Date.now(),
          confidence: 0.1,
        });
      }
    } catch {
      addMessage({
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'عذراً، لم أتمكن من الاتصال بالخادم.',
        timestamp: Date.now(),
        confidence: 0.1,
      });
    }
    setThinking(false);
  }, [inputText, messages, defaultModel, sendMessage, addMessage, setThinking, updateDeliberationData]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }, [handleSend]);

  // ─── تنسيق الوقت ─────────────────────────────────────────
  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  };

  // ─── حلقات المدار ─────────────────────────────────────────
  const ringNodes = useMemo(() => ({
    1: ORBITAL_NODES.filter(n => n.ring === 1),
    2: ORBITAL_NODES.filter(n => n.ring === 2),
    3: ORBITAL_NODES.filter(n => n.ring === 3),
    4: ORBITAL_NODES.filter(n => n.ring === 4),
    5: ORBITAL_NODES.filter(n => n.ring === 5),
  }), []);

  // ─── أبعاد المركز المداري ─────────────────────────────────
  const orbitalSize = 240;
  const ocx = orbitalSize / 2;
  const ocy = orbitalSize / 2;

  // ─── نبض تنفسي المركز ─────────────────────────────────────
  const breathe = 1 + 0.03 * Math.sin(tick * 0.07);

  // ═══════════════════════════════════════════════════════════════
  // الرسم
  // ═══════════════════════════════════════════════════════════════
  return (
    <div dir="rtl" style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', width: '100vw',
      background: T.bg, color: T.text,
      fontFamily: "'Cairo', 'Tajawal', 'Space Grotesk', system-ui, sans-serif",
      overflow: 'hidden',
    }}>
      {/* ─── المنطقة الرئيسية ─── */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>

        {/* ═══════ الشات (يسار 30%) ═══════ */}
        <div style={{
          width: '30%', minWidth: 320, maxWidth: 480,
          display: 'flex', flexDirection: 'column',
          background: T.chatBg,
          borderLeft: `1px solid ${T.white08}`,
        }}>
          {/* رأس الشات */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '12px 16px',
            borderBottom: `1px solid ${T.white08}`,
            background: `${T.chatBg}`,
          }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: isConscious ? T.accent : T.red,
              boxShadow: isConscious ? T.accentGlow : 'none',
            }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: T.white }}>العقل الخارق</span>
            <span style={{ fontSize: 10, color: T.textDim, flex: 1 }}>مأمون v40.0</span>
            <button onClick={clearChat} style={{
              background: T.primaryDim, border: `1px solid ${T.white08}`,
              color: T.textDim, borderRadius: 6, padding: '2px 8px',
              cursor: 'pointer', fontSize: 9,
            }}>مسح</button>
          </div>

          {/* ─── المركز المداري (SVG) ─── */}
          <div style={{
            padding: '8px 16px',
            display: 'flex', justifyContent: 'center',
            position: 'relative',
          }}>
            <svg width={orbitalSize} height={orbitalSize} viewBox={`0 0 ${orbitalSize} ${orbitalSize}`}
              style={{ display: 'block' }}>
              {/* خلفية متوهجة */}
              <defs>
                <radialGradient id="coreGlow">
                  <stop offset="0%" stopColor={T.primary} stopOpacity="0.15" />
                  <stop offset="100%" stopColor={T.primary} stopOpacity="0" />
                </radialGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* تموج عند رسالة جديدة */}
              {ripple > 0 && (
                <circle cx={ocx} cy={ocy} r={20} fill="none" stroke={T.primary}
                  strokeWidth={1} opacity={Math.max(0, 1 - (tick - ripple / 50) * 0.1)}>
                  <animate attributeName="r" from="20" to={orbitalSize / 2} dur="1.5s" fill="freeze" />
                  <animate attributeName="opacity" from="0.4" to="0" dur="1.5s" fill="freeze" />
                </circle>
              )}

              {/* هالة المركز */}
              <circle cx={ocx} cy={ocy} r={45} fill="url(#coreGlow)" />

              {/* المركز — نبض تنفسي */}
              <g transform={`translate(${ocx}, ${ocy}) scale(${breathe})`} style={{ transformOrigin: '0 0' }}>
                <circle cx={0} cy={0} r={30} fill={T.primaryDim}
                  stroke={T.primary} strokeWidth={1.5} strokeOpacity={0.4} />
                {/* نسبة الوعي */}
                <text x={0} y={-6} textAnchor="middle" fill={T.accent}
                  fontSize={16} fontWeight="700">
                  {Math.round(consciousness * 100)}%
                </text>
                <text x={0} y={8} textAnchor="middle" fill={T.textDim}
                  fontSize={8}>مأمون</text>
                <text x={0} y={18} textAnchor="middle" fill={T.textDim}
                  fontSize={7}>{vitality}% حيوية</text>
              </g>

              {/* حلقة الوعي المتقطعة */}
              <circle cx={ocx} cy={ocy} r={38} fill="none"
                stroke={T.primary} strokeWidth={1} strokeOpacity={0.2}
                strokeDasharray="6 10"
                style={{
                  transform: `rotate(${tick * 0.5}deg)`,
                  transformOrigin: `${ocx}px ${ocy}px`,
                }} />

              {/* الحلقات المدارية الخمسة */}
              <OrbitalRing
                nodes={ringNodes[1]} radius={50} centerX={ocx} centerY={ocy}
                tick={tick} selectedNode={selectedNode} hoveredNode={hoveredNode}
                winnerNode={winnerNodeId} onNodeClick={setSelectedNode}
                onNodeHover={setHoveredNode} speedFactor={0.003}
                ringColor={T.ring1Color}
              />
              <OrbitalRing
                nodes={ringNodes[2]} radius={70} centerX={ocx} centerY={ocy}
                tick={tick} selectedNode={selectedNode} hoveredNode={hoveredNode}
                winnerNode={winnerNodeId} onNodeClick={setSelectedNode}
                onNodeHover={setHoveredNode} speedFactor={-0.002}
                ringColor={T.ring2Color}
              />
              <OrbitalRing
                nodes={ringNodes[3]} radius={90} centerX={ocx} centerY={ocy}
                tick={tick} selectedNode={selectedNode} hoveredNode={hoveredNode}
                winnerNode={winnerNodeId} onNodeClick={setSelectedNode}
                onNodeHover={setHoveredNode} speedFactor={0.0015}
                ringColor={T.ring3Color}
              />
              <OrbitalRing
                nodes={ringNodes[4]} radius={105} centerX={ocx} centerY={ocy}
                tick={tick} selectedNode={selectedNode} hoveredNode={hoveredNode}
                winnerNode={winnerNodeId} onNodeClick={setSelectedNode}
                onNodeHover={setHoveredNode} speedFactor={-0.001}
                ringColor={T.ring4Color}
              />
              <OrbitalRing
                nodes={ringNodes[5]} radius={115} centerX={ocx} centerY={ocy}
                tick={tick} selectedNode={selectedNode} hoveredNode={hoveredNode}
                winnerNode={winnerNodeId} onNodeClick={setSelectedNode}
                onNodeHover={setHoveredNode} speedFactor={0.0008}
                ringColor={T.ring5Color}
              />
            </svg>
          </div>

          {/* ─── منطقة الرسائل ─── */}
          <div style={{
            flex: 1, overflowY: 'auto', padding: '8px 12px',
            display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', padding: 20, color: T.textDim, fontSize: 11 }}>
                <div style={{ fontSize: 28, marginBottom: 8 }}>⚡</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: T.primary, marginBottom: 6 }}>العقل الخارق</div>
                <div style={{ lineHeight: 1.8 }}>أنا أتحكم بكل شيء: الباك إند، الفرونت إند، الأدمغة، GitHub، البحث، الإصلاح</div>
                <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'center' }}>
                  {['طوّر نفسك', 'اسحب التحديثات', 'ابحث عن...', 'حلّل نفسك', 'غيّر وضعك لباحث', 'أصلح الأخطاء'].map(cmd => (
                    <span key={cmd} style={{ background: T.primaryDim, border: `1px solid ${T.white08}`, borderRadius: 8, padding: '2px 8px', fontSize: 9, color: T.primary }}>{cmd}</span>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} style={{
                maxWidth: '85%',
                alignSelf: msg.role === 'user' ? 'flex-start' : 'flex-end',
              }}>
                <div style={{
                  padding: '8px 12px',
                  background: msg.role === 'user'
                    ? T.accentMid
                    : T.bubble,
                  border: msg.role === 'user'
                    ? `1px solid ${T.accentStrong}`
                    : `1px solid ${T.primaryDim}`,
                  borderRadius: msg.role === 'user'
                    ? '16px 16px 4px 16px'
                    : '16px 16px 16px 4px',
                }}>
                  {/* شارة الدماغ */}
                  {msg.role === 'assistant' && (msg.brain || msg.confidence) && (
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 4,
                      marginBottom: 4, fontSize: 9,
                    }}>
                      <span style={{ color: T.primary, fontWeight: 600 }}>
                        {msg.brain || 'مأمون'}
                      </span>
                      {msg.confidence && (
                        <span style={{ color: T.textDim }}>
                          {Math.round(msg.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  )}

                  {/* المحتوى */}
                  {msg.role === 'assistant' ? (
                    <div style={{
                      fontSize: 12, lineHeight: 1.8,
                      color: T.text,
                      whiteSpace: 'pre-wrap',
                    }}>
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p style={{
                      fontSize: 12, lineHeight: 1.7,
                      color: T.white90, margin: 0,
                      whiteSpace: 'pre-wrap',
                    }}>{msg.content}</p>
                  )}

                  <div style={{
                    fontSize: 7, color: T.textDim,
                    marginTop: 4, textAlign: msg.role === 'user' ? 'left' : 'right',
                  }}>
                    {formatTime(msg.timestamp)}
                  </div>
                </div>
              </div>
            ))}

            {/* مؤشر التفكير الحي — 5 أدمغة تتنافس */}
            {isThinking && (
              <div style={{ alignSelf: 'flex-end', width: '85%' }}>
                <div style={{
                  padding: '10px 16px',
                  background: T.bubble,
                  border: `1px solid ${T.primaryStrong}`,
                  borderRadius: '16px 16px 16px 4px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <div style={{ fontSize: 12, color: T.primary, fontWeight: 700 }}>🧠 أدمغة مأمون تتنافس...</div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {['عصبي', 'سببي', 'رمزي', 'بيزي', 'عالمي'].map((name, i) => {
                      const isActive = (Math.floor(tick / 8) % 5) === i;
                      return (
                        <div key={name} style={{
                          padding: '2px 6px',
                          borderRadius: 6,
                          fontSize: 9,
                          background: isActive ? T.primaryMid : T.primaryDim,
                          color: isActive ? T.white : T.textDim,
                          border: isActive ? `1px solid ${T.primary}` : `1px solid ${T.white08}`,
                          transition: 'all 0.2s',
                          fontWeight: isActive ? 700 : 400,
                          boxShadow: isActive ? T.primaryGlow : 'none',
                        }}>{name}</div>
                      );
                    })}
                  </div>
                  <div style={{ display: 'flex', gap: 3, marginTop: 8, alignItems: 'center' }}>
                    {[0, 1, 2, 3, 4].map(i => (
                      <div key={i} style={{
                        width: 4, height: 4, borderRadius: '50%',
                        background: T.primary,
                        opacity: 0.3 + 0.7 * Math.sin(tick * 0.12 + i * 0.6),
                        transition: 'opacity 0.1s',
                      }} />
                    ))}
                    <span style={{ fontSize: 8, color: T.textDim, marginRight: 4 }}>مداولة جارية</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ─── حقل الإدخال ─── */}
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
                placeholder="اكتب رسالتك هنا"
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
              <button onClick={handleSend}
                disabled={isThinking || !inputText.trim()}
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
                }}>
                ➤
              </button>
            </div>
          </div>

          {/* ─── شريط المقاييس ─── */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '6px 16px',
            borderTop: `1px solid ${T.white04}`,
            fontSize: 10, color: T.textDim,
          }}>
            <span>🧠 {brainData.length || 5}</span>
            <span>⚡ {vitality}%</span>
            <span>📡 {signalCount}</span>
            {selectedNode && (
              <span style={{ color: T.primary, fontWeight: 600 }}>
                {ORBITAL_NODES.find(n => n.id === selectedNode)?.icon}{' '}
                {ORBITAL_NODES.find(n => n.id === selectedNode)?.nameAr}
              </span>
            )}
          </div>
        </div>

        {/* ═══════ اللوحة الديناميكية (يمين 70%) ═══════ */}
        <div style={{
          flex: 1, position: 'relative',
          background: T.bg, overflow: 'hidden',
        }}>
          {/* خلفية الخيوط العصبية */}
          <canvas ref={canvasRef} style={{
            position: 'absolute', top: 0, left: 0,
            width: '100%', height: '100%',
            pointerEvents: 'none', opacity: 0.6,
          }} />

          {/* المحتوى الديناميكي */}
          <div style={{ position: 'relative', zIndex: 1, height: '100%' }}>
            {selectedPanel === 'brains' && (
              <BrainsOrbPanel
                brains={brainData}
                vitality={vitality}
                consciousness={consciousness}
                onBack={() => setSelectedNode(null)}
              />
            )}
            {selectedPanel === 'neuralbus' && (
              <NeuralBusPanel
                signalCount={signalCount}
                onBack={() => setSelectedNode(null)}
              />
            )}
            {selectedPanel === 'monologue' && (
              <InnerMonologuePanel
                onBack={() => setSelectedNode(null)}
              />
            )}
            {selectedPanel === 'life' && (
              <LifePanel
                vitality={vitality}
                onBack={() => setSelectedNode(null)}
              />
            )}
            {selectedPanel === 'consciousness' && (
              <ConsciousnessPanel
                consciousness={consciousness}
                onBack={() => setSelectedNode(null)}
              />
            )}
            {selectedPanel === 'projects' && (
              <ProjectsPanel
                onBack={() => setSelectedNode(null)}
              />
            )}
            {selectedPanel === 'swarm' && (
              <SwarmPanel
                onBack={() => setSelectedNode(null)}
              />
            )}
            {selectedPanel === 'sites' && (
              <SitesPanel
                onBack={() => setSelectedNode(null)}
              />
            )}
            {/* لوحات عامة للركائز والقدرات */}
            {(selectedPanel === 'agi' || selectedPanel === 'capability') && (
              <GenericDetailPanel
                nodeId={selectedNode}
                onBack={() => setSelectedNode(null)}
              />
            )}
          </div>
        </div>
      </div>

      {/* ─── الشريط السفلي ─── */}
      <div style={{
        height: 36, display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        background: T.chatBg,
        borderTop: `1px solid ${T.white08}`,
        fontSize: 10, color: T.textDim,
      }}>
        <div style={{ display: 'flex', gap: 16 }}>
          <span>NeuralBus: {signalCount} | Active: {brainData.filter(b => b.status === 'active').length || 5} brains</span>
          <span>Projects: {projectCount}</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ width: 12, height: 12, borderRadius: 2, background: T.bg, border: `1px solid ${T.white08}` }} />
          <span style={{ width: 12, height: 12, borderRadius: 2, background: T.primary, border: `1px solid ${T.white08}` }} />
          <span style={{ width: 12, height: 12, borderRadius: 2, background: T.accent, border: `1px solid ${T.white08}` }} />
          <span style={{ width: 12, height: 12, borderRadius: 2, background: T.text, border: `1px solid ${T.white08}` }} />
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// لوحة تفاصيل عامة للركائز والقدرات
// ═══════════════════════════════════════════════════════════════════════════════
function GenericDetailPanel({ nodeId, onBack }: { nodeId: string | null; onBack: () => void }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const node = ORBITAL_NODES.find(n => n.id === nodeId);

  useEffect(() => {
    const load = async () => {
      if (!node?.apiPath) { setLoading(false); return; }
      try {
        const res = await fetch(node.apiPath);
        if (res.ok) {
          const d = await res.json();
          setData(d);
        }
      } catch { /* fallback */ }
      setLoading(false);
    };
    load();
  }, [node?.apiPath]);

  return (
    <div dir="rtl" style={{
      background: T.bg, height: '100%',
      color: T.text, fontFamily: 'Tajawal, sans-serif',
      overflowY: 'auto',
    }}>
      {/* رأس */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '16px 20px',
        borderBottom: `1px solid ${T.white08}`,
      }}>
        <button onClick={onBack} style={{
          background: T.primaryDim,
          border: `1px solid ${T.primaryStrong}`,
          color: T.primary, borderRadius: 8,
          padding: '6px 10px', cursor: 'pointer',
          display: 'flex', alignItems: 'center',
        }}>→</button>
        <span style={{ fontSize: 20 }}>{node?.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: T.white }}>
            {node?.nameAr || 'تفاصيل'}
          </div>
          <div style={{ fontSize: 11, color: T.textDim }}>
            {node?.apiPath || 'نظام داخلي'}
          </div>
        </div>
      </div>

      {/* محتوى */}
      <div style={{ padding: 20 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40, color: T.textDim }}>
            جاري التحميل...
          </div>
        ) : data ? (
          <div style={{
            background: T.chatBg, borderRadius: 12,
            padding: 20, border: `1px solid ${T.white08}`,
          }}>
            <pre style={{
              fontSize: 11, color: T.text,
              whiteSpace: 'pre-wrap', direction: 'ltr',
              textAlign: 'left',
            }}>
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>{node?.icon}</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: T.white, marginBottom: 8 }}>
              {node?.nameAr}
            </div>
            <div style={{ fontSize: 11, color: T.textDim }}>
              هذا النظام يعمل داخلياً — لا يوجد API عام
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
