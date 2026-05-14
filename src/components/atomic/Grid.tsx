'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface GridProps {
  columns?: number;
  gap?: number;
  children: React.ReactNode;
}

const T = {
  card: '#0d0d1a',
  text: '#c8d0e0',
  textDim: '#5a6a80',
};

export default function Grid({ columns = 3, gap = 16, children }: GridProps) {
  const childArray = React.Children.toArray(children);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
        gap,
        width: '100%',
      }}
    >
      {childArray.map((child, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: i * 0.05 }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}
