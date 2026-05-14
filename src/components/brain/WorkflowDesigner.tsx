// ═══════════════════════════════════════════════════════════════════
// WorkflowDesigner — مصمم سير العمل
// Visual workflow builder with node graph
// Allows creating, connecting, and managing workflow steps
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface WorkflowNode {
  id: string;
  type: 'start' | 'process' | 'decision' | 'action' | 'end';
  label: string;
  x: number;
  y: number;
  config?: Record<string, unknown>;
}

interface WorkflowEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
}

interface WorkflowDesignerProps {
  workflow?: {
    name?: string;
    nodes?: WorkflowNode[];
    edges?: WorkflowEdge[];
  };
  _isOffline?: boolean;
  onBack?: () => void;
  [key: string]: unknown;
}

const NODE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  start: { bg: 'rgba(76,175,80,0.1)', border: 'rgba(76,175,80,0.3)', text: '#4CAF50' },
  process: { bg: 'rgba(13,123,181,0.1)', border: 'rgba(13,123,181,0.3)', text: '#0d7bb5' },
  decision: { bg: 'rgba(255,152,0,0.1)', border: 'rgba(255,152,0,0.3)', text: '#FF9800' },
  action: { bg: 'rgba(156,39,176,0.1)', border: 'rgba(156,39,176,0.3)', text: '#9C27B0' },
  end: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', text: '#EF4444' },
};

const NODE_ICONS: Record<string, string> = {
  start: '▶️', process: '⚙️', decision: '🔀', action: '🔧', end: '⏹️',
};

export default function WorkflowDesigner(props: WorkflowDesignerProps) {
  const workflow = props.workflow || {};
  const isOffline = props._isOffline || false;

  const [nodes, setNodes] = useState<WorkflowNode[]>(workflow.nodes || [
    { id: 'start-1', type: 'start', label: 'البداية', x: 50, y: 50 },
    { id: 'process-1', type: 'process', label: 'معالجة الطلب', x: 200, y: 50 },
    { id: 'decision-1', type: 'decision', label: 'هل النتيجة صحيحة؟', x: 370, y: 50 },
    { id: 'action-1', type: 'action', label: 'تنفيذ الإجراء', x: 370, y: 170 },
    { id: 'end-1', type: 'end', label: 'النهاية', x: 530, y: 50 },
  ]);

  const [edges, setEdges] = useState<WorkflowEdge[]>(workflow.edges || [
    { id: 'e1', from: 'start-1', to: 'process-1' },
    { id: 'e2', from: 'process-1', to: 'decision-1' },
    { id: 'e3', from: 'decision-1', to: 'end-1', label: 'نعم' },
    { id: 'e4', from: 'decision-1', to: 'action-1', label: 'لا' },
  ]);

  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);

  const addNode = useCallback((type: WorkflowNode['type']) => {
    const id = `${type}-${Date.now()}`;
    const label = type === 'start' ? 'بداية' : type === 'end' ? 'نهاية'
      : type === 'decision' ? 'قرار' : type === 'action' ? 'إجراء' : 'عملية';
    setNodes(prev => [...prev, { id, type, label, x: 100 + Math.random() * 300, y: 100 + Math.random() * 200 }]);
  }, []);

  const getNodePosition = (id: string) => {
    const node = nodes.find(n => n.id === id);
    return node ? { x: node.x + 60, y: node.y + 20 } : { x: 0, y: 0 };
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', color: '#c8d0e0',
      fontFamily: "'Cairo', system-ui, sans-serif",
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 12px',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(13,13,26,0.5)',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: 16 }}>⚡</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>مصمم سير العمل</span>

        {(['start', 'process', 'decision', 'action', 'end'] as const).map(type => (
          <button
            key={type}
            onClick={() => addNode(type)}
            style={{
              background: NODE_COLORS[type].bg,
              border: `1px solid ${NODE_COLORS[type].border}`,
              borderRadius: 6, padding: '3px 8px',
              color: NODE_COLORS[type].text,
              cursor: 'pointer', fontSize: 9, fontWeight: 600,
            }}
          >
            {NODE_ICONS[type]} {type === 'start' ? 'بداية' : type === 'end' ? 'نهاية'
              : type === 'decision' ? 'قرار' : type === 'action' ? 'إجراء' : 'عملية'}
          </button>
        ))}

        <span style={{ marginRight: 'auto', fontSize: 9, color: '#5a6a80' }}>
          {nodes.length} عقد • {edges.length} اتصال
        </span>
      </div>

      {/* Canvas */}
      <div style={{
        flex: 1, position: 'relative',
        background: '#080810',
        backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)',
        backgroundSize: '20px 20px',
        overflow: 'auto',
      }}>
        {/* Edges (SVG) */}
        <svg style={{
          position: 'absolute', top: 0, left: 0,
          width: '100%', height: '100%',
          pointerEvents: 'none',
        }}>
          {edges.map(edge => {
            const from = getNodePosition(edge.from);
            const to = getNodePosition(edge.to);
            return (
              <g key={edge.id}>
                <line
                  x1={from.x} y1={from.y}
                  x2={to.x} y2={to.y}
                  stroke="rgba(13,123,181,0.4)"
                  strokeWidth={2}
                  markerEnd="url(#arrowhead)"
                />
                {edge.label && (
                  <text
                    x={(from.x + to.x) / 2}
                    y={(from.y + to.y) / 2 - 6}
                    fill="#5a6a80"
                    fontSize={9}
                    textAnchor="middle"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            );
          })}
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6"
              refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="rgba(13,123,181,0.6)" />
            </marker>
          </defs>
        </svg>

        {/* Nodes */}
        {nodes.map((node, i) => {
          const colors = NODE_COLORS[node.type] || NODE_COLORS.process;
          const isSelected = selectedNode === node.id;

          return (
            <motion.div
              key={node.id}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1, x: node.x, y: node.y }}
              transition={{ delay: i * 0.05 }}
              onClick={() => setSelectedNode(isSelected ? null : node.id)}
              onMouseDown={() => setDragging(node.id)}
              onMouseUp={() => setDragging(null)}
              style={{
                position: 'absolute',
                minWidth: 120, padding: '8px 12px',
                background: isSelected ? `${colors.bg}` : colors.bg,
                border: `1px solid ${isSelected ? colors.text : colors.border}`,
                borderRadius: node.type === 'decision' ? 0 : 8,
                cursor: 'grab',
                transform: node.type === 'decision' ? 'rotate(0deg)' : undefined,
                boxShadow: isSelected ? `0 0 12px ${colors.border}` : 'none',
              }}
            >
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 11, fontWeight: 600, color: colors.text,
              }}>
                <span>{NODE_ICONS[node.type]}</span>
                <span>{node.label}</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Node Detail Panel */}
      <AnimatePresence>
        {selectedNode && (() => {
          const node = nodes.find(n => n.id === selectedNode);
          if (!node) return null;
          const colors = NODE_COLORS[node.type];
          return (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{
                padding: '8px 12px',
                borderTop: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(13,13,26,0.8)',
                overflow: 'hidden',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 14 }}>{NODE_ICONS[node.type]}</span>
                <input
                  value={node.label}
                  onChange={(e) => {
                    setNodes(prev => prev.map(n =>
                      n.id === selectedNode ? { ...n, label: e.target.value } : n
                    ));
                  }}
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 4, padding: '3px 8px',
                    color: '#fff', fontSize: 11, flex: 1,
                  }}
                  dir="rtl"
                />
                <button
                  onClick={() => {
                    setNodes(prev => prev.filter(n => n.id !== selectedNode));
                    setEdges(prev => prev.filter(e => e.from !== selectedNode && e.to !== selectedNode));
                    setSelectedNode(null);
                  }}
                  style={{
                    background: 'rgba(239,68,68,0.1)',
                    border: '1px solid rgba(239,68,68,0.3)',
                    borderRadius: 4, padding: '3px 8px',
                    color: '#EF4444', cursor: 'pointer', fontSize: 9,
                  }}
                >
                  حذف
                </button>
              </div>
              <div style={{ fontSize: 9, color: '#5a6a80', marginTop: 4 }}>
                النوع: {node.type} • المعرف: {node.id} • الموقع: ({Math.round(node.x)}, {Math.round(node.y)})
              </div>
            </motion.div>
          );
        })()}
      </AnimatePresence>

      {isOffline && (
        <div style={{
          fontSize: 10, color: '#FF9800',
          background: 'rgba(255,152,0,0.05)',
          border: '1px solid rgba(255,152,0,0.2)',
          padding: '4px 10px',
        }}>
          ⚠️ وضع عدم الاتصال — التغييرات ستُحفظ محلياً
        </div>
      )}
    </div>
  );
}
