import React from 'react';
import { Finding, ProactiveRecommendation, SeverityLevel } from '../types/audit';
import { SeverityBadge } from './SeverityBadge';
import { CheckCircle2, ArrowRight, Lightbulb, AlertTriangle, ShieldCheck, ListOrdered } from 'lucide-react';

interface RecommendationsViewProps {
  findings: Finding[];
  proactiveRecommendations: ProactiveRecommendation[];
  onSelectFinding: (finding: Finding) => void;
}

export const RecommendationsView: React.FC<RecommendationsViewProps> = ({
  findings,
  proactiveRecommendations,
  onSelectFinding,
}) => {
  // Sort findings by severity priority
  const severityRank: Record<SeverityLevel, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
    info: 4,
  };

  const sortedFindings = [...findings].sort(
    (a, b) => severityRank[a.severity] - severityRank[b.severity]
  );

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Section 1: Confirmed Defect Remediation Queue */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-workbench-800 pb-3">
          <div className="flex items-center space-x-2">
            <ListOrdered className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
              Prioritized Defect Remediation Queue ({findings.length})
            </h3>
          </div>
          <span className="text-[11px] font-mono text-workbench-400">
            Ranked by AI discoverability & engagement impact
          </span>
        </div>

        {sortedFindings.length === 0 ? (
          <div className="workbench-panel p-6 text-center space-y-2 font-mono text-xs text-workbench-400">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
            <p className="text-workbench-200 font-bold">ZERO CONFIRMED DEFECTS</p>
            <p className="text-workbench-500 text-[11px]">
              No evidence-backed defects require immediate engineering remediation.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedFindings.map((finding, index) => (
              <div
                key={finding.id}
                className="workbench-panel p-4 space-y-3 border-l-4 transition hover:border-cyan-500"
                style={{
                  borderLeftColor:
                    finding.severity === 'critical'
                      ? '#ef4444'
                      : finding.severity === 'high'
                      ? '#f97316'
                      : finding.severity === 'medium'
                      ? '#eab308'
                      : finding.severity === 'low'
                      ? '#3b82f6'
                      : '#64748b',
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-workbench-400">
                      #{index + 1}
                    </span>
                    <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950 px-2 py-0.5 border border-cyan-800 rounded">
                      {finding.id}
                    </span>
                    <SeverityBadge severity={finding.suggested_action.priority || finding.severity} size="sm" />
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-workbench-950 text-workbench-400 border border-workbench-800">
                      {finding.category.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <button
                    onClick={() => onSelectFinding(finding)}
                    className="inline-flex items-center space-x-1 text-xs font-mono text-cyan-400 hover:text-cyan-300 transition"
                  >
                    <span>Investigate Evidence</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-workbench-100 font-mono">
                    {finding.title}
                  </h4>
                  <p className="text-xs text-workbench-300 leading-relaxed font-sans">
                    <strong>Action: </strong> {finding.suggested_action.summary}
                  </p>
                  {finding.suggested_action.implementation_details && (
                    <p className="text-[11px] font-mono text-workbench-400 bg-workbench-950 p-2 rounded border border-workbench-850 mt-1">
                      <strong>Guidance: </strong> {finding.suggested_action.implementation_details}
                    </p>
                  )}
                </div>

                <div className="text-[11px] text-workbench-500 font-mono pt-1 flex items-center justify-between">
                  <span>Scope: {finding.affected_urls.length} affected {finding.affected_urls.length === 1 ? 'URL' : 'URLs'}</span>
                  <span>Impact: {finding.impact.slice(0, 70)}...</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 2: Proactive Graph Grounding Opportunities */}
      <div className="space-y-4 pt-4 border-t border-workbench-800">
        <div className="flex items-center space-x-2">
          <Lightbulb className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
            Proactive Entity Grounding Opportunities ({proactiveRecommendations.length})
          </h3>
        </div>

        <p className="text-xs text-workbench-400">
          These items are not defects or regressions, but proactive architectural optimizations to enhance universal knowledge graph disambiguation and entity authority.
        </p>

        {proactiveRecommendations.length === 0 ? (
          <div className="workbench-panel p-5 text-center text-workbench-500 font-mono text-xs">
            No proactive entity recommendations generated for this site archetype.
          </div>
        ) : (
          <div className="space-y-3">
            {proactiveRecommendations.map((rec) => (
              <div
                key={rec.id}
                className="workbench-panel p-4 space-y-2 border-l-4 border-l-amber-500/70"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold text-amber-400 bg-amber-950 px-2 py-0.5 border border-amber-800 rounded">
                    {rec.id}
                  </span>
                  <span className="text-xs font-bold text-workbench-100 font-mono">
                    {rec.title}
                  </span>
                </div>

                <p className="text-xs text-workbench-300 leading-relaxed font-sans">
                  <strong>Opportunity: </strong> {rec.opportunity}
                </p>

                <div className="p-2.5 bg-workbench-950 rounded border border-workbench-850 text-xs font-mono text-workbench-300 space-y-1">
                  <div>
                    <strong className="text-workbench-400">Recommended Enhancement: </strong>
                    {rec.suggested_action.summary}
                  </div>
                  {rec.suggested_action.implementation_details && (
                    <div className="text-[11px] text-workbench-500">
                      <strong>Code Spec: </strong> {rec.suggested_action.implementation_details}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
