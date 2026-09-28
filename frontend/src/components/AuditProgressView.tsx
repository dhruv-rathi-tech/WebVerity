import React, { useState, useEffect } from 'react';
import { Loader2, CheckCircle2, Clock, Globe, ShieldAlert } from 'lucide-react';

interface AuditProgressViewProps {
  targetUrl: string;
}

const STAGES = [
  { id: 1, name: 'URL Validation & Host Resolution', time: 0 },
  { id: 2, name: 'Robots.txt & Sitemap Inspection', time: 1 },
  { id: 3, name: 'Bounded Multi-Page Crawl & Evidence Gathering', time: 2 },
  { id: 4, name: 'Crawl & Render Analysis (CSR Content Loss)', time: 3 },
  { id: 5, name: 'Structured Data & Entity Graph Validation', time: 4 },
  { id: 6, name: 'Freshness & Cross-Page Contradiction Audit', time: 5 },
  { id: 7, name: 'On-Site Engagement & Heading Hierarchy Inspection', time: 6 },
  { id: 8, name: 'Cross-Skill Deduplication & Finding Synthesis', time: 7 },
];

export const AuditProgressView: React.FC<AuditProgressViewProps> = ({ targetUrl }) => {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="max-w-3xl mx-auto px-4 py-12 space-y-8">
      {/* Target Header */}
      <div className="workbench-panel p-6 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400 bg-cyan-950/60 px-2.5 py-0.5 border border-cyan-800/80 rounded">
            Investigation in Progress
          </span>
          <div className="flex items-center space-x-1.5 text-xs font-mono text-workbench-400">
            <Clock className="w-3.5 h-3.5" />
            <span>Elapsed: {seconds}s</span>
          </div>
        </div>

        <div className="flex items-center space-x-2 pt-1">
          <Globe className="w-4 h-4 text-workbench-400 shrink-0" />
          <h2 className="text-sm sm:text-base font-mono font-bold text-workbench-100 truncate">
            {targetUrl}
          </h2>
        </div>
      </div>

      {/* Stage Progression Checklist */}
      <div className="workbench-panel p-6 space-y-4">
        <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-300 border-b border-workbench-800 pb-3">
          Audit Pipeline Execution
        </h3>

        <div className="space-y-3 font-mono text-xs">
          {STAGES.map((stage) => {
            const isCompleted = seconds >= stage.time + 2;
            const isCurrent = seconds >= stage.time && seconds < stage.time + 2;

            return (
              <div
                key={stage.id}
                className={`flex items-center justify-between p-2.5 rounded border transition ${
                  isCompleted
                    ? 'bg-workbench-950/60 border-workbench-800/80 text-workbench-300'
                    : isCurrent
                    ? 'bg-cyan-950/20 border-cyan-800/60 text-cyan-300 font-medium'
                    : 'bg-workbench-950/30 border-workbench-900 text-workbench-600'
                }`}
              >
                <div className="flex items-center space-x-3">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-cyan-400 animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-workbench-700 shrink-0" />
                  )}
                  <span>{stage.name}</span>
                </div>
                <span className="text-[10px] uppercase text-workbench-500">
                  {isCompleted ? 'Done' : isCurrent ? 'Running...' : 'Pending'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Honest Status telemetry */}
      <div className="p-3 bg-workbench-950 border border-workbench-800 rounded flex items-center justify-between text-[11px] font-mono text-workbench-400">
        <span>Engine: Python Asynchronous Orchestrator</span>
        <span>Politeness: Bounded Concurrency (5 req/s)</span>
      </div>
    </div>
  );
};
