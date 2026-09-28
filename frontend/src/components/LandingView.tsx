import React, { useState } from 'react';
import {
  Search,
  Sliders,
  Shield,
  Bot,
  Compass,
} from 'lucide-react';
import type { AuditRequestOptions } from '../types/audit';

interface LandingViewProps {
  onStartAudit: (options: AuditRequestOptions) => void;
  onLoadDemo: (type: 'ecommerce' | 'healthy') => void;
  isLoading: boolean;
  errorMessage?: string | null;
}

export const LandingView: React.FC<LandingViewProps> = ({
  onStartAudit,
  onLoadDemo,
  isLoading,
  errorMessage,
}) => {
  const [url, setUrl] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [maxPages, setMaxPages] = useState(10);
  const [maxDepth, setMaxDepth] = useState(2);
  const [timeout, setTimeoutVal] = useState(15);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    onStartAudit({
      url: url.trim(),
      max_pages: maxPages,
      max_depth: maxDepth,
      timeout,
    });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12 space-y-10">
      {/* Workbench Welcome Banner */}
      <div className="text-center space-y-3 max-w-2xl mx-auto">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-workbench-900 border border-workbench-700 text-xs font-mono text-cyan-400">
          <Shield className="w-3.5 h-3.5" />
          <span>Evidence-Driven Website Intelligence</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-workbench-100">
          WEBVERITY
        </h2>
        <p className="text-xs font-mono uppercase tracking-wider text-cyan-400">
          AI Readiness & Website Intelligence Workbench
        </p>
        <p className="text-sm text-workbench-400 leading-relaxed">
          Investigate what your website exposes to machines and people. Analyzes how discoverable, machine-readable, schema-grounded, and engaging a public website is for modern AI systems and visitors.
        </p>
      </div>

      {/* Audit Target Input Card */}
      <div className="workbench-panel p-6 shadow-xl border-workbench-700">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="target-url" className="block text-xs font-mono font-medium text-workbench-300 uppercase tracking-wider">
              Target Website URL
            </label>
            <div className="flex flex-col sm:flex-row items-stretch gap-2">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-workbench-500 font-mono text-xs">
                  https://
                </div>
                <input
                  id="target-url"
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="example.com or https://company.com"
                  className="w-full pl-20 pr-4 py-2.5 bg-workbench-950 border border-workbench-700 rounded text-sm text-workbench-100 font-mono placeholder:text-workbench-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={isLoading || !url.trim()}
                className="inline-flex items-center justify-center space-x-2 px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:bg-workbench-800 disabled:text-workbench-600 text-white font-mono text-xs font-semibold rounded uppercase tracking-wider transition shadow-sm"
              >
                <Search className="w-4 h-4" />
                <span>Run Investigation</span>
              </button>
            </div>
          </div>

          {/* Quick Presets & Advanced Options */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs font-mono">
            <div className="flex items-center space-x-2 text-workbench-400">
              <span>Sample Targets:</span>
              <button
                type="button"
                onClick={() => onLoadDemo('ecommerce')}
                className="px-2.5 py-1 rounded bg-workbench-800 hover:bg-workbench-700 text-cyan-300 border border-workbench-700 transition"
              >
                E-Commerce (Defects)
              </button>
              <button
                type="button"
                onClick={() => onLoadDemo('healthy')}
                className="px-2.5 py-1 rounded bg-workbench-800 hover:bg-workbench-700 text-emerald-300 border border-workbench-700 transition"
              >
                Healthy Baseline (0 Defects)
              </button>
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="inline-flex items-center space-x-1 text-workbench-400 hover:text-workbench-200 transition"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>{showAdvanced ? 'Hide Options' : 'Crawl Parameters'}</span>
            </button>
          </div>

          {/* Advanced Configuration Accordion */}
          {showAdvanced && (
            <div className="pt-4 border-t border-workbench-800/80 grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
              <div className="space-y-1">
                <label className="text-workbench-400">Max Pages (1-20)</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  className="w-full px-3 py-1.5 bg-workbench-950 border border-workbench-800 rounded text-workbench-200"
                />
              </div>
              <div className="space-y-1">
                <label className="text-workbench-400">Max Depth (1-3)</label>
                <input
                  type="number"
                  min={1}
                  max={3}
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Number(e.target.value))}
                  className="w-full px-3 py-1.5 bg-workbench-950 border border-workbench-800 rounded text-workbench-200"
                />
              </div>
              <div className="space-y-1">
                <label className="text-workbench-400">Timeout Seconds</label>
                <input
                  type="number"
                  min={5}
                  max={60}
                  value={timeout}
                  onChange={(e) => setTimeoutVal(Number(e.target.value))}
                  className="w-full px-3 py-1.5 bg-workbench-950 border border-workbench-800 rounded text-workbench-200"
                />
              </div>
            </div>
          )}

          {errorMessage && (
            <div className="p-3 bg-red-950/50 border border-red-800/80 rounded text-xs font-mono text-red-300">
              {errorMessage}
            </div>
          )}
        </form>
      </div>

      {/* Technical Category Taxonomy Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Category Group 1: AI Discoverability */}
        <div className="workbench-panel p-5 space-y-4">
          <div className="flex items-center space-x-2 border-b border-workbench-800 pb-3">
            <Bot className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
              AI Discoverability & Machine Readability
            </h3>
          </div>
          <div className="space-y-3 text-xs">
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-cyan-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Crawlability & Bot Access:</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Validates robots.txt AI user-agent directives, sitemap extraction, and network transport health.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-cyan-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Machine Readability (CSR vs Raw):</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Detects pricing, technical specs, or body copy omitted from initial HTML and trapped behind client-side rendering.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-cyan-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Structured Data (JSON-LD):</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Validates schema.org syntax, entity representation, and flags contradictions between schema and rendered text.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-cyan-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Freshness & Factual Consistency:</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Identifies temporal staleness and cross-page factual contradictions across site pages.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Category Group 2: On-Site Engagement */}
        <div className="workbench-panel p-5 space-y-4">
          <div className="flex items-center space-x-2 border-b border-workbench-800 pb-3">
            <Compass className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
              On-Site Engagement & Information Architecture
            </h3>
          </div>
          <div className="space-y-3 text-xs">
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-emerald-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Value Proposition Orientation:</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Audits semantic H1 clarity, hero messaging, and above-the-fold value proposition visibility.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-emerald-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Semantic Heading Hierarchy:</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Flags skipped heading levels (H1 to H3), missing titles, and disorganized document outlines.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-emerald-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Next-Step Pathways & Conversion:</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Detects dead-end pages lacking clear navigation, related links, or contextual next-step calls to action.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-2.5">
              <span className="font-mono text-emerald-400 mt-0.5">•</span>
              <div>
                <strong className="text-workbench-200 font-mono">Answer Discoverability:</strong>
                <p className="text-workbench-400 text-[11px] mt-0.5">
                  Inspects FAQ clarity and ensures crucial answers are not buried in inaccessible markup.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Safety Notice */}
      <div className="p-4 bg-workbench-900/50 border border-workbench-800 rounded flex items-center space-x-3 text-xs font-mono text-workbench-400">
        <Shield className="w-4 h-4 text-cyan-400 shrink-0" />
        <span>
          <strong>Read-Only Forensic Engine:</strong> Bounded crawling, strict robots.txt compliance, no form submission, and zero invasive actions.
        </span>
      </div>
    </div>
  );
};
