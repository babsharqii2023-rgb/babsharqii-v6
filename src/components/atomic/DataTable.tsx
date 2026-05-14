'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface DataTableProps {
  data: Record<string, unknown>[];
  columns: string[];
  onRowClick?: (row: Record<string, unknown>) => void;
}

const T = {
  bg: '#080810',
  card: '#0d0d1a',
  primary: '#0d7bb5',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white90: 'rgba(255,255,255,0.9)',
  white08: 'rgba(255,255,255,0.08)',
};

export default function DataTable({ data, columns, onRowClick }: DataTableProps) {
  if (!data || data.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: T.textDim, background: T.card, borderRadius: 12, border: `1px solid ${T.white08}` }}>
        لا توجد بيانات لعرضها
      </div>
    );
  }

  const columnLabels: Record<string, string> = {
    name: 'الاسم',
    nameAr: 'الاسم',
    status: 'الحالة',
    progress: 'التقدم',
    brain: 'الدماغ',
    model: 'النموذج',
    confidence: 'الثقة',
    time: 'الوقت',
    action: 'الإجراء',
    result: 'النتيجة',
    category: 'الفئة',
    weight: 'الوزن',
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ background: T.card, borderRadius: 12, border: `1px solid ${T.white08}`, overflow: 'hidden' }}
    >
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col} style={{
                  padding: '10px 14px',
                  textAlign: 'right',
                  color: T.textDim,
                  fontWeight: 600,
                  fontSize: 11,
                  borderBottom: `1px solid ${T.white08}`,
                  background: 'rgba(13,123,181,0.05)',
                }}>
                  {columnLabels[col] || col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 50).map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick?.(row)}
                style={{
                  cursor: onRowClick ? 'pointer' : 'default',
                  borderBottom: `1px solid ${T.white08}`,
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(13,123,181,0.05)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                {columns.map((col) => {
                  const val = row[col];
                  const isStatus = col === 'status';
                  const statusColors: Record<string, string> = {
                    active: '#4CAF50', idle: '#FF9800', error: '#EF4444',
                    working: '#2196F3', completed: '#4CAF50', paused: '#FF9800',
                    thinking: '#9C27B0', proposed: '#FF9800', done: '#4CAF50',
                  };
                  return (
                    <td key={col} style={{ padding: '8px 14px', color: T.text }}>
                      {isStatus ? (
                        <span style={{
                          padding: '2px 10px',
                          borderRadius: 12,
                          fontSize: 11,
                          background: `${statusColors[val as string] || '#0d7bb5'}22`,
                          color: statusColors[val as string] || '#0d7bb5',
                          fontWeight: 600,
                        }}>
                          {val as string}
                        </span>
                      ) : col === 'progress' ? (
                        <span style={{ fontFamily: 'monospace' }}>{typeof val === 'number' ? `${Math.round(val)}%` : val as string}</span>
                      ) : (
                        val as string
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
