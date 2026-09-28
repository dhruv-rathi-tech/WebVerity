import React, { useState, useMemo } from 'react';
import { Finding, SeverityLevel } from '../types/audit';
import { SeverityBadge } from './SeverityBadge';
import { Search, Filter, AlertCircle, CheckCircle2, ChevronRight } from 'lucide-react';

interface FindingsListProps {
  findings: Finding[];
  selectedFindingId: string | null;
  onSelectFinding: (finding: Finding) => void;
}

export const FindingsList: React.FC<FindingsListProps> = ({
  findings,
  selectedFindingId,
  onSelectFinding,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');

  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      const matchesSev = selectedSeverity === 'all' || f.severity.toLowerCase() === selectedSeverity.toLowerCase();
      const matchesSearch =
        !searchQuery.trim() ||
        f.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.observation.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSev && matchesSearch;
    });
  }, [findings, selectedSeverity, searchQuery]);

  // Severity counts
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: findings.length, critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    findings.forEach((f) => {
      const s = f.severity.toLowerCase();
      if (c[s] !== undefined) c[s]++;
    });
    return c;
  }, [findings]);

  return (
    <div className="space-y-3 flex flex-col h-full">
      {/* Search & Filter Bar */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-workbench-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search findings (e.g., F-001, CSR, price)..."
            className="w-full pl-9 pr-3 py-2 bg-workbench-950 border border-workbench-800 rounded text-xs text-workbench-200 font-mono placeholder:text-workbench-600 focus:outline-none focus:border-cyan-500 transition"
          />
        </div>

        {/* Severity Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
          {(['all', 'critical', 'high', 'medium', 'low', 'info'] as const).map((sev) => {
            const count = counts[sev] || 0;
            const isSelected = selectedSeverity === sev;
            return (
              <button
                key={sev}
                onClick={() => setSelectedSeverity(sev)}
                className={`px-2 py-0.5 rounded border transition flex items-center space-x-1 ${
                  isSelected
                    ? 'bg-workbench-800 border-cyan-500 text-cyan-300 font-bold'
                    : 'bg-workbench-950 border-workbench-800 text-workbench-400 hover:text-workbench-200 hover:border-workbench-700'
                }`}
              >
                <span className="uppercase">{sev}</span>
                <span className="text-[10px] px-1 rounded bg-workbench-900 text-workbench-400">
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Findings List Container */}
      <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-270px)] pr-1 flex-1">
        {filteredFindings.length === 0 ? (
          <div className="workbench-panel p-8 text-center text-workbench-500 font-mono text-xs">
            {findings.length === 0 ? (
              <div className="space-y-2">
                <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
                <p className="text-workbench-300 font-bold">NO CONFIRMED DEFECTS</p>
                <p className="text-workbench-500 text-[11px]">
                  The audit did not detect evidence-backed defects in the sampled pages.
                </p>
              </div>
            ) : (
              <span>No findings match the active filter.</span>
            )}
          </div>
        ) : (
          filteredFindings.map((f) => {
            const isSelected = selectedFindingId === f.id;
            return (
              <div
                key={f.id}
                onClick={() => onSelectFinding(f)}
                className={`p-3.5 rounded border cursor-pointer transition text-left space-y-2 ${
                  isSelected
                    ? 'bg-workbench-800/90 border-cyan-500/80 shadow-md ring-1 ring-cyan-500/30'
                    : 'bg-workbench-900/60 border-workbench-800/80 hover:bg-workbench-850 hover:border-workbench-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-workbench-200">
                      {f.id}
                    </span>
                    <SeverityBadge severity={f.severity} size="sm" />
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-workbench-950 text-workbench-400 border border-workbench-800">
                      {f.category.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <ChevronRight
                    className={`w-3.5 h-3.5 transition ${
                      isSelected ? 'text-cyan-400 transform translate-x-0.5' : 'text-workbench-600'
                    }`}
                  />
                </div>

                <h4 className="text-xs font-bold text-workbench-100 font-mono leading-snug">
                  {f.title}
                </h4>

                <p className="text-[11px] text-workbench-400 line-clamp-2 leading-relaxed">
                  {f.observation}
                </p>

                <div className="flex items-center justify-between text-[10px] font-mono text-workbench-500 pt-1 border-t border-workbench-800/60">
                  <span>Confidence: {f.confidence}</span>
                  <span>{f.affected_urls.length} affected {f.affected_urls.length === 1 ? 'URL' : 'URLs'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
