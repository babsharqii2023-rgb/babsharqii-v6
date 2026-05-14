// ═══════════════════════════════════════════════════════════════════
// SiteStatsPanel — لوحة إحصائيات الموقع
// Website stats dashboard with metrics
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface SiteStatsPanelProps {
  onBack?: () => void;
}

interface MetricCard {
  labelAr: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  color: string;
  icon: string;
}

export default function SiteStatsPanel({ onBack }: SiteStatsPanelProps) {
  const [metrics] = useState<MetricCard[]>([
    { labelAr: 'الزيارات اليومية', value: '2,847', change: '+12%', trend: 'up', color: '#69f0ae', icon: '👥' },
    { labelAr: 'معدل الارتداد', value: '34%', change: '-5%', trend: 'down', color: '#00e5ff', icon: '📉' },
    { labelAr: 'مدة الجلسة', value: '4:32', change: '+18%', trend: 'up', color: '#ffd740', icon: '⏱️' },
    { labelAr: 'التحويلات', value: '156', change: '+8%', trend: 'up', color: '#448aff', icon: '🎯' },
    { labelAr: 'الصفحات/جلسة', value: '3.8', change: '+2%', trend: 'up', color: '#ff9100', icon: '📄' },
    { labelAr: 'المستخدمون الجدد', value: '423', change: '+24%', trend: 'up', color: '#69f0ae', icon: '🌟' },
  ]);

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto' }}>
      {/* Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: 12,
        marginBottom: 20,
      }}>
        {metrics.map((metric, i) => (
          <motion.div
            key={metric.labelAr}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 10,
              padding: '14px 16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <span style={{ fontSize: 18 }}>{metric.icon}</span>
              <span style={{ fontSize: 10, color: '#5a6a80' }}>{metric.labelAr}</span>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: metric.color }}>
              {metric.value}
            </div>
            <div style={{
              fontSize: 10,
              color: metric.trend === 'up' ? '#69f0ae' : metric.trend === 'down' ? '#ff9100' : '#5a6a80',
              marginTop: 4,
            }}>
              {metric.change} من الأسبوع الماضي
            </div>
          </motion.div>
        ))}
      </div>

      {/* Traffic Chart Placeholder */}
      <div style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 10,
        padding: 20,
        height: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 8,
      }}>
        <div style={{ fontSize: 28 }}>📊</div>
        <div style={{ fontSize: 12, color: '#5a6a80' }}>رسم بياني للزيارات</div>
        <div style={{ fontSize: 10, color: '#5a6a80', opacity: 0.6 }}>سيتم عرض البيانات الحية هنا</div>
      </div>
    </div>
  );
}
