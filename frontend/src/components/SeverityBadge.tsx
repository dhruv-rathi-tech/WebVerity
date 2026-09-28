import React from 'react';
import { SeverityLevel } from '../types/audit';

interface SeverityBadgeProps {
  severity: SeverityLevel | string;
  size?: 'sm' | 'md';
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, size = 'md', className = '' }) => {
  const sev = (severity || 'info').toLowerCase() as SeverityLevel;

  const styles: Record<SeverityLevel, { bg: string; text: string; border: string }> = {
    critical: {
      bg: 'bg-red-950/60',
      text: 'text-red-400',
      border: 'border-red-800/80',
    },
    high: {
      bg: 'bg-amber-950/60',
      text: 'text-amber-400',
      border: 'border-amber-800/80',
    },
    medium: {
      bg: 'bg-yellow-950/50',
      text: 'text-yellow-400',
      border: 'border-yellow-700/70',
    },
    low: {
      bg: 'bg-blue-950/50',
      text: 'text-blue-400',
      border: 'border-blue-800/70',
    },
    info: {
      bg: 'bg-slate-900',
      text: 'text-slate-400',
      border: 'border-slate-700',
    },
  };

  const style = styles[sev] || styles.info;
  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5';

  return (
    <span
      className={`inline-flex items-center font-mono font-semibold uppercase tracking-wider rounded border ${style.bg} ${style.text} ${style.border} ${sizeClasses} ${className}`}
    >
      {sev}
    </span>
  );
};
