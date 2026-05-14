'use client';

import React from 'react';
import type { UIDirective, UIAction } from '@/lib/ui-directive';
import MetricCard from '@/components/atomic/MetricCard';
import DataTable from '@/components/atomic/DataTable';
import ProgressBar from '@/components/atomic/ProgressBar';
import CodeBlock from '@/components/atomic/CodeBlock';
import StatusBadge from '@/components/atomic/StatusBadge';
import ActionButtons from '@/components/atomic/ActionButtons';

interface DefaultScreenProps {
  directive?: UIDirective;
  onAction?: (action: { intent: string; payload?: Record<string, unknown> }) => void;
  [key: string]: unknown;
}

function renderSection(
  section: UIDirective['sections'][0],
  onAction?: (action: UIAction) => void
) {
  const commonProps = { ...section.props };

  switch (section.type) {
    case 'MetricCard':
      return <MetricCard {...commonProps as any} />;
    case 'DataTable':
      return (
        <DataTable
          data={(commonProps.data as Record<string, unknown>[]) || []}
          columns={(commonProps.columns as string[]) || []}
          onRowClick={section.actions?.[0] ? (row) => {
            onAction?.({ trigger: 'click', intentId: section.actions![0].intentId, payload: row });
          } : undefined}
        />
      );
    case 'ProgressBar':
      return <ProgressBar {...commonProps as any} />;
    case 'CodeBlock':
      return <CodeBlock {...commonProps as any} />;
    case 'StatusBadge':
      return <StatusBadge status={String(commonProps.status || 'active')} size={(commonProps.size as 'sm' | 'md' | 'lg') || 'md'} />;
    case 'ActionButtons':
      return (
        <ActionButtons
          buttons={(commonProps.buttons as Array<{ label: string; intentId: string; variant: 'approve' | 'reject' | 'modify'; payload?: Record<string, unknown> }>) || []}
          onAction={(btn) => {
            onAction?.({ trigger: 'click', intentId: btn.intentId, payload: btn.payload });
          }}
        />
      );
    default:
      return <MetricCard title="بيانات" value={JSON.stringify(commonProps).slice(0, 50)} />;
  }
}

export default function DefaultScreen({ directive, onAction, ...rest }: DefaultScreenProps) {
  // If no directive, try to generate from props
  if (!directive) {
    return (
      <div style={{ padding: 24, color: '#5a6a80', textAlign: 'center' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>⚡</div>
        <div style={{ fontSize: 14 }}>أرسل رسالة لبدء التفاعل مع العقل الخارق</div>
      </div>
    );
  }

  const gridCols = directive.layout === 'grid' ? 12 : directive.layout === 'split' ? 2 : 1;

  return (
    <div style={{
      padding: 16,
      display: 'grid',
      gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
      gap: 12,
      direction: 'rtl',
    }}>
      {directive.sections
        .sort((a, b) => (a.order || 0) - (b.order || 0))
        .map((section, i) => (
          <div
            key={i}
            style={{
              gridColumn: `span ${Math.min(section.span || gridCols, gridCols)}`,
            }}
          >
            {renderSection(section, onAction ? (action) => {
              onAction({ intent: action.intentId, payload: action.payload });
            } : undefined)}
          </div>
        ))}
    </div>
  );
}
