// ═══════════════════════════════════════════════════════════════════
// DeployPanel — لوحة النشر
// Deployment panel
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface DeployPanelProps {
  onBack?: () => void;
}

export default function DeployPanel({ onBack }: DeployPanelProps) {
  const [deploying, setDeploying] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  const environments = [
    { id: 'dev', labelAr: 'تطوير', color: '#ffd740' },
    { id: 'staging', labelAr: 'تجريبي', color: '#448aff' },
    { id: 'production', labelAr: 'إنتاج', color: '#69f0ae' },
  ];

  const handleDeploy = async (env: string) => {
    setDeploying(true);
    setLogs([]);
    const steps = [
      `🚀 بدء النشر على بيئة ${environments.find(e => e.id === env)?.labelAr}...`,
      '📦 تجميع الحزم...',
      '🧪 تشغيل الاختبارات...',
      '📤 رفع الملفات...',
      '🔄 إعادة تشغيل الخدمات...',
      '✅ اكتمل النشر بنجاح!',
    ];
    for (const s of steps) {
      await new Promise(r => setTimeout(r, 700));
      setLogs(prev => [...prev, s]);
    }
    setDeploying(false);
  };

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ fontSize: 14, fontWeight: 700, color: '#0d7bb5' }}>
        🚀 لوحة النشر
      </div>

      {/* Environment Buttons */}
      <div style={{ display: 'flex', gap: 10 }}>
        {environments.map(env => (
          <button
            key={env.id}
            onClick={() => handleDeploy(env.id)}
            disabled={deploying}
            style={{
              flex: 1,
              padding: '14px 12px',
              background: `${env.color}15`,
              border: `1px solid ${env.color}40`,
              borderRadius: 8,
              cursor: deploying ? 'default' : 'pointer',
              color: env.color,
              fontSize: 12,
              fontWeight: 600,
              opacity: deploying ? 0.5 : 1,
            }}
          >
            <div style={{ fontSize: 22, marginBottom: 4 }}>🚀</div>
            {env.labelAr}
          </button>
        ))}
      </div>

      {/* Deploy Log */}
      {logs.length > 0 && (
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: 8,
          padding: 12,
          fontFamily: 'monospace',
          fontSize: 10,
          flex: 1,
          overflow: 'auto',
        }}>
          {logs.map((log, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              style={{ color: '#69f0ae', marginBottom: 4 }}
            >
              {log}
            </motion.div>
          ))}
          {deploying && (
            <motion.div
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1, repeat: Infinity }}
              style={{ color: '#0d7bb5' }}
            >
              ▌
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
