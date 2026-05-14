'use client';

import React, { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface Tab {
  id: string;
  label: string;
  icon?: string;
}

interface TabContainerProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
  children: React.ReactNode;
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

export default function TabContainer({ tabs, activeTab, onTabChange, children }: TabContainerProps) {
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [indicator, setIndicator] = useState({ left: 0, width: 0 });

  useEffect(() => {
    const activeEl = tabRefs.current.get(activeTab);
    if (activeEl) {
      const parent = activeEl.parentElement;
      if (parent) {
        const parentRect = parent.getBoundingClientRect();
        const elRect = activeEl.getBoundingClientRect();
        setIndicator({
          left: elRect.left - parentRect.left,
          width: elRect.width,
        });
      }
    }
  }, [activeTab, tabs]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: T.card,
        borderRadius: 12,
        border: `1px solid ${T.white08}`,
        overflow: 'hidden',
      }}
    >
      {/* Tab bar */}
      <div style={{
        position: 'relative',
        display: 'flex',
        borderBottom: `1px solid ${T.white08}`,
        background: 'rgba(255,255,255,0.02)',
      }}>
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              ref={(el) => {
                if (el) tabRefs.current.set(tab.id, el);
              }}
              onClick={() => onTabChange(tab.id)}
              style={{
                padding: '10px 18px',
                background: 'none',
                border: 'none',
                color: isActive ? T.primary : T.textDim,
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'color 0.2s',
                whiteSpace: 'nowrap',
              }}
            >
              {tab.icon && <span style={{ fontSize: 14 }}>{tab.icon}</span>}
              {tab.label}
            </button>
          );
        })}

        {/* Animated underline indicator */}
        <motion.div
          animate={{
            left: indicator.left,
            width: indicator.width,
          }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          style={{
            position: 'absolute',
            bottom: 0,
            height: 2,
            background: `linear-gradient(90deg, ${T.primary}, #0a9b8a)`,
            borderRadius: 1,
            boxShadow: `0 0 8px ${T.primary}66`,
          }}
        />
      </div>

      {/* Tab content */}
      <div style={{ padding: 16 }}>
        {children}
      </div>
    </motion.div>
  );
}
