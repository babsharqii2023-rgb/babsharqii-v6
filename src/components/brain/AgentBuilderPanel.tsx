// ═══════════════════════════════════════════════════════════════════
// AgentBuilderPanel — بناء الوكلاء
// Agent builder panel
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface AgentBuilderPanelProps {
  onBack?: () => void;
}

export default function AgentBuilderPanel({ onBack }: AgentBuilderPanelProps) {
  const [agentName, setAgentName] = useState('');
  const [agentRole, setAgentRole] = useState('researcher');

  const roles = [
    { id: 'researcher', labelAr: 'باحث', icon: '🔍', desc: 'يبحث ويجمع المعلومات' },
    { id: 'coder', labelAr: 'مبرمج', icon: '⌨️', desc: 'يكتب ويراجع الكود' },
    { id: 'analyst', labelAr: 'محلل', icon: '📊', desc: 'يحلل البيانات والاتجاهات' },
    { id: 'manager', labelAr: 'مدير', icon: '📋', desc: 'ينسق بين الوكلاء' },
    { id: 'guardian', labelAr: 'حارس', icon: '🛡️', desc: 'يتحقق من الأمان' },
  ];

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ fontSize: 14, fontWeight: 700, color: '#0d7bb5' }}>
        🤖 بناء وكيل جديد
      </div>

      {/* Agent Name */}
      <div>
        <label style={{ fontSize: 10, color: '#5a6a80', marginBottom: 4, display: 'block' }}>اسم الوكيل</label>
        <input
          value={agentName}
          onChange={e => setAgentName(e.target.value)}
          placeholder="أدخل اسم الوكيل"
          dir="rtl"
          style={{
            width: '100%', background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8, padding: '10px 12px',
            color: '#c8d0e0', fontSize: 12, outline: 'none',
          }}
        />
      </div>

      {/* Role Selection */}
      <div>
        <label style={{ fontSize: 10, color: '#5a6a80', marginBottom: 8, display: 'block' }}>دور الوكيل</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {roles.map(role => (
            <motion.button
              key={role.id}
              whileHover={{ scale: 1.01 }}
              onClick={() => setAgentRole(role.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 14px',
                background: agentRole === role.id ? 'rgba(13,123,181,0.12)' : 'rgba(255,255,255,0.02)',
                border: agentRole === role.id ? '1px solid #0d7bb5' : '1px solid rgba(255,255,255,0.06)',
                borderRadius: 8,
                cursor: 'pointer',
                textAlign: 'right',
                color: '#c8d0e0',
              }}
            >
              <span style={{ fontSize: 20 }}>{role.icon}</span>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{role.labelAr}</div>
                <div style={{ fontSize: 9, color: '#5a6a80' }}>{role.desc}</div>
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      <button
        disabled={!agentName.trim()}
        style={{
          padding: '10px 20px',
          background: '#0d7bb5',
          border: 'none',
          borderRadius: 8,
          color: '#fff',
          fontSize: 12,
          fontWeight: 600,
          cursor: agentName.trim() ? 'pointer' : 'default',
          opacity: agentName.trim() ? 1 : 0.4,
          marginTop: 'auto',
        }}
      >
        🤖 إنشاء الوكيل
      </button>
    </div>
  );
}
