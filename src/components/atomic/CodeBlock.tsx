'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface CodeBlockProps {
  title?: string;
  content: string;
  language?: string;
}

export default function CodeBlock({ title, content, language }: CodeBlockProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        background: '#0a0a14',
        borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.08)',
        overflow: 'hidden',
      }}
    >
      {title && (
        <div style={{
          padding: '8px 14px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(13,123,181,0.05)',
        }}>
          <span style={{ color: '#c8d0e0', fontSize: 12, fontWeight: 600 }}>{title}</span>
          {language && <span style={{ color: '#5a6a80', fontSize: 10, fontFamily: 'monospace' }}>{language}</span>}
        </div>
      )}
      <pre style={{
        padding: 14,
        margin: 0,
        overflow: 'auto',
        maxHeight: 300,
        fontSize: 12,
        fontFamily: 'monospace',
        lineHeight: 1.6,
        color: '#c8d0e0',
        direction: 'ltr',
        textAlign: 'left',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        {content}
      </pre>
    </motion.div>
  );
}
