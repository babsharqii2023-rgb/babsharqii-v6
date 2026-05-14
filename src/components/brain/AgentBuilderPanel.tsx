// ═══════════════════════════════════════════════════════════════════
// AgentBuilderPanel — لوحة بناء الوكلاء (v62 CONNECTED)
// Agent builder — NOW CONNECTED TO REAL BACKEND API
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface AgentBuilderPanelProps {
  onBack?: () => void;
}

const agentRoles = [
  { id: 'researcher', label: '🔍 باحث', desc: 'يبحث ويجمع المعلومات' },
  { id: 'coder', label: '💻 مبرمج', desc: 'يكتب ويعدل الأكواد' },
  { id: 'analyst', label: '📊 محلل', desc: 'يحلل البيانات والأنماط' },
  { id: 'writer', label: '✍️ كاتب', desc: 'يكتب المحتوى والتقارير' },
  { id: 'manager', label: '📋 مدير', desc: 'ينسق المهام والمشاريع' },
  { id: 'custom', label: '⚡ مخصص', desc: 'وكيل بناءً على وصفك' },
];

export default function AgentBuilderPanel({ onBack }: AgentBuilderPanelProps) {
  const [agentName, setAgentName] = useState('');
  const [agentRole, setAgentRole] = useState('researcher');
  const [agentDescription, setAgentDescription] = useState('');
  const [building, setBuilding] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBuild = async () => {
    setBuilding(true);
    setResult(null);
    setError(null);

    try {
      const res = await fetch('/api/mamoun/evolution/build-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: agentName || `${agentRole}_agent`,
          role: agentRole,
          description: agentDescription || `وكيل ${agentRoles.find(r => r.id === agentRole)?.label || agentRole}`,
          capabilities: [agentRole],
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        const errorData = await res.json().catch(() => ({}));
        setError(errorData.detail || `خطأ HTTP: ${res.status}`);
      }
    } catch (err) {
      setError(`فشل الاتصال: ${err instanceof Error ? err.message : 'غير معروف'}`);
    }

    setBuilding(false);
  };

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ fontSize: 13, fontWeight: 700, color: '#f59e0b' }}>
        🤖 بناء وكيل ذكي
      </div>

      {/* Agent Name */}
      <div>
        <label style={{ fontSize: 10, color: '#5a6a80', display: 'block', marginBottom: 4 }}>
          اسم الوكيل
        </label>
        <input
          value={agentName}
          onChange={e => setAgentName(e.target.value)}
          placeholder={`${agentRole}_agent`}
          dir="ltr"
          style={{
            width: '100%', padding: '8px 12px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 6, color: '#c8d0e0',
            fontSize: 11, outline: 'none',
          }}
        />
      </div>

      {/* Role Selection */}
      <div>
        <label style={{ fontSize: 10, color: '#5a6a80', display: 'block', marginBottom: 6 }}>
          دور الوكيل
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {agentRoles.map((role) => (
            <motion.button
              key={role.id}
              whileHover={{ scale: 1.02 }}
              onClick={() => setAgentRole(role.id)}
              style={{
                padding: '8px 10px',
                background: agentRole === role.id ? 'rgba(245,158,11,0.15)' : 'rgba(255,255,255,0.02)',
                border: `1px solid ${agentRole === role.id ? 'rgba(245,158,11,0.4)' : 'rgba(255,255,255,0.06)'}`,
                borderRadius: 6, cursor: 'pointer',
                textAlign: 'right' as const,
              }}
            >
              <div style={{ fontSize: 11, color: agentRole === role.id ? '#f59e0b' : '#c8d0e0' }}>
                {role.label}
              </div>
              <div style={{ fontSize: 8, color: '#5a6a80' }}>
                {role.desc}
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Description */}
      <div>
        <label style={{ fontSize: 10, color: '#5a6a80', display: 'block', marginBottom: 4 }}>
          وصف المهام (اختياري)
        </label>
        <textarea
          value={agentDescription}
          onChange={e => setAgentDescription(e.target.value)}
          placeholder="صف المهام التي يجب أن ينفذها هذا الوكيل..."
          rows={2}
          style={{
            width: '100%', padding: '8px 12px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 6, color: '#c8d0e0',
            fontSize: 11, outline: 'none', resize: 'vertical',
          }}
        />
      </div>

      {/* Build Button */}
      <button
        onClick={handleBuild}
        disabled={building}
        style={{
          padding: '12px 20px',
          background: building ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.2)',
          border: '1px solid rgba(245,158,11,0.4)',
          borderRadius: 8, color: '#f59e0b',
          fontSize: 13, fontWeight: 700,
          cursor: building ? 'default' : 'pointer',
          opacity: building ? 0.5 : 1,
          transition: 'all 0.2s',
        }}
      >
        {building ? '⏳ جاري البناء...' : '🤖 إنشاء الوكيل'}
      </button>

      {/* Result */}
      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 6, padding: 8,
          fontSize: 10, color: '#EF4444',
        }}>
          {error}
        </div>
      )}

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            background: 'rgba(245,158,11,0.1)',
            border: '1px solid rgba(245,158,11,0.3)',
            borderRadius: 8, padding: 12,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: '#f59e0b', marginBottom: 8 }}>
            ✓ تم إنشاء الوكيل بنجاح
          </div>
          <div style={{ fontSize: 10, color: '#c8d0e0' }}>
            <div>الاسم: {result.name || result.agent_name || agentName}</div>
            {result.file_path && <div>الملف: {result.file_path}</div>}
            {result.message && <div style={{ marginTop: 4, color: '#69f0ae' }}>{result.message}</div>}
          </div>
          <pre dir="ltr" style={{ fontSize: 8, color: '#5a6a80', marginTop: 8, maxHeight: 80, overflow: 'auto' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </motion.div>
      )}
    </div>
  );
}
