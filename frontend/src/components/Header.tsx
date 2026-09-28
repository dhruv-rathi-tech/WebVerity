import React from 'react';
import { Terminal, Plus, FileText } from 'lucide-react';

interface HeaderProps {
  onNewAudit: () => void;
  onOpenReport?: () => void;
  isBackendConnected: boolean;
  isDemoMode: boolean;
  hasActiveReport: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onNewAudit,
  onOpenReport,
  isBackendConnected,
  isDemoMode,
  hasActiveReport,
}) => {
  return (
    <header className="border-b border-workbench-800 bg-workbench-900/95 sticky top-0 z-40 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Left: Brand / System Title */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onNewAudit}>
          <div className="w-8 h-8 rounded bg-workbench-800 border border-workbench-700 flex items-center justify-center text-cyan-400 font-mono font-bold text-sm shadow-inner">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-bold tracking-tight text-workbench-100 font-mono uppercase">
                WEBVERITY
              </h1>
              <span className="text-[10px] font-mono px-1.5 py-0.2 bg-cyan-950 text-cyan-400 border border-cyan-800/60 rounded">
                v1.0
              </span>
            </div>
            <p className="text-[11px] text-workbench-400 hidden sm:block font-mono">
              AI READINESS & WEBSITE INTELLIGENCE
            </p>
          </div>
        </div>

        {/* Right: Actions and Status Indicators */}
        <div className="flex items-center space-x-3">
          {/* Status Badge */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-workbench-950 border border-workbench-800 text-[11px] font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isBackendConnected ? 'bg-emerald-500 animate-pulse' : isDemoMode ? 'bg-amber-500' : 'bg-rose-500'
              }`}
            />
            <span className="text-workbench-300">
              {isBackendConnected ? 'API Connected' : isDemoMode ? 'Demo Mode' : 'Offline'}
            </span>
          </div>

          {hasActiveReport && onOpenReport && (
            <button
              onClick={onOpenReport}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono bg-workbench-800 hover:bg-workbench-700 text-workbench-200 border border-workbench-700 transition"
              title="View Markdown Report"
            >
              <FileText className="w-3.5 h-3.5 text-workbench-400" />
              <span>Report</span>
            </button>
          )}

          <button
            onClick={onNewAudit}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium bg-cyan-600 hover:bg-cyan-500 text-white transition shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Investigation</span>
          </button>
        </div>
      </div>
    </header>
  );
};
