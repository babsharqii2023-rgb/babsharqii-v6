'use client';

import React, { useState, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';

interface SplitPaneProps {
  left: React.ReactNode;
  right: React.ReactNode;
  splitRatio?: number;
  direction?: 'horizontal' | 'vertical';
}

const T = {
  card: '#0d0d1a',
  primary: '#0d7bb5',
  text: '#c8d0e0',
  white08: 'rgba(255,255,255,0.08)',
  white15: 'rgba(255,255,255,0.15)',
};

export default function SplitPane({
  left,
  right,
  splitRatio = 0.5,
  direction = 'horizontal',
}: SplitPaneProps) {
  const [ratio, setRatio] = useState(splitRatio);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    isDragging.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, []);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      let newRatio: number;

      if (direction === 'horizontal') {
        newRatio = (e.clientX - rect.left) / rect.width;
      } else {
        newRatio = (e.clientY - rect.top) / rect.height;
      }

      newRatio = Math.max(0.15, Math.min(0.85, newRatio));
      setRatio(newRatio);
    },
    [direction]
  );

  const handlePointerUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const isHorizontal = direction === 'horizontal';

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      style={{
        display: 'flex',
        flexDirection: isHorizontal ? 'row' : 'column',
        width: '100%',
        height: '100%',
        minHeight: isHorizontal ? undefined : 200,
        minWidth: isHorizontal ? 300 : undefined,
        background: T.card,
        borderRadius: 12,
        border: `1px solid ${T.white08}`,
        overflow: 'hidden',
      }}
    >
      {/* Left pane */}
      <div
        style={{
          flex: 'none',
          width: isHorizontal ? `${ratio * 100}%` : '100%',
          height: isHorizontal ? '100%' : `${ratio * 100}%`,
          overflow: 'auto',
          position: 'relative',
        }}
      >
        {left}
      </div>

      {/* Divider */}
      <div
        onPointerDown={handlePointerDown}
        style={{
          flex: 'none',
          width: isHorizontal ? 6 : '100%',
          height: isHorizontal ? '100%' : 6,
          background: T.white15,
          cursor: isHorizontal ? 'col-resize' : 'row-resize',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'background 0.15s',
          zIndex: 10,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = `${T.primary}44`;
        }}
        onMouseLeave={(e) => {
          if (!isDragging.current) {
            e.currentTarget.style.background = T.white15;
          }
        }}
      >
        {/* Center grip dots */}
        <div style={{
          display: 'flex',
          flexDirection: isHorizontal ? 'column' : 'row',
          gap: 3,
          alignItems: 'center',
        }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: 3,
                height: 3,
                borderRadius: '50%',
                background: T.primary,
                opacity: 0.6,
              }}
            />
          ))}
        </div>
      </div>

      {/* Right pane */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          position: 'relative',
        }}
      >
        {right}
      </div>
    </motion.div>
  );
}
