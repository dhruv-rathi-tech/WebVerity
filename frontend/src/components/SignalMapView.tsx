import React from 'react';
import { Finding, SeverityLevel } from '../types/audit';
import { SeverityBadge } from './SeverityBadge';
import { Activity, Bot, Compass, ArrowUpRight } from 'lucide-react';

interface SignalMapViewProps {
  findings: Finding[];
  onSelectFinding: (finding: Finding) => void;
}

export const SignalMapView: React.FC<SignalMapViewProps> = ({
  findings,
  onSelectFinding,
}) => {
  // Categorize findings into Discoverability vs Engagement
  const discoverability = findings.filter(
    (f) =>
      !f.category.toLowerCase().includes('engagement') &&
      f.category.toLowerCase() !== 'on_site_engagement'
  );
  const engagement = findings.filter(
    (f) =>
      f.category.toLowerCase().includes('engagement') ||
      f.category.toLowerCase() === 'on_site_engagement'
  );

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="workbench-panel p-5 space-y-2">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
            Forensic Signal Distribution Matrix
          </h3>
        </div>
        <p className="text-xs text-workbench-400 font-sans leading-relaxed">
          Bi-axial diagnostic map partitioning detected defects between automated AI Discoverability barriers and human On-Site Engagement friction.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left Column: AI Discoverability Axis */}
        <div className="workbench-panel p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-workbench-800 pb-3">
            <div className="flex items-center space-x-2">
              <Bot className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono font-bold uppercase text-workbench-100">
                AI Discoverability Defects ({discoverability.length})
              </span>
            </div>
            <span className="text-[10px] font-mono text-workbench-500 uppercase">Machine Access</span>
          </div>

          <div className="space-y-2.5">
            {discoverability.length === 0 ? (
              <p className="text-xs font-mono text-workbench-600 italic">No discoverability defects identified.</p>
            ) : (
              discoverability.map((f) => (
                <div
                  key={f.id}
                  onClick={() => onSelectFinding(f)}
                  className="p-3 bg-workbench-950/80 rounded border border-workbench-800 hover:border-cyan-500/80 cursor-pointer transition space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-cyan-400">{f.id}</span>
                    <SeverityBadge severity={f.severity} size="sm" />
                  </div>
                  <h4 className="text-xs font-mono font-bold text-workbench-200 truncate">
                    {f.title}
                  </h4>
                  <p className="text-[11px] text-workbench-400 line-clamp-1">
                    {f.observation}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: On-Site Engagement Axis */}
        <div className="workbench-panel p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-workbench-800 pb-3">
            <div className="flex items-center space-x-2">
              <Compass className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-mono font-bold uppercase text-workbench-100">
                On-Site Engagement Defects ({engagement.length})
              </span>
            </div>
            <span className="text-[10px] font-mono text-workbench-500 uppercase">Human UX</span>
          </div>

          <div className="space-y-2.5">
            {engagement.length === 0 ? (
              <p className="text-xs font-mono text-workbench-600 italic">No engagement defects identified.</p>
            ) : (
              engagement.map((f) => (
                <div
                  key={f.id}
                  onClick={() => onSelectFinding(f)}
                  className="p-3 bg-workbench-950/80 rounded border border-workbench-800 hover:border-emerald-500/80 cursor-pointer transition space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-emerald-400">{f.id}</span>
                    <SeverityBadge severity={f.severity} size="sm" />
                  </div>
                  <h4 className="text-xs font-mono font-bold text-workbench-200 truncate">
                    {f.title}
                  </h4>
                  <p className="text-[11px] text-workbench-400 line-clamp-1">
                    {f.observation}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
