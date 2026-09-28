import React, { useMemo } from 'react';
import { Finding } from '../types/audit';
import { SeverityBadge } from './SeverityBadge';
import { Compass, ArrowRight, CheckCircle2, Navigation, Layers, HelpCircle } from 'lucide-react';

interface EngagementViewProps {
  findings: Finding[];
  onSelectFinding: (finding: Finding) => void;
}

export const EngagementView: React.FC<EngagementViewProps> = ({
  findings,
  onSelectFinding,
}) => {
  const engagementFindings = useMemo(() => {
    return findings.filter((f) =>
      f.category.toLowerCase().includes('engagement') ||
      f.category.toLowerCase() === 'on_site_engagement'
    );
  }, [findings]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header telemetry banner */}
      <div className="workbench-panel p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Compass className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
              On-Site Engagement & Information Architecture
            </h3>
          </div>
          <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-950 px-2 py-0.5 border border-emerald-800 rounded">
            {engagementFindings.length} {engagementFindings.length === 1 ? 'Finding' : 'Findings'} Detected
          </span>
        </div>
        <p className="text-xs text-workbench-400 font-sans leading-relaxed">
          Audits the human and navigational agent experience across visited pages. Identifies broken heading outlines, missing primary value proposition messaging, dead-end conversion pathways, and buried answers.
        </p>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {engagementFindings.length === 0 ? (
          <div className="workbench-panel p-8 text-center space-y-2 font-mono text-xs text-workbench-400">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
            <p className="text-workbench-200 font-bold">OPTIMAL ON-SITE ENGAGEMENT</p>
            <p className="text-workbench-500 text-[11px]">
              Sampled pages exhibit clear semantic heading structure and accessible internal conversion paths.
            </p>
          </div>
        ) : (
          engagementFindings.map((finding) => (
            <div
              key={finding.id}
              className="workbench-panel p-4 space-y-2.5 transition hover:border-workbench-700"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-950 px-2 py-0.5 border border-emerald-800 rounded">
                    {finding.id}
                  </span>
                  <SeverityBadge severity={finding.severity} size="sm" />
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-workbench-950 text-workbench-400 border border-workbench-800 uppercase">
                    {finding.category.replace(/_/g, ' ')}
                  </span>
                </div>

                <button
                  onClick={() => onSelectFinding(finding)}
                  className="inline-flex items-center space-x-1 text-xs font-mono text-emerald-400 hover:text-emerald-300 transition"
                >
                  <span>Examine Evidence</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <h4 className="text-sm font-bold text-workbench-100 font-mono">
                {finding.title}
              </h4>

              <p className="text-xs text-workbench-300 font-sans leading-relaxed">
                {finding.observation}
              </p>

              <div className="pt-2 border-t border-workbench-800 flex items-center justify-between text-[11px] font-mono text-workbench-500">
                <span>Confidence: {finding.confidence}</span>
                <span>{finding.affected_urls.length} Affected URLs</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
