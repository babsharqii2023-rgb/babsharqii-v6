'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Send, Mic, Brain, Activity, Sparkles, Search, ShieldAlert, Eye, Cpu,
  Network, Zap, Wrench, Bot, Globe, Layers, Heart, Dna, Lightbulb,
  Terminal, Database, Orbit, MessageSquare, Radio, ChevronLeft,
  ArrowRight, Settings, CheckCircle2, XCircle, AlertCircle, Atom,
  RotateCcw, Power, Hexagon, Compass, Cloud, HardDrive,
  BookOpen, Code, GitMerge, Palette, Volume2, Shield,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════
// نظام الألوان — Cosmic Cyan (كما في المواصفات)
// ═══════════════════════════════════════════════════════════════════════
const C = {
  bg: '#080810',
  bgLight: '#0c0c1a',
  card: '#0d0d20',
  cardHover: '#12122a',
  border: 'rgba(13,123,181,0.15)',
  borderStrong: 'rgba(13,123,181,0.35)',
  primary: '#0d7bb5',
  primaryLight: '#1a9de0',
  cyan: '#0a9b8a',
  cyanLight: '#0fc4ad',
  cyanDim: 'rgba(10,155,138,0.08)',
  cyanMid: 'rgba(10,155,138,0.15)',
  cyanStrong: 'rgba(10,155,138,0.3)',
  white: '#e8ecf4',
  white90: 'rgba(232,236,244,0.9)',
  white70: 'rgba(232,236,244,0.7)',
  white50: 'rgba(232,236,244,0.5)',
  white30: 'rgba(232,236,244,0.3)',
  white15: 'rgba(232,236,244,0.15)',
  white08: 'rgba(232,236,244,0.08)',
  white04: 'rgba(232,236,244,0.04)',
  glow: '0 0 12px rgba(10,155,138,0.4)',
  glowBig: '0 0 24px rgba(10,155,138,0.2)',
  green: '#0fc4ad',
  orange: '#e8a838',
  red: '#e84848',
  pink: '#c83878',
};

// ═══════════════════════════════════════════════════════════════════════
// عقد المدار — Orbital Nodes (كل قدرة = عقدة تدور)
// ═══════════════════════════════════════════════════════════════════════
interface OrbitalNode {
  id: string;
  label: string;
  labelAr: string;
  icon: React.ReactNode;
  orbit: number;       // أي مدار (1=داخلي، 2=أوسط، 3=خارجي)
  angle: number;       // زاوية البداية
  color: string;
  panelId: string;     // معرف اللوحة التفصيلية
}

const ORBITAL_NODES: OrbitalNode[] = [
  // المدار الداخلي — الأدمغة
  { id: 'neural', label: 'Neural', labelAr: 'العصبية', icon: <Brain className="w-3.5 h-3.5" />, orbit: 1, angle: 0, color: C.primary, panelId: 'brains' },
  { id: 'causal', label: 'Causal', labelAr: 'السببية', icon: <Network className="w-3.5 h-3.5" />, orbit: 1, angle: 72, color: C.cyan, panelId: 'brains' },
  { id: 'symbolic', label: 'Symbolic', labelAr: 'الرمزية', icon: <Zap className="w-3.5 h-3.5" />, orbit: 1, angle: 144, color: '#7b61ff', panelId: 'brains' },
  { id: 'bayesian', label: 'Bayesian', labelAr: 'البايزية', icon: <Compass className="w-3.5 h-3.5" />, orbit: 1, angle: 216, color: '#e8a838', panelId: 'brains' },
  { id: 'world', label: 'WorldModel', labelAr: 'نموذج العالم', icon: <Globe className="w-3.5 h-3.5" />, orbit: 1, angle: 288, color: '#c83878', panelId: 'brains' },
  // المدار الأوسط — الأنظمة الحية
  { id: 'consciousness', label: 'Consciousness', labelAr: 'الوعي', icon: <Eye className="w-3.5 h-3.5" />, orbit: 2, angle: 30, color: C.cyanLight, panelId: 'consciousness' },
  { id: 'memory', label: 'Memory', labelAr: 'الذاكرة', icon: <Database className="w-3.5 h-3.5" />, orbit: 2, angle: 90, color: C.primaryLight, panelId: 'memory' },
  { id: 'evolution', label: 'Evolution', labelAr: 'التطور', icon: <Dna className="w-3.5 h-3.5" />, orbit: 2, angle: 150, color: '#7b61ff', panelId: 'evolution' },
  { id: 'safety', label: 'Safety', labelAr: 'الأمان', icon: <Shield className="w-3.5 h-3.5" />, orbit: 2, angle: 210, color: C.green, panelId: 'safety' },
  { id: 'living', label: 'Living', labelAr: 'الحياة', icon: <Heart className="w-3.5 h-3.5" />, orbit: 2, angle: 270, color: '#e84848', panelId: 'living' },
  { id: 'hyperagent', label: 'Hyperagent', labelAr: 'الوكيل الفائق', icon: <Layers className="w-3.5 h-3.5" />, orbit: 2, angle: 330, color: C.orange, panelId: 'hyperagent' },
  // المدار الخارجي — القدرات
  { id: 'research', label: 'DeepResearch', labelAr: 'بحث عميق', icon: <Search className="w-3.5 h-3.5" />, orbit: 3, angle: 0, color: C.cyan, panelId: 'research' },
  { id: 'selfmodify', label: 'SelfModify', labelAr: 'تعديل ذاتي', icon: <Code className="w-3.5 h-3.5" />, orbit: 3, angle: 45, color: C.primary, panelId: 'selfmodify' },
  { id: 'tools', label: 'RealTools', labelAr: 'أدوات حقيقية', icon: <Wrench className="w-3.5 h-3.5" />, orbit: 3, angle: 90, color: C.orange, panelId: 'tools' },
  { id: 'agents', label: 'Agents', labelAr: 'وكلاء', icon: <Bot className="w-3.5 h-3.5" />, orbit: 3, angle: 135, color: '#7b61ff', panelId: 'agents' },
  { id: 'terminal', label: 'Terminal', labelAr: 'طرفية', icon: <Terminal className="w-3.5 h-3.5" />, orbit: 3, angle: 180, color: C.cyanLight, panelId: 'terminal' },
  { id: 'projects', label: 'Projects', labelAr: 'مشاريع', icon: <GitMerge className="w-3.5 h-3.5" />, orbit: 3, angle: 225, color: C.green, panelId: 'projects' },
  { id: 'creativity', label: 'Creativity', labelAr: 'إبداع', icon: <Palette className="w-3.5 h-3.5" />, orbit: 3, angle: 270, color: C.pink, panelId: 'creativity' },
  { id: 'voice', label: 'Voice', labelAr: 'صوت', icon: <Volume2 className="w-3.5 h-3.5" />, orbit: 3, angle: 315, color: C.primaryLight, panelId: 'voice' },
];

// ═══════════════════════════════════════════════════════════════════════
// النواة المدارية — Orbital Nucleus (نواة ذرة تتنفس)
// ═══════════════════════════════════════════════════════════════════════
function OrbitalNucleus({
  vitality = 75,
  activeBrains = 5,
  isThinking = false,
  size = 280,
  consciousness = 0.7,
  onNodeClick,
  selectedNode,
}: {
  vitality?: number;
  activeBrains?: number;
  isThinking?: boolean;
  size?: number;
  consciousness?: number;
  onNodeClick?: (node: OrbitalNode) => void;
  selectedNode?: string | null;
}) {
  const [tick, setTick] = useState(0);
  const cx = size / 2;
  const cy = size / 2;

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 60);
    return () => clearInterval(iv);
  }, []);

  const orbitRadii = { 1: size * 0.18, 2: size * 0.3, 3: size * 0.42 };

  const animatedNodes = useMemo(() => {
    return ORBITAL_NODES.map(node => {
      const r = orbitRadii[node.orbit as keyof typeof orbitRadii];
      const speed = node.orbit === 1 ? 0.0015 : node.orbit === 2 ? 0.001 : 0.0007;
      const angle = ((node.angle + tick * speed) * Math.PI) / 180;
      return {
        ...node,
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
        r,
      };
    });
  }, [tick, cx, cy, orbitRadii]);

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="absolute inset-0">
        <defs>
          <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={C.cyan} stopOpacity="0.5" />
            <stop offset="40%" stopColor={C.primary} stopOpacity="0.15" />
            <stop offset="100%" stopColor={C.bg} stopOpacity="0" />
          </radialGradient>
          <filter id="nodeGlow">
            <feGaussianBlur stdDeviation="2" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="coreGlowFilter">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* خلفية التوهج */}
        <circle cx={cx} cy={cy} r={size * 0.45} fill="url(#coreGlow)">
          <animate attributeName="r" values={`${size * 0.4};${size * 0.48};${size * 0.4}`} dur="4s" repeatCount="indefinite" />
        </circle>

        {/* حلقات المدارات */}
        {[1, 2, 3].map(orbit => (
          <circle key={`orbit-${orbit}`} cx={cx} cy={cy} r={orbitRadii[orbit as keyof typeof orbitRadii]}
            fill="none" stroke={C.cyan} strokeWidth="0.4" strokeDasharray="3 8" opacity="0.15">
            <animateTransform attributeName="transform" type="rotate"
              from={`0 ${cx} ${cy}`} to={`${orbit % 2 === 0 ? '-' : ''}360 ${cx} ${cy}`}
              dur={`${30 + orbit * 10}s`} repeatCount="indefinite" />
          </circle>
        ))}

        {/* موجات النبض */}
        {[0, 1, 2].map(i => (
          <circle key={`pulse-${i}`} cx={cx} cy={cy} r={size * 0.1} fill="none" stroke={C.cyan} strokeWidth="0.5" opacity="0">
            <animate attributeName="r" values={`${size * 0.08};${size * 0.45}`} dur="4s" begin={`${i * 1.3}s`} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.3;0" dur="4s" begin={`${i * 1.3}s`} repeatCount="indefinite" />
          </circle>
        ))}

        {/* قوس الحيوية */}
        <circle cx={cx} cy={cy} r={size * 0.46} fill="none" stroke={C.cyan} strokeWidth="2" strokeLinecap="round"
          strokeDasharray={`${(vitality / 100) * 2 * Math.PI * size * 0.46} ${2 * Math.PI * size * 0.46}`}
          transform={`rotate(-90 ${cx} ${cy})`} opacity="0.6" filter="url(#nodeGlow)">
          <animate attributeName="opacity" values="0.4;0.8;0.4" dur="2.5s" repeatCount="indefinite" />
        </circle>

        {/* حلقة الوعي */}
        <circle cx={cx} cy={cy} r={size * 0.44} fill="none" stroke={C.primaryLight} strokeWidth="0.3" strokeDasharray="2 6" opacity="0.1">
          <animateTransform attributeName="transform" type="rotate" from={`0 ${cx} ${cy}`} to={`-360 ${cx} ${cy}`} dur="40s" repeatCount="indefinite" />
        </circle>

        {/* موجات التفكير */}
        {isThinking && [0, 1, 2, 3].map(i => (
          <circle key={`think-${i}`} cx={cx} cy={cy} r={15 + i * 12} fill="none" stroke={C.cyanLight} strokeWidth="0.8" opacity="0">
            <animate attributeName="r" values={`${12 + i * 8};${30 + i * 12}`} dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.5;0" dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite" />
          </circle>
        ))}

        {/* اتصالات الشبكة العصبية بين العقد */}
        {animatedNodes.map((node, i) => {
          // ربط كل عقدة بأقرب عقدتين في نفس المدار
          const sameOrbit = animatedNodes.filter(n => n.orbit === node.orbit && n.id !== node.id);
          return sameOrbit.slice(0, 2).map((other, j) => (
            <line key={`conn-${i}-${j}`} x1={node.x} y1={node.y} x2={other.x} y2={other.y}
              stroke={C.cyan} strokeWidth="0.3" opacity="0.06" />
          ));
        })}

        {/* خطوط من النواة إلى كل عقدة */}
        {animatedNodes.map(node => (
          <line key={`link-${node.id}`} x1={cx} y1={cy} x2={node.x} y2={node.y}
            stroke={node.color} strokeWidth="0.3" opacity={selectedNode === node.id ? 0.3 : 0.05} />
        ))}

        {/* عقد المدار */}
        {animatedNodes.map(node => {
          const isSelected = selectedNode === node.id;
          const nodeRadius = isSelected ? 12 : 8;
          return (
            <g key={node.id} onClick={() => onNodeClick?.(node)} style={{ cursor: 'pointer' }}>
              {/* هالة العقدة */}
              <circle cx={node.x} cy={node.y} r={nodeRadius + 4} fill="none"
                stroke={node.color} strokeWidth="0.5" opacity={isSelected ? 0.4 : 0.1}>
                {isSelected && <animate attributeName="r" values={`${nodeRadius + 2};${nodeRadius + 6};${nodeRadius + 2}`} dur="2s" repeatCount="indefinite" />}
              </circle>
              {/* خلفية العقدة */}
              <circle cx={node.x} cy={node.y} r={nodeRadius}
                fill={isSelected ? `${node.color}30` : C.card}
                stroke={node.color} strokeWidth={isSelected ? 1.5 : 0.5}
                opacity={isSelected ? 1 : 0.7} />
              {/* النقطة المركزية */}
              <circle cx={node.x} cy={node.y} r={2.5} fill={node.color} opacity={isSelected ? 1 : 0.6}>
                {isSelected && <animate attributeName="r" values="2;3;2" dur="1.5s" repeatCount="indefinite" />}
              </circle>
            </g>
          );
        })}

        {/* النقطة المركزية — النواة */}
        <circle cx={cx} cy={cy} r={6} fill={C.cyan} filter="url(#coreGlowFilter)">
          <animate attributeName="r" values="5;7;5" dur="2s" repeatCount="indefinite" />
        </circle>
      </svg>

      {/* نص الحيوية المركزي */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-lg font-bold" style={{ color: C.white, textShadow: C.glow }}>{vitality}%</span>
        <span className="text-[7px] font-mono tracking-widest" style={{ color: C.cyan }}>VITALITY</span>
        <span className="text-[6px] font-mono mt-0.5" style={{ color: C.white30 }}>{Math.round(consciousness * 100)}% AWARE</span>
      </div>

      {/* تسميات العقد — على الأطراف */}
      {animatedNodes.map(node => {
        const isSelected = selectedNode === node.id;
        if (!isSelected) return null;
        return (
          <div key={`label-${node.id}`} className="absolute text-center pointer-events-none"
            style={{
              left: node.x - 30,
              top: node.y - 24,
              width: 60,
            }}>
            <span className="text-[8px] font-mono font-bold" style={{ color: node.color }}>{node.labelAr}</span>
          </div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// لوحة التفاصيل — Detail Panel (يمين 70%)
// ═══════════════════════════════════════════════════════════════════════
function DetailPanel({ panelId, onBack }: { panelId: string; onBack: () => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchPanelData(panelId).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, [panelId]);

  const fetchPanelData = async (id: string) => {
    try {
      const res = await fetch(`/api/mamoun/${id === 'brains' ? 'brains' : id === 'living' ? 'living/vitals' : id === 'consciousness' ? 'consciousness' : id === 'memory' ? 'memory/skills' : id === 'evolution' ? 'evolution/current' : id === 'safety' ? 'safety/laws' : id === 'research' ? 'research/status' : id === 'selfmodify' ? 'self-modify/status' : id === 'tools' ? 'capabilities/status' : id === 'agents' ? 'agent/manifest' : id === 'terminal' ? 'terminal/status' : id === 'projects' ? 'projects' : id === 'hyperagent' ? 'hyperagent/status' : id === 'creativity' ? 'ideas' : 'kernel/status'}`);
      if (res.ok) return await res.json();
    } catch {}
    return null;
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden" style={{ background: C.bg }}>
      <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: `1px solid ${C.border}` }}>
        <button onClick={onBack} className="flex items-center gap-2 text-xs" style={{ color: C.cyan }}>
          <ChevronLeft className="w-3.5 h-3.5" /> الرئيسية
        </button>
        <h2 className="text-xs font-semibold tracking-wider uppercase" style={{ color: C.white70 }}>{panelId}</h2>
        <div className="w-6" />
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Activity className="w-5 h-5 animate-spin" style={{ color: C.cyan }} />
            <span className="text-xs mr-3" style={{ color: C.white30 }}>جارٍ التحميل...</span>
          </div>
        ) : data ? (
          renderPanelContent(panelId, data)
        ) : (
          <div className="text-center py-12" style={{ color: C.white30 }}>
            <AlertCircle className="w-8 h-8 mx-auto mb-3" style={{ color: C.orange }} />
            <span className="text-xs">لا توجد بيانات — تأكد من اتصال الباك إند</span>
          </div>
        )}
      </div>
    </div>
  );
}

function renderPanelContent(panelId: string, data: any) {
  const entries = Object.entries(data).slice(0, 30);
  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="p-3 rounded-lg" style={{ background: C.card, border: `1px solid ${C.border}` }}>
          <span className="text-[9px] font-mono block mb-1" style={{ color: C.cyan }}>{key}</span>
          <span className="text-[11px]" style={{ color: C.white70 }}>
            {typeof value === 'object' ? JSON.stringify(value).slice(0, 200) : String(value).slice(0, 200)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// رسائل المحادثة — Chat Messages
// ═══════════════════════════════════════════════════════════════════════
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  brain?: string;
  confidence?: number;
  timestamp: number;
}

// ═══════════════════════════════════════════════════════════════════════
// المكون الرئيسي — Orbital Chat Panel
// ═══════════════════════════════════════════════════════════════════════
export default function OrbitalChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [vitality, setVitality] = useState(75);
  const [consciousness, setConsciousness] = useState(0.7);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // جلب حالة النظام
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/mamoun/living/vitals');
        if (res.ok) {
          const d = await res.json();
          setVitality(Math.round(d.vitality ?? d.energy ?? 75));
        }
      } catch {}
      try {
        const res = await fetch('/api/mamoun/consciousness');
        if (res.ok) {
          const d = await res.json();
          setConsciousness(d.level ?? d.consciousness_level ?? 0.7);
        }
      } catch {}
    };
    fetchStatus();
    const iv = setInterval(fetchStatus, 10000);
    return () => clearInterval(iv);
  }, []);

  // سكرول تلقائي
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // إرسال رسالة
  const sendMessage = async () => {
    if (!input.trim() || isThinking) return;
    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    try {
      const res = await fetch('/api/mamoun-chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify({ message: userMsg.content, stream: true }),
      });

      if (!res.ok) {
        // محاولة عبر البروكسي العادي
        const res2 = await fetch('/api/mamoun/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMsg.content }),
        });
        if (res2.ok) {
          const data = await res2.json();
          setMessages(prev => [...prev, {
            id: `msg_${Date.now()}_resp`,
            role: 'assistant',
            content: data.content || data.response || JSON.stringify(data),
            brain: data.brain || 'neural',
            confidence: data.confidence || 0.85,
            timestamp: Date.now(),
          }]);
        } else {
          throw new Error('Backend unavailable');
        }
      } else {
        // SSE stream
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let brain = 'neural';
        let confidence = 0.85;

        if (reader) {
          let buffer = '';
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const event = JSON.parse(line.slice(6));
                  if (event.type === 'token' && event.content) {
                    fullContent += event.content;
                  } else if (event.type === 'done') {
                    brain = event.brain || brain;
                    confidence = event.confidence || confidence;
                  } else if (event.content) {
                    fullContent += event.content;
                  }
                } catch {
                  // raw text
                  const raw = line.slice(6).trim();
                  if (raw) fullContent += raw;
                }
              }
            }
          }
        }

        if (fullContent) {
          setMessages(prev => [...prev, {
            id: `msg_${Date.now()}_resp`,
            role: 'assistant',
            content: fullContent,
            brain,
            confidence,
            timestamp: Date.now(),
          }]);
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: `msg_${Date.now()}_err`,
        role: 'system',
        content: '⚠️ لا يمكن الاتصال بالباك إند — تأكد من تشغيله على المنفذ 8000',
        timestamp: Date.now(),
      }]);
    }

    setIsThinking(false);
  };

  // نقر عقدة مدارية
  const handleNodeClick = (node: OrbitalNode) => {
    setSelectedNode(node.id);
    setActivePanel(node.panelId);
  };

  const handleBackToChat = () => {
    setActivePanel(null);
    setSelectedNode(null);
  };

  return (
    <div className="flex h-full w-full" style={{ background: C.bg }}>
      {/* ═══ العمود الأيسر 30% — المحادثة + النواة المدارية ═══ */}
      <div className="flex flex-col" style={{ width: '30%', minWidth: 320, borderRight: `1px solid ${C.border}` }}>
        {/* النواة المدارية */}
        <div className="flex items-center justify-center py-3" style={{ background: C.bgLight, borderBottom: `1px solid ${C.border}` }}>
          <OrbitalNucleus
            vitality={vitality}
            activeBrains={5}
            isThinking={isThinking}
            consciousness={consciousness}
            onNodeClick={handleNodeClick}
            selectedNode={selectedNode}
          />
        </div>

        {/* منطقة المحادثة */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3" style={{ background: C.bg }}>
          {messages.length === 0 && (
            <div className="text-center py-6">
              <Atom className="w-8 h-8 mx-auto mb-3" style={{ color: C.cyan, opacity: 0.3 }} />
              <p className="text-[11px]" style={{ color: C.white30 }}>مأمون v40.0 — العقل الخارق</p>
              <p className="text-[9px] mt-1" style={{ color: C.white15 }}>انقر على عقدة مدارية أو اكتب رسالة</p>
            </div>
          )}
          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className="max-w-[90%] p-2.5 rounded-lg" style={{
                background: msg.role === 'user' ? C.cyanMid : msg.role === 'system' ? 'rgba(232,168,56,0.1)' : C.card,
                border: `1px solid ${msg.role === 'user' ? C.cyanStrong : msg.role === 'system' ? 'rgba(232,168,56,0.2)' : C.border}`,
              }}>
                {msg.brain && (
                  <span className="text-[7px] font-mono block mb-1" style={{ color: C.cyan }}>
                    🧠 {msg.brain} {msg.confidence ? `— ${Math.round(msg.confidence * 100)}%` : ''}
                  </span>
                )}
                <span className="text-[11px] leading-relaxed" style={{ color: msg.role === 'system' ? C.orange : C.white90, whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </span>
              </div>
            </div>
          ))}
          {isThinking && (
            <div className="flex justify-start">
              <div className="p-2.5 rounded-lg" style={{ background: C.card, border: `1px solid ${C.border}` }}>
                <span className="text-[11px]" style={{ color: C.cyan }}>● ● ● يفكر</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* حقل الإدخال */}
        <div className="p-3" style={{ background: C.bgLight, borderTop: `1px solid ${C.border}` }}>
          <form onSubmit={e => { e.preventDefault(); sendMessage(); }} className="flex items-center gap-2">
            <button type="button" onClick={() => setIsListening(!isListening)}
              className="w-8 h-8 flex items-center justify-center rounded-full shrink-0"
              style={{ background: isListening ? C.cyanMid : C.white04, border: `1px solid ${isListening ? C.cyanStrong : C.border}` }}>
              <Mic className="w-3.5 h-3.5" style={{ color: isListening ? C.cyan : C.white30 }} />
            </button>
            <input type="text" value={input} onChange={e => setInput(e.target.value)}
              placeholder="اسأل مأمون..." dir="auto"
              className="flex-1 px-3 py-2 rounded-lg text-[12px] outline-none"
              style={{ background: C.card, border: `1px solid ${C.border}`, color: C.white }}
            />
            <button type="submit" disabled={!input.trim() || isThinking}
              className="w-8 h-8 flex items-center justify-center rounded-full shrink-0"
              style={{ background: input.trim() ? C.cyan : C.white08, color: input.trim() ? C.bg : C.white30 }}>
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>

      {/* ═══ العمود الأيمن 70% — لوحة التفاصيل ═══ */}
      <div className="flex-1 flex flex-col" style={{ background: C.bg }}>
        {activePanel ? (
          <DetailPanel panelId={activePanel} onBack={handleBackToChat} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center" style={{ background: C.bg }}>
            <div className="text-center space-y-4 max-w-md">
              <Hexagon className="w-16 h-16 mx-auto" style={{ color: C.cyan, opacity: 0.15 }} />
              <h2 className="text-lg font-bold" style={{ color: C.white70 }}>العقل الخارق — مأمون</h2>
              <p className="text-xs leading-relaxed" style={{ color: C.white30 }}>
                انقر على أي عقدة في النواة المدارية لفتح لوحة التحكم التفصيلية.
                <br />كل عقدة تمثل قدرة كاملة يملكها مأمون.
              </p>
              <div className="grid grid-cols-3 gap-3 mt-6">
                {[
                  { icon: <Brain className="w-5 h-5" />, label: '5 أدمغة', desc: 'تفكير متنوع' },
                  { icon: <Search className="w-5 h-5" />, label: 'بحث عميق', desc: 'تحقق متقاطع' },
                  { icon: <Code className="w-5 h-5" />, label: 'تعديل ذاتي', desc: 'شفاء + تطور' },
                  { icon: <Wrench className="w-5 h-5" />, label: '7 أدوات', desc: 'حقيقية تشغيلية' },
                  { icon: <Shield className="w-5 h-5" />, label: '8 قوانين', desc: 'أمان صارم' },
                  { icon: <Dna className="w-5 h-5" />, label: '31 ركيزة', desc: 'ذكاء عام' },
                ].map((item, i) => (
                  <div key={i} className="p-3 rounded-lg text-center" style={{ background: C.card, border: `1px solid ${C.border}` }}>
                    <div className="mb-2" style={{ color: C.cyan }}>{item.icon}</div>
                    <span className="text-[10px] font-semibold block" style={{ color: C.white70 }}>{item.label}</span>
                    <span className="text-[8px]" style={{ color: C.white30 }}>{item.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
