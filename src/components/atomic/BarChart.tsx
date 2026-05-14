'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  data: BarItem[];
  loading?: boolean;
}

const T = {
  card: '#0d0d1a',
  primary: '#0d7bb5',
  secondary: '#0a9b8a',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white08: 'rgba(255,255,255,0.08)',
};

const BAR_COLORS = ['#0d7bb5', '#0a9b8a', '#6366f1', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981', '#ec4899'];

export default function BarChart({ data, loading = false }: BarChartProps) {
  const height = 220;
  const padding = { top: 20, right: 20, bottom: 40, left: 40 };
  const width = 400;
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;
  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const barWidth = Math.min(36, chartW / data.length - 8);

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{
          background: T.card,
          borderRadius: 12,
          border: `1px solid ${T.white08}`,
          padding: 16,
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <motion.div
          animate={{ opacity: [0.3, 0.7, 0.3] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          style={{ color: T.textDim, fontSize: 13 }}
        >
          Loading chart...
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        background: T.card,
        borderRadius: 12,
        border: `1px solid rgba(13,123,181,0.15)`,
        padding: 16,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
          const y = padding.top + chartH * (1 - pct);
          const val = (maxVal * pct).toFixed(0);
          return (
            <React.Fragment key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="rgba(255,255,255,0.06)"
                strokeDasharray="4,4"
              />
              <text x={padding.left - 8} y={y + 4} textAnchor="end" fill={T.textDim} fontSize={10} fontFamily="monospace">
                {val}
              </text>
            </React.Fragment>
          );
        })}

        {/* Bars */}
        {data.map((d, i) => {
          const barColor = d.color || BAR_COLORS[i % BAR_COLORS.length];
          const barH = (d.value / maxVal) * chartH;
          const x = padding.left + (i + 0.5) * (chartW / data.length) - barWidth / 2;
          const y = padding.top + chartH - barH;

          return (
            <React.Fragment key={i}>
              {/* Bar */}
              <motion.rect
                x={x}
                width={barWidth}
                fill={barColor}
                rx={4}
                initial={{ y: padding.top + chartH, height: 0 }}
                animate={{ y, height: barH }}
                transition={{ duration: 0.6, delay: i * 0.08, ease: 'easeOut' }}
                style={{ filter: `drop-shadow(0 0 6px ${barColor}44)` }}
              />
              {/* Bar value */}
              <motion.text
                x={x + barWidth / 2}
                y={y - 6}
                textAnchor="middle"
                fill={T.text}
                fontSize={10}
                fontFamily="monospace"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 + i * 0.08 }}
              >
                {d.value}
              </motion.text>
              {/* Label */}
              <text
                x={x + barWidth / 2}
                y={height - 10}
                textAnchor="middle"
                fill={T.textDim}
                fontSize={10}
              >
                {d.label.length > 6 ? d.label.slice(0, 6) + '…' : d.label}
              </text>
            </React.Fragment>
          );
        })}
      </svg>
    </motion.div>
  );
}
