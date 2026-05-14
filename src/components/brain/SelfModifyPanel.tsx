// ═══════════════════════════════════════════════════════════════════
// SelfModifyPanel — لوحة التعديل الذاتي
// Displays self-modification proposals with diff view
// Shows risk assessment, code changes, and approval interface
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';

interface SelfModifyProps {
  modification?: {
    id?: string;
    description?: string;
    target_file?: string;
    diff?: string;
    risk_level?: number;
    status?: 'pending' | 'approved' | 'applied' | 'rejected';
    proposed_changes?: Array<{
      file: string;
      type: 'add' | 'modify' | 'delete';
      lines_added: number;
      lines_removed: number;
    }>;
  };
  status?: string;
  _isOffline?: boolean;
  onBack?: () => void;
  [key: string]: unknown;
}

export default function SelfModifyPanel(props: SelfModifyProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const mod = props.modification || {};
  const isOffline = props._isOffline || false;

  const riskLevel = mod.risk_level ?? 5;
  const riskColor = riskLevel >= 8 ? '#EF4444' : riskLevel >= 5 ? '#FF9800' : '#4CAF50';
  const riskLabel = riskLevel >= 8 ? 'حرج' : riskLevel >= 5 ? 'متوسط' : 'منخفض';

  const changes = mod.proposed_changes || [
    { file: mod.target_file || 'unknown.py', type: 'modify' as const, lines_added: 15, lines_removed: 8 },
  ];

  const diffLines = useMemo(() => {
    const raw = mod.diff || '';
    if (!raw) return [];
    return raw.split('\n').map((line, i) => ({
      num: i + 1,
      text: line,
      type: line.startsWith('+') ? 'add' : line.startsWith('-') ? 'remove' : 'context' as const,
    }));
  }, [mod.diff]);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', padding: 16, gap: 12,
      color: '#c8d0e0', fontFamily: "'Cairo', system-ui, sans-serif",
      overflow: 'auto',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          style={{ fontSize: 24 }}
        >
          🧬
        </motion.div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>التعديل الذاتي</div>
          <div style={{ fontSize: 10, color: '#5a6a80' }}>
            {isOffline ? 'غير متصل بالخادم' : 'اقتراح تعديل الكود'}
          </div>
        </div>
        <div style={{
          marginRight: 'auto',
          background: `${riskColor}15`,
          border: `1px solid ${riskColor}40`,
          borderRadius: 8, padding: '4px 10px',
          fontSize: 11, fontWeight: 600, color: riskColor,
        }}>
          مخاطر: {riskLabel} ({riskLevel}/10)
        </div>
      </div>

      {/* Description */}
      {mod.description && (
        <div style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 8, padding: '10px 14px',
          fontSize: 12, lineHeight: 1.8,
        }}>
          {mod.description}
        </div>
      )}

      {/* Files Changed */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, color: '#0d7bb5' }}>
          الملفات المتأثرة ({changes.length})
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {changes.map((change, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              onClick={() => setSelectedFile(change.file)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px',
                background: selectedFile === change.file
                  ? 'rgba(13,123,181,0.1)'
                  : 'rgba(255,255,255,0.02)',
                border: `1px solid ${selectedFile === change.file ? 'rgba(13,123,181,0.3)' : 'rgba(255,255,255,0.05)'}`,
                borderRadius: 6, cursor: 'pointer',
              }}
            >
              <span style={{
                fontSize: 10, fontWeight: 600,
                color: change.type === 'add' ? '#4CAF50' : change.type === 'delete' ? '#EF4444' : '#FF9800',
                background: `${change.type === 'add' ? '#4CAF50' : change.type === 'delete' ? '#EF4444' : '#FF9800'}15`,
                padding: '1px 6px', borderRadius: 4,
              }}>
                {change.type === 'add' ? 'جديد' : change.type === 'delete' ? 'حذف' : 'تعديل'}
              </span>
              <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#c8d0e0' }}>
                {change.file}
              </span>
              <span style={{ marginRight: 'auto', fontSize: 9, color: '#5a6a80' }}>
                +{change.lines_added} / -{change.lines_removed}
              </span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Diff View */}
      {diffLines.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, color: '#0d7bb5' }}>
            التغييرات المقترحة
          </div>
          <div style={{
            background: '#0d0d1a',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8,
            padding: 8,
            fontFamily: 'monospace',
            fontSize: 10,
            maxHeight: 250,
            overflow: 'auto',
          }}>
            {diffLines.map((line) => (
              <div key={line.num} style={{
                display: 'flex',
                background: line.type === 'add' ? 'rgba(76,175,80,0.08)'
                  : line.type === 'remove' ? 'rgba(239,68,68,0.08)' : 'transparent',
                padding: '1px 6px',
              }}>
                <span style={{ width: 30, color: '#5a6a80', textAlign: 'right', marginRight: 8 }}>
                  {line.num}
                </span>
                <span style={{
                  color: line.type === 'add' ? '#4CAF50' : line.type === 'remove' ? '#EF4444' : '#c8d0e0',
                }}>
                  {line.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Status */}
      {mod.status && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 12px',
          background: mod.status === 'approved' ? 'rgba(76,175,80,0.08)'
            : mod.status === 'rejected' ? 'rgba(239,68,68,0.08)'
            : 'rgba(255,152,0,0.08)',
          border: `1px solid ${mod.status === 'approved' ? 'rgba(76,175,80,0.3)'
            : mod.status === 'rejected' ? 'rgba(239,68,68,0.3)'
            : 'rgba(255,152,0,0.3)'}`,
          borderRadius: 8,
        }}>
          <span style={{ fontSize: 14 }}>
            {mod.status === 'approved' ? '✅' : mod.status === 'rejected' ? '❌' : '⏳'}
          </span>
          <span style={{ fontSize: 11, fontWeight: 600 }}>
            {mod.status === 'approved' ? 'تمت الموافقة' : mod.status === 'rejected' ? 'مرفوض' : 'بانتظار الموافقة'}
          </span>
        </div>
      )}

      {isOffline && (
        <div style={{
          fontSize: 10, color: '#FF9800',
          background: 'rgba(255,152,0,0.05)',
          border: '1px solid rgba(255,152,0,0.2)',
          borderRadius: 6, padding: '6px 10px',
        }}>
          ⚠️ الخادم غير متصل — لن يتم تنفيذ أي تعديل حتى يتم الاتصال
        </div>
      )}
    </div>
  );
}
