// ═══════════════════════════════════════════════════════════════════
// SiteStatsPanel — لوحة إحصائيات المواقع (v62 CONNECTED)
// Site statistics panel — NOW CONNECTED TO REAL BACKEND API
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';

interface SiteStatsPanelProps {
  onBack?: () => void;
}

interface StatCard {
  label: string;
  value: string;
  change?: string;
  color: string;
  icon: string;
}

export default function SiteStatsPanel({ onBack }: SiteStatsPanelProps) {
  const [stats, setStats] = useState<StatCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<number>(0);

  const fetchStats = useCallback(async () => {
    setLoading(true);

    const statCards: StatCard[] = [];

    // Fetch kernel status for system metrics
    try {
      const res = await fetch('/api/mamoun/kernel/status');
      if (res.ok) {
        const data = await res.json();
        statCards.push({
          label: 'حالة النواة',
          value: data.status === 'running' ? 'نشط' : data.status || 'غير معروف',
          color: data.status === 'running' ? '#69f0ae' : '#ffd740',
          icon: '🧠',
        });
        statCards.push({
          label: 'الدماغ النشط',
          value: data.winning_brain || data.active_brain || '--',
          color: '#818cf8',
          icon: '⚡',
        });
      }
    } catch {}

    // Fetch brain status
    try {
      const res = await fetch('/api/mamoun/brains/status');
      if (res.ok) {
        const data = await res.json();
        const brainCount = data.brains ? Object.keys(data.brains).length : 0;
        const activeBrains = data.brains ? Object.values(data.brains).filter((b: any) => b.status === 'active' || b.state === 'active').length : 0;
        statCards.push({
          label: 'أدمغة نشطة',
          value: `${activeBrains}/${brainCount}`,
          color: '#69f0ae',
          icon: '🧩',
        });
      }
    } catch {}

    // Fetch projects count
    try {
      const res = await fetch('/api/mamoun/kernel/projects');
      if (res.ok) {
        const data = await res.json();
        const projectCount = data.projects ? data.projects.length : 0;
        statCards.push({
          label: 'المشاريع',
          value: String(projectCount),
          color: '#f59e0b',
          icon: '📁',
        });
      }
    } catch {}

    // Fetch consciousness state
    try {
      const res = await fetch('/api/mamoun/consciousness/state');
      if (res.ok) {
        const data = await res.json();
        statCards.push({
          label: 'مستوى الوعي',
          value: data.level || data.consciousness_level || '--',
          color: '#c084fc',
          icon: '👁️',
        });
      }
    } catch {}

    // Fetch living vitals
    try {
      const res = await fetch('/api/mamoun/living/vitals');
      if (res.ok) {
        const data = await res.json();
        statCards.push({
          label: 'نبض الحياة',
          value: data.heartbeat ? `${data.heartbeat}bpm` : data.status || '--',
          color: '#EF4444',
          icon: '❤️',
        });
      }
    } catch {}

    // If no stats were fetched, show placeholder
    if (statCards.length === 0) {
      statCards.push(
        { label: 'الخادم', value: 'غير متصل', color: '#EF4444', icon: '🔴' },
        { label: 'الأدمغة', value: '--', color: '#5a6a80', icon: '🧩' },
        { label: 'المشاريع', value: '--', color: '#5a6a80', icon: '📁' },
        { label: 'الوعي', value: '--', color: '#5a6a80', icon: '👁️' },
        { label: 'الحياة', value: '--', color: '#5a6a80', icon: '❤️' },
        { label: 'الأدوات', value: '--', color: '#5a6a80', icon: '🔧' },
      );
    }

    setStats(statCards);
    setLastUpdate(Date.now());
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#f472b6' }}>
          📊 إحصائيات النظام
        </div>
        {lastUpdate > 0 && (
          <div style={{ fontSize: 8, color: '#5a6a80' }}>
            تحديث: {new Date(lastUpdate).toLocaleTimeString('ar-SA')}
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 8, padding: '10px 12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: 14 }}>{stat.icon}</span>
              <span style={{ fontSize: 9, color: '#5a6a80' }}>{stat.label}</span>
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: stat.color }}>
              {loading ? '...' : stat.value}
            </div>
            {stat.change && (
              <div style={{ fontSize: 8, color: stat.change.startsWith('+') ? '#69f0ae' : '#EF4444', marginTop: 2 }}>
                {stat.change}
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Refresh */}
      <button
        onClick={fetchStats}
        disabled={loading}
        style={{
          padding: '8px 16px',
          background: 'rgba(244,114,182,0.1)',
          border: '1px solid rgba(244,114,182,0.2)',
          borderRadius: 6, color: '#f472b6',
          fontSize: 10, cursor: loading ? 'default' : 'pointer',
          opacity: loading ? 0.5 : 1,
        }}
      >
        ⟳ تحديث
      </button>
    </div>
  );
}
