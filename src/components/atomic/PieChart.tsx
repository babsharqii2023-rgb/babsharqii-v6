'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface PieSegment {
  label: string;
  value: number;
  color: string;
}

interface PieChartProps {
  data: PieSegment[];
  loading?: boolean;
}

const T = {
  card: '#0d0d1a',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white08: 'rgba(255,255,255,0.08)',
};

export default function PieChart({ data, loading = false }: PieChartProps) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 80;
  const innerR = 45;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;

  const segments = data.map((d) => {
    const angle = (d.value / total) * 360;
    return { ...d, angle };
  });

  const describeArc = (startAngle: number, endAngle: number, rOuter: number, rInner: number) => {
    const startRad = ((startAngle - 90) * Math.PI) / 180;
    const endRad = ((endAngle - 90) * Math.PI) / 180;
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;

    const x1 = cx + rOuter * Math.cos(startRad);
    const y1 = cy + rOuter * Math.sin(startRad);
    const x2 = cx + rOuter * Math.cos(endRad);
    const y2 = cy + rOuter * Math.sin(endRad);
    const x3 = cx + rInner * Math.cos(endRad);
    const y3 = cy + rInner * Math.sin(endRad);
    const x4 = cx + rInner * Math.cos(startRad);
    const y4 = cy + rInner * Math.sin(startRad);

    return `M${x1},${y1} A${rOuter},${rOuter} 0 ${largeArc} 1 ${x2},${y2} L${x3},${y3} A${rInner},${rInner} 0 ${largeArc} 0 ${x4},${y4} Z`;
  };

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
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: 260,
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

  type SegmentWithAngle = PieSegment & { angle: number };

  // Compute arc angles before render
  const arcData = segments.reduce<Array<{ seg: SegmentWithAngle; startAngle: number; endAngle: number }>>(
    (acc, seg) => {
      const startAngle = acc.length > 0 ? acc[acc.length - 1].endAngle : 0;
      const endAngle = startAngle + seg.angle;
      return [...acc, { seg, startAngle, endAngle }];
    },
    []
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        background: T.card,
        borderRadius: 12,
        border: `1px solid rgba(255,255,255,0.08)`,
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 12,
      }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {arcData.map(({ seg, startAngle, endAngle }, i) => {
          // Handle full circle
          const pathD = seg.angle >= 360
            ? describeArc(0, 359.9, outerR, innerR)
            : describeArc(startAngle, endAngle, outerR, innerR);

          return (
            <motion.path
              key={i}
              d={pathD}
              fill={seg.color}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              style={{
                transformOrigin: `${cx}px ${cy}px`,
                filter: `drop-shadow(0 0 3px ${seg.color}44)`,
                cursor: 'pointer',
              }}
              whileHover={{ opacity: 0.85, scale: 1.03 }}
            />
          );
        })}

        {/* Center text */}
        <text x={cx} y={cy - 4} textAnchor="middle" fill={T.text} fontSize={16} fontWeight={700} fontFamily="monospace">
          {total}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill={T.textDim} fontSize={10}>
          total
        </text>
      </svg>

      {/* Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
        {data.map((d, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 + i * 0.05 }}
            style={{ display: 'flex', alignItems: 'center', gap: 4 }}
          >
            <span style={{
              width: 8,
              height: 8,
              borderRadius: 2,
              background: d.color,
              boxShadow: `0 0 4px ${d.color}66`,
            }} />
            <span style={{ color: T.textDim, fontSize: 11 }}>{d.label}</span>
            <span style={{ color: T.text, fontSize: 11, fontFamily: 'monospace' }}>
              {Math.round((d.value / total) * 100)}%
            </span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
