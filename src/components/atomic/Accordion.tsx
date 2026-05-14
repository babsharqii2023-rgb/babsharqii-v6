// ═══════════════════════════════════════════════════════════════════
// Accordion — مكون الأكورديون الذري
// Collapsible sections for structured content
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface AccordionItem {
  id: string;
  title: string;
  content: React.ReactNode;
  icon?: string;
  defaultOpen?: boolean;
}

interface AccordionProps {
  items: AccordionItem[];
  allowMultiple?: boolean;
  variant?: 'default' | 'bordered' | 'ghost';
}

export default function Accordion({ items, allowMultiple = false, variant = 'default' }: AccordionProps) {
  const [openItems, setOpenItems] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    items.forEach(item => {
      if (item.defaultOpen) initial.add(item.id);
    });
    return initial;
  });

  const toggleItem = (id: string) => {
    setOpenItems(prev => {
      const next = new Set(allowMultiple ? prev : []);
      if (prev.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const getVariantStyles = () => {
    switch (variant) {
      case 'bordered':
        return { background: 'rgba(13,123,181,0.05)', border: '1px solid rgba(13,123,181,0.15)', borderRadius: 8 };
      case 'ghost':
        return { background: 'transparent', border: 'none', borderRadius: 0 };
      default:
        return { background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6 };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {items.map(item => {
        const isOpen = openItems.has(item.id);
        const styles = getVariantStyles();

        return (
          <div key={item.id} style={styles}>
            <button
              onClick={() => toggleItem(item.id)}
              style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 12px',
                background: 'transparent',
                border: 'none',
                color: '#c8d0e0',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: 600,
                direction: 'rtl',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {item.icon && <span>{item.icon}</span>}
                <span>{item.title}</span>
              </div>
              <motion.span
                animate={{ rotate: isOpen ? 180 : 0 }}
                transition={{ duration: 0.2 }}
                style={{ fontSize: 8, color: '#5a6a80' }}
              >
                ▼
              </motion.span>
            </button>
            <AnimatePresence>
              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  style={{ overflow: 'hidden' }}
                >
                  <div style={{ padding: '0 12px 8px', fontSize: 10, color: '#5a6a80', lineHeight: 1.6 }}>
                    {item.content}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
