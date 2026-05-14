'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: string;
  color?: string;
  trend?: 'up' | 'down' | 'stable';
}

const T = {
  bg: '#080810',
  card: '#0d0d1a',
  primary: '#0d7bb5',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white90: 'rgba(255,255,255,0.9)',
  white08: 'rgba(255,255,255,0.08)',
  white15: 'rgba(255,255,255,0.15)',
};

export default function MetricCard({ title, value, subtitle, icon, color = T.primary, trend }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        background: T.card,
        border: `1px solid ${color}33`,
        borderRadius: 12,
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Glow effect */}
      <div style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: 60,
        height: 60,
        background: `radial-gradient(circle, ${color}15 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: T.textDim, fontSize: 12, fontWeight: 500 }}>{title}</span>
        {trend && (
          <span style={{
            fontSize: 11,
            color: trend === 'up' ? '#4CAF50' : trend === 'down' ? '#EF4444' : '#FF9800',
          }}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ color: T.white90, fontSize: 28, fontWeight: 700, fontFamily: 'monospace' }}>{value}</span>
        {icon && <span style={{ fontSize: 16, opacity: 0.5 }}>{icon}</span>}
      </div>

      {subtitle && <span style={{ color: T.textDim, fontSize: 11 }}>{subtitle}</span>}
    </motion.div>
  );
}
