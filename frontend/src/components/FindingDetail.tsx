import React, { useState } from 'react';
import {
  Finding,
  SeverityLevel
} from '../types/audit';
import { SeverityBadge } from './SeverityBadge';
import {
  ExternalLink,
  Copy,
  Check,
  ArrowDown,
  AlertTriangle,
  FileCode,
  ShieldCheck,
  Cpu,
  Layers,
  Sparkles
} from 'lucide-react';

interface FindingDetailProps {
  finding: Finding | null;
}

export const FindingDetail: React.FC<FindingDetailProps> = ({ finding }) => {
  const [copied, setCopied] = useState(false);

  if (!finding) {
    return (
      <div className="workbench-panel p-8 text-center text-workbench-500 font-mono text-xs flex flex-col items-center justify-center min-h-[400px]">
        <FileCode className="w-8 h-8 text-workbench-700 mb-2" />
        <span>Select a finding from the list to inspect forensic evidence and causal analysis.</span>
      </div>
    );
  }

  const handleCopyEvidence = () => {
    navigator.clipboard.writeText(finding.evidence);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="workbench-panel p-5 sm:p-6 space-y-6 overflow-y-auto max-h-[calc(100vh-210px)]">
      {/* Finding Header */}
      <div className="space-y-2 border-b border-workbench-800 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-950 px-2 py-0.5 border border-cyan-800 rounded">
              {finding.id}
            </span>
            <SeverityBadge severity={finding.severity} />
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-workbench-800 text-workbench-300 border border-workbench-700">
              {finding.category.replace(/_/g, ' ')}
            </span>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono text-workbench-400">
            <span>Confidence: <strong className="text-workbench-200 uppercase">{finding.confidence}</strong></span>
            <span>•</span>
            <span>Method: <strong className="text-workbench-200">{finding.detection_method}</strong></span>
          </div>
        </div>

        <h3 className="text-base sm:text-lg font-bold text-workbench-100 font-mono leading-snug">
          {finding.title}
        </h3>
      </div>

      {/* Visual Causal Chain Flow */}
      <div className="space-y-4">
        {/* Step 1: Observation */}
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2 text-xs font-mono font-bold uppercase tracking-wider text-workbench-300">
            <span className="w-4 h-4 rounded bg-workbench-800 flex items-center justify-center text-[10px] text-cyan-400">1</span>
            <span>Observation</span>
          </div>
          <div className="p-3 bg-workbench-950/60 border border-workbench-800 rounded text-xs text-workbench-200 leading-relaxed font-sans">
            {finding.observation}
          </div>
        </div>

        {/* Chain Arrow */}
        <div className="flex justify-center text-workbench-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* Step 2: Evidence */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-xs font-mono font-bold uppercase tracking-wider text-workbench-300">
              <span className="w-4 h-4 rounded bg-workbench-800 flex items-center justify-center text-[10px] text-cyan-400">2</span>
              <span>Forensic Evidence</span>
            </div>
            <button
              onClick={handleCopyEvidence}
              className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-workbench-800 hover:bg-workbench-700 text-workbench-300 border border-workbench-700 transition"
              title="Copy raw evidence text"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <div className="forensic-code-block max-h-56">
            {finding.evidence}
          </div>
        </div>

        {/* Chain Arrow */}
        <div className="flex justify-center text-workbench-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* Step 3: Root Cause */}
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2 text-xs font-mono font-bold uppercase tracking-wider text-workbench-300">
            <span className="w-4 h-4 rounded bg-workbench-800 flex items-center justify-center text-[10px] text-cyan-400">3</span>
            <span>Root Cause</span>
          </div>
          <div className="p-3 bg-workbench-950/60 border border-workbench-800 rounded text-xs text-workbench-200 leading-relaxed font-sans">
            {finding.root_cause}
          </div>
        </div>

        {/* Chain Arrow */}
        <div className="flex justify-center text-workbench-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* Step 4: Impact */}
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2 text-xs font-mono font-bold uppercase tracking-wider text-workbench-300">
            <span className="w-4 h-4 rounded bg-workbench-800 flex items-center justify-center text-[10px] text-cyan-400">4</span>
            <span>Impact on AI Discoverability & Engagement</span>
          </div>
          <div className="p-3 bg-amber-950/20 border border-amber-900/40 rounded text-xs text-amber-200/90 leading-relaxed font-sans">
            {finding.impact}
          </div>
        </div>

        {/* Chain Arrow */}
        <div className="flex justify-center text-workbench-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* Step 5: Suggested Action */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-xs font-mono font-bold uppercase tracking-wider text-workbench-300">
              <span className="w-4 h-4 rounded bg-emerald-950 flex items-center justify-center text-[10px] text-emerald-400">5</span>
              <span>Recommended Remediation</span>
            </div>
            <SeverityBadge severity={finding.suggested_action.priority || finding.severity} size="sm" />
          </div>
          <div className="p-3.5 bg-emerald-950/20 border border-emerald-900/50 rounded space-y-2 text-xs font-sans">
            <p className="text-emerald-200 font-medium leading-relaxed">
              {finding.suggested_action.summary}
            </p>
            {finding.suggested_action.implementation_details && (
              <div className="pt-2 border-t border-emerald-900/40 text-[11px] font-mono text-emerald-300/80">
                <strong>Implementation Guidance: </strong>
                {finding.suggested_action.implementation_details}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Affected URLs Section */}
      <div className="space-y-2 border-t border-workbench-800 pt-4">
        <div className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-400">
          Affected URLs ({finding.affected_urls.length})
        </div>
        <div className="space-y-1.5 font-mono text-xs">
          {finding.affected_urls.map((url, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 bg-workbench-950 border border-workbench-800 rounded group hover:border-workbench-700 transition"
            >
              <span className="text-workbench-300 truncate mr-2">{url}</span>
              <a
                href={url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-workbench-500 hover:text-cyan-400 transition shrink-0"
                title="Open in new tab"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
