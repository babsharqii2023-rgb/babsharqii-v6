// ═══════════════════════════════════════════════════════════════════
// TreeView — مكون عرض الشجرة الذري
// Hierarchical data display with expand/collapse
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';

interface TreeNode {
  id: string;
  label: string;
  icon?: string;
  children?: TreeNode[];
  expanded?: boolean;
  color?: string;
}

interface TreeViewProps {
  data: TreeNode[];
  onSelect?: (node: TreeNode) => void;
  selectedId?: string;
}

function TreeItem({ node, depth, onSelect, selectedId }: {
  node: TreeNode;
  depth: number;
  onSelect?: (node: TreeNode) => void;
  selectedId?: string;
}) {
  const [expanded, setExpanded] = useState(node.expanded ?? false);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedId === node.id;

  return (
    <div style={{ direction: 'rtl' }}>
      <div
        onClick={() => {
          if (hasChildren) setExpanded(!expanded);
          onSelect?.(node);
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 8px',
          paddingRight: depth * 16 + 8,
          cursor: 'pointer',
          background: isSelected ? 'rgba(13,123,181,0.15)' : 'transparent',
          borderRight: isSelected ? '2px solid #0d7bb5' : '2px solid transparent',
          borderRadius: '0 4px 4px 0',
          transition: 'background 0.15s',
          fontSize: 10,
          color: '#c8d0e0',
        }}
        onMouseEnter={(e) => {
          if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
        }}
        onMouseLeave={(e) => {
          if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent';
        }}
      >
        {hasChildren && (
          <span style={{
            fontSize: 7,
            transition: 'transform 0.2s',
            transform: expanded ? 'rotate(90deg)' : 'rotate(0)',
            display: 'inline-block',
            color: '#5a6a80',
          }}>
            ▶
          </span>
        )}
        {!hasChildren && <span style={{ width: 7 }} />}
        {node.icon && <span style={{ fontSize: 11 }}>{node.icon}</span>}
        <span style={{ fontWeight: isSelected ? 600 : 400, color: node.color || '#c8d0e0' }}>
          {node.label}
        </span>
      </div>
      {hasChildren && expanded && (
        <div>
          {node.children!.map(child => (
            <TreeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
              selectedId={selectedId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function TreeView({ data, onSelect, selectedId }: TreeViewProps) {
  return (
    <div style={{ padding: 8 }}>
      {data.map(node => (
        <TreeItem
          key={node.id}
          node={node}
          depth={0}
          onSelect={onSelect}
          selectedId={selectedId}
        />
      ))}
    </div>
  );
}
