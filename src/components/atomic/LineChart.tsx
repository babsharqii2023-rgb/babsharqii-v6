'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface LineChartProps {
  data: {
    labels: string[];
    values: number[];
    color?: string;
  };
  loading?: boolean;
  height?: number;
}

const T = {
  bg: '#080810',
  card: '#0d0d1a',
  primary: '#0d7bb5',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white08: 'rgba(255,255,255,0.08)',
  white15: 'rgba(255,255,255,0.15)',
};

export default function LineChart({ data, loading = false, height = 200 }: LineChartProps) {
  const color = data.color || T.primary;
  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const width = 400;
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const minVal = Math.min(...data.values);
  const maxVal = Math.max(...data.values);
  const range = maxVal - minVal || 1;

  const points = data.values.map((v, i) => ({
    x: padding.left + (i / Math.max(data.values.length - 1, 1)) * chartW,
    y: padding.top + chartH - ((v - minVal) / range) * chartH,
  }));

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  const areaPath = `${linePath} L${points[points.length - 1].x},${padding.top + chartH} L${points[0].x},${padding.top + chartH} Z`;

  // Grid lines
  const gridLines = 4;
  const yTicks = Array.from({ length: gridLines + 1 }, (_, i) => {
    const val = minVal + (range * i) / gridLines;
    const y = padding.top + chartH - (i / gridLines) * chartH;
    return { val, y };
  });

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
        border: `1px solid ${color}22`,
        padding: 16,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Glow */}
      <div style={{
        position: 'absolute',
        top: -20,
        right: -20,
        width: 80,
        height: 80,
        background: `radial-gradient(circle, ${color}15 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />

      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
        {/* Grid lines */}
        {yTicks.map(({ y }, i) => (
          <line
            key={i}
            x1={padding.left}
            y1={y}
            x2={width - padding.right}
            y2={y}
            stroke="rgba(255,255,255,0.06)"
            strokeDasharray="4,4"
          />
        ))}

        {/* Y-axis labels */}
        {yTicks.map(({ val, y }, i) => (
          <text key={i} x={padding.left - 8} y={y + 4} textAnchor="end" fill={T.textDim} fontSize={10} fontFamily="monospace">
            {typeof val === 'number' ? val.toFixed(1) : val}
          </text>
        ))}

        {/* X-axis labels */}
        {data.labels.map((label, i) => {
          const x = padding.left + (i / Math.max(data.labels.length - 1, 1)) * chartW;
          return (
            <text key={i} x={x} y={height - 6} textAnchor="middle" fill={T.textDim} fontSize={10}>
              {label}
            </text>
          );
        })}

        {/* Area fill */}
        <motion.path
          d={areaPath}
          fill={`${color}18`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        />

        {/* Line */}
        <motion.path
          d={linePath}
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 4px ${color}66)` }}
        />

        {/* Data points */}
        {points.map((p, i) => (
          <motion.circle
            key={i}
            cx={p.x}
            cy={p.y}
            r={3}
            fill={color}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.8 + i * 0.05 }}
          />
        ))}
      </svg>
    </motion.div>
  );
}
