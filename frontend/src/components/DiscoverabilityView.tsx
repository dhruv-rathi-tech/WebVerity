import React, { useMemo } from 'react';
import { Finding } from '../types/audit';
import { SeverityBadge } from './SeverityBadge';
import { Bot, ArrowRight, CheckCircle2, ShieldAlert, FileSearch, Database, Sparkles } from 'lucide-react';

interface DiscoverabilityViewProps {
  findings: Finding[];
  onSelectFinding: (finding: Finding) => void;
}

const DISCOVERABILITY_CATEGORIES = [
  'crawlability',
  'machine_readability',
  'structured_data',
  'entity_clarity',
  'freshness_corroboration',
];

export const DiscoverabilityView: React.FC<DiscoverabilityViewProps> = ({
  findings,
  onSelectFinding,
}) => {
  const discoverabilityFindings = useMemo(() => {
    return findings.filter((f) =>
      DISCOVERABILITY_CATEGORIES.includes(f.category.toLowerCase())
    );
  }, [findings]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header telemetry banner */}
      <div className="workbench-panel p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Bot className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
              AI Discoverability & Machine Readability
            </h3>
          </div>
          <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950 px-2 py-0.5 border border-cyan-800 rounded">
            {discoverabilityFindings.length} {discoverabilityFindings.length === 1 ? 'Finding' : 'Findings'} Detected
          </span>
        </div>
        <p className="text-xs text-workbench-400 font-sans leading-relaxed">
          Assesses how automated AI crawlers, LLM search engines, and structured data extractors perceive your site. Identifies robots.txt AI bot exclusions, client-side JavaScript rendering content loss, schema syntax & semantic contradictions, and temporal staleness.
        </p>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {discoverabilityFindings.length === 0 ? (
          <div className="workbench-panel p-8 text-center space-y-2 font-mono text-xs text-workbench-400">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
            <p className="text-workbench-200 font-bold">NO AI DISCOVERABILITY BARRIERS</p>
            <p className="text-workbench-500 text-[11px]">
              Sampled pages exhibit valid schema, server-rendered content, and open bot crawlability.
            </p>
          </div>
        ) : (
          discoverabilityFindings.map((finding) => (
            <div
              key={finding.id}
              className="workbench-panel p-4 space-y-2.5 transition hover:border-workbench-700"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950 px-2 py-0.5 border border-cyan-800 rounded">
                    {finding.id}
                  </span>
                  <SeverityBadge severity={finding.severity} size="sm" />
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-workbench-950 text-workbench-400 border border-workbench-800 uppercase">
                    {finding.category.replace(/_/g, ' ')}
                  </span>
                </div>

                <button
                  onClick={() => onSelectFinding(finding)}
                  className="inline-flex items-center space-x-1 text-xs font-mono text-cyan-400 hover:text-cyan-300 transition"
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
