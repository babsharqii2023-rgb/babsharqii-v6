'use client';

import React, { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';

interface FloatingPanelProps {
  title: string;
  icon?: string;
  initialPosition?: { x: number; y: number };
  children: React.ReactNode;
  onClose?: () => void;
}

const T = {
  card: '#0d0d1a',
  primary: '#0d7bb5',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white90: 'rgba(255,255,255,0.9)',
  white08: 'rgba(255,255,255,0.08)',
  white15: 'rgba(255,255,255,0.15)',
};

export default function FloatingPanel({
  title,
  icon,
  initialPosition = { x: 100, y: 100 },
  children,
  onClose,
}: FloatingPanelProps) {
  const [position, setPosition] = useState(initialPosition);
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    setIsDragging(true);
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  }, [position]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    const newX = e.clientX - dragOffset.current.x;
    const newY = e.clientY - dragOffset.current.y;
    setPosition({
      x: Math.max(0, newX),
      y: Math.max(0, newY),
    });
  }, [isDragging]);

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.2 }}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        minWidth: 280,
        maxWidth: 480,
        background: T.card,
        border: `1px solid ${T.primary}33`,
        borderRadius: 14,
        overflow: 'hidden',
        zIndex: 9000,
        boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 20px ${T.primary}11`,
      }}
    >
      {/* Header (draggable) */}
      <div
        onPointerDown={handlePointerDown}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          background: 'rgba(255,255,255,0.03)',
          borderBottom: `1px solid ${T.white08}`,
          cursor: isDragging ? 'grabbing' : 'grab',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {icon && <span style={{ fontSize: 14, opacity: 0.7 }}>{icon}</span>}
          <span style={{ color: T.white90, fontSize: 13, fontWeight: 600 }}>{title}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {/* Drag indicator */}
          <div style={{
            display: 'flex',
            gap: 2,
            opacity: 0.3,
          }}>
            <div style={{ width: 3, height: 3, borderRadius: '50%', background: T.textDim }} />
            <div style={{ width: 3, height: 3, borderRadius: '50%', background: T.textDim }} />
            <div style={{ width: 3, height: 3, borderRadius: '50%', background: T.textDim }} />
          </div>
          {onClose && (
            <motion.button
              whileHover={{ scale: 1.1, background: 'rgba(239,68,68,0.2)' }}
              whileTap={{ scale: 0.9 }}
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              style={{
                width: 22,
                height: 22,
                borderRadius: 6,
                background: T.white08,
                border: 'none',
                color: T.textDim,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                lineHeight: 1,
                transition: 'all 0.15s',
              }}
            >
              ✕
            </motion.button>
          )}
        </div>
      </div>

      {/* Content */}
      <div style={{
        padding: 14,
        maxHeight: 400,
        overflowY: 'auto',
      }}>
        {children}
      </div>

      {/* Bottom glow line */}
      <div style={{
        height: 2,
        background: `linear-gradient(90deg, transparent, ${T.primary}44, transparent)`,
      }} />
    </motion.div>
  );
}
