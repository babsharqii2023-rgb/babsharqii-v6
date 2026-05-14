'use client';

import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  active: { label: 'نشط', color: '#4CAF50' },
  idle: { label: 'خامل', color: '#FF9800' },
  error: { label: 'خطأ', color: '#EF4444' },
  thinking: { label: 'يفكر', color: '#9C27B0' },
  proposed: { label: 'مقترح', color: '#FF9800' },
  working: { label: 'يعمل', color: '#2196F3' },
  done: { label: 'مكتمل', color: '#4CAF50' },
  completed: { label: 'مكتمل', color: '#4CAF50' },
  paused: { label: 'متوقف', color: '#FF9800' },
  evolving: { label: 'يتطور', color: '#0d7bb5' },
  sleeping: { label: 'نائم', color: '#5a6a80' },
};

const SIZES = {
  sm: { padding: '2px 8px', fontSize: 10 },
  md: { padding: '3px 12px', fontSize: 11 },
  lg: { padding: '4px 16px', fontSize: 13 },
};

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = STATUS_MAP[status] || { label: status, color: '#0d7bb5' };
  const sizeConfig = SIZES[size];

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: sizeConfig.padding,
      borderRadius: 12,
      fontSize: sizeConfig.fontSize,
      fontWeight: 600,
      background: `${config.color}22`,
      color: config.color,
      border: `1px solid ${config.color}33`,
    }}>
      <span style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: config.color,
        boxShadow: `0 0 4px ${config.color}`,
      }} />
      {config.label}
    </span>
  );
}
