// ═══════════════════════════════════════════════════════════════════
// HeatMap — مكون الخريطة الحرارية الذري
// Displays data as a color-coded grid
// ═══════════════════════════════════════════════════════════════════

'use client';

import React from 'react';

interface HeatMapCell {
  value: number;
  label?: string;
  row: number;
  col: number;
}

interface HeatMapProps {
  data: HeatMapCell[];
  rows?: number;
  cols?: number;
  title?: string;
  colorScale?: { min: string; max: string };
  cellSize?: number;
  showLabels?: boolean;
}

export default function HeatMap({
  data,
  rows = 5,
  cols = 7,
  title,
  colorScale = { min: '#0d7bb5', max: '#EF4444' },
  cellSize = 24,
  showLabels = true,
}: HeatMapProps) {
  const maxValue = Math.max(...data.map(d => d.value), 1);

  const getColor = (value: number) => {
    const ratio = value / maxValue;
    if (ratio < 0.33) return colorScale.min;
    if (ratio < 0.66) return '#FF9800';
    return colorScale.max;
  };

  const getOpacity = (value: number) => {
    return 0.3 + (value / maxValue) * 0.7;
  };

  return (
    <div style={{ padding: 8 }}>
      {title && (
        <div style={{ fontSize: 11, color: '#c8d0e0', fontWeight: 600, marginBottom: 8 }}>
          {title}
        </div>
      )}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
        gap: 3,
      }}>
        {Array.from({ length: rows * cols }, (_, i) => {
          const row = Math.floor(i / cols);
          const col = i % cols;
          const cell = data.find(d => d.row === row && d.col === col);
          const value = cell?.value || 0;
          return (
            <div
              key={i}
              title={cell?.label || `${row},${col}: ${value}`}
              style={{
                width: cellSize,
                height: cellSize,
                borderRadius: 3,
                background: value > 0 ? getColor(value) : 'rgba(255,255,255,0.05)',
                opacity: value > 0 ? getOpacity(value) : 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 7,
                color: 'rgba(255,255,255,0.8)',
                cursor: 'pointer',
                transition: 'transform 0.2s',
              }}
              onMouseEnter={(e) => { (e.target as HTMLElement).style.transform = 'scale(1.1)'; }}
              onMouseLeave={(e) => { (e.target as HTMLElement).style.transform = 'scale(1)'; }}
            >
              {showLabels && value > 0 ? Math.round(value) : ''}
            </div>
          );
        })}
      </div>
    </div>
  );
}
