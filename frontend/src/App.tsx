import React, { useState, useEffect } from 'react';
import {
  AuditReport,
  AuditRequestOptions,
  Finding
} from './types/audit';
import { auditApi, AuditApiError } from './api/auditApi';
import { Header } from './components/Header';
import { LandingView } from './components/LandingView';
import { AuditProgressView } from './components/AuditProgressView';
import { FindingsList } from './components/FindingsList';
import { FindingDetail } from './components/FindingDetail';
import { PagesInspector } from './components/PagesInspector';
import { RecommendationsView } from './components/RecommendationsView';
import { DiscoverabilityView } from './components/DiscoverabilityView';
import { EngagementView } from './components/EngagementView';
import { SignalMapView } from './components/SignalMapView';
import { RawReportModal } from './components/RawReportModal';
import {
  Shield,
  Layers,
  Bot,
  Compass,
  FileSearch,
  ListOrdered,
  Activity,
  Globe,
  Clock,
  ExternalLink,
  RefreshCw,
  FileText
} from 'lucide-react';

type ActiveTab =
  | 'findings'
  | 'discoverability'
  | 'engagement'
  | 'pages'
  | 'recommendations'
  | 'signal_map';

export function App() {
  const [view, setView] = useState<'landing' | 'running' | 'results'>('landing');
  const [targetUrl, setTargetUrl] = useState<string>('');
  const [report, setReport] = useState<AuditReport | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('findings');
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [showReportModal, setShowReportModal] = useState<boolean>(false);

  // Check backend health on initial load
  useEffect(() => {
    auditApi
      .checkHealth()
      .then(() => {
        setIsBackendConnected(true);
      })
      .catch(() => {
        setIsBackendConnected(false);
      });
  }, []);

  const handleStartAudit = async (options: AuditRequestOptions) => {
    setTargetUrl(options.url);
    setIsLoading(true);
    setErrorMessage(null);
    setView('running');

    try {
      const data = await auditApi.runAudit(options);
      setReport(data);
      setIsDemoMode(false);
      if (data.findings && data.findings.length > 0) {
        setSelectedFinding(data.findings[0]);
      } else {
        setSelectedFinding(null);
      }
      setView('results');
    } catch (err: any) {
      console.warn('Audit error:', err);
      // If server unreachable, provide clear message
      setErrorMessage(
        err instanceof AuditApiError
          ? err.message
          : 'Could not connect to backend server. Make sure the FastAPI backend is running on port 8000, or load a sample dataset.'
      );
      setView('landing');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadDemo = (type: 'ecommerce' | 'healthy') => {
    const demoReport = auditApi.getDemoReport(type);
    setReport(demoReport);
    setIsDemoMode(true);
    setTargetUrl(demoReport.site);
    if (demoReport.findings.length > 0) {
      setSelectedFinding(demoReport.findings[0]);
    } else {
      setSelectedFinding(null);
    }
    setView('results');
  };

  const handleNewAudit = () => {
    setView('landing');
    setErrorMessage(null);
  };

  const handleSelectFinding = (finding: Finding) => {
    setSelectedFinding(finding);
    setActiveTab('findings');
  };

  return (
    <div className="min-h-screen bg-workbench-950 text-workbench-200 flex flex-col font-sans">
      {/* Workbench Navigation Header */}
      <Header
        onNewAudit={handleNewAudit}
        onOpenReport={report ? () => setShowReportModal(true) : undefined}
        isBackendConnected={isBackendConnected}
        isDemoMode={isDemoMode}
        hasActiveReport={!!report}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {view === 'landing' && (
          <LandingView
            onStartAudit={handleStartAudit}
            onLoadDemo={handleLoadDemo}
            isLoading={isLoading}
            errorMessage={errorMessage}
          />
        )}

        {view === 'running' && <AuditProgressView targetUrl={targetUrl} />}

        {view === 'results' && report && (
          <div className="space-y-6">
            {/* Demo Mode Notice */}
            {isDemoMode && (
              <div className="p-3 bg-amber-950/40 border border-amber-800/80 rounded text-xs font-mono text-amber-300 flex items-center justify-between">
                <span>
                  <strong>DEMO DATA:</strong> You are viewing a pre-recorded forensic audit dataset. Click &quot;New Audit&quot; to test a live website.
                </span>
                <button
                  onClick={handleNewAudit}
                  className="px-2 py-0.5 rounded bg-amber-900 text-amber-200 hover:bg-amber-800 transition"
                >
                  Run Live Audit
                </button>
              </div>
            )}

            {/* Audit Summary Header Card */}
            <div className="workbench-panel p-5 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-workbench-800 pb-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2 text-xs font-mono">
                    <span className="text-workbench-400">Target Site:</span>
                    <span className="text-cyan-400 font-bold">{report.site}</span>
                    <a
                      href={report.site}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-workbench-500 hover:text-cyan-300 transition"
                      title="Open target"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-workbench-400 pt-0.5">
                    <span>Archetype: <strong className="text-workbench-200 uppercase">{report.site_archetype.replace(/_/g, ' ')}</strong></span>
                    <span>•</span>
                    <span>Audited: <strong className="text-workbench-200">{new Date(report.audited_at).toLocaleString()}</strong></span>
                    <span>•</span>
                    <span>Duration: <strong className="text-workbench-200">{report.crawl_duration_seconds}s</strong></span>
                    <span>•</span>
                    <span>Pages: <strong className="text-workbench-200">{report.pages_audited} audited</strong> ({report.pages_discovered} discovered)</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={() => setShowReportModal(true)}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono bg-workbench-800 hover:bg-workbench-700 text-workbench-200 border border-workbench-700 transition"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Export Markdown / JSON</span>
                  </button>
                  <button
                    onClick={() => handleStartAudit({ url: report.site })}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white transition font-medium"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Re-Run</span>
                  </button>
                </div>
              </div>

              {/* Summary Counts Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center font-mono text-xs">
                <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                  <span className="text-workbench-500 block text-[10px] uppercase">Total Findings</span>
                  <span className="text-lg font-bold text-workbench-100">{report.summary.total_findings}</span>
                </div>
                <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                  <span className="text-red-500 block text-[10px] uppercase">Critical</span>
                  <span className="text-lg font-bold text-red-400">{report.summary.critical}</span>
                </div>
                <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                  <span className="text-amber-500 block text-[10px] uppercase">High</span>
                  <span className="text-lg font-bold text-amber-400">{report.summary.high}</span>
                </div>
                <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                  <span className="text-yellow-500 block text-[10px] uppercase">Medium</span>
                  <span className="text-lg font-bold text-yellow-400">{report.summary.medium}</span>
                </div>
                <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                  <span className="text-blue-500 block text-[10px] uppercase">Low</span>
                  <span className="text-lg font-bold text-blue-400">{report.summary.low}</span>
                </div>
                <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Info</span>
                  <span className="text-lg font-bold text-slate-400">{report.summary.info}</span>
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex flex-wrap items-center gap-2 border-b border-workbench-800 pb-2 text-xs font-mono">
              <button
                onClick={() => setActiveTab('findings')}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-t border-b-2 transition ${
                  activeTab === 'findings'
                    ? 'border-cyan-500 bg-workbench-900 text-cyan-300 font-bold'
                    : 'border-transparent text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <FileSearch className="w-4 h-4" />
                <span>All Findings ({report.findings.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('discoverability')}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-t border-b-2 transition ${
                  activeTab === 'discoverability'
                    ? 'border-cyan-500 bg-workbench-900 text-cyan-300 font-bold'
                    : 'border-transparent text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <Bot className="w-4 h-4" />
                <span>AI Discoverability</span>
              </button>

              <button
                onClick={() => setActiveTab('engagement')}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-t border-b-2 transition ${
                  activeTab === 'engagement'
                    ? 'border-emerald-500 bg-workbench-900 text-emerald-300 font-bold'
                    : 'border-transparent text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <Compass className="w-4 h-4" />
                <span>On-Site Engagement</span>
              </button>

              <button
                onClick={() => setActiveTab('pages')}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-t border-b-2 transition ${
                  activeTab === 'pages'
                    ? 'border-cyan-500 bg-workbench-900 text-cyan-300 font-bold'
                    : 'border-transparent text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <Globe className="w-4 h-4" />
                <span>Audited Pages ({report.pages.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('recommendations')}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-t border-b-2 transition ${
                  activeTab === 'recommendations'
                    ? 'border-amber-500 bg-workbench-900 text-amber-300 font-bold'
                    : 'border-transparent text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <ListOrdered className="w-4 h-4" />
                <span>Remediation Queue</span>
              </button>

              <button
                onClick={() => setActiveTab('signal_map')}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-t border-b-2 transition ${
                  activeTab === 'signal_map'
                    ? 'border-cyan-500 bg-workbench-900 text-cyan-300 font-bold'
                    : 'border-transparent text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <Activity className="w-4 h-4" />
                <span>Signal Matrix</span>
              </button>
            </div>

            {/* Tab Views */}
            <div className="pt-2">
              {activeTab === 'findings' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* Left Column: Findings List (5 cols) */}
                  <div className="lg:col-span-5">
                    <FindingsList
                      findings={report.findings}
                      selectedFindingId={selectedFinding?.id || null}
                      onSelectFinding={setSelectedFinding}
                    />
                  </div>

                  {/* Right Column: Finding Causal Chain & Evidence Inspector (7 cols) */}
                  <div className="lg:col-span-7">
                    <FindingDetail finding={selectedFinding} />
                  </div>
                </div>
              )}

              {activeTab === 'discoverability' && (
                <DiscoverabilityView
                  findings={report.findings}
                  onSelectFinding={handleSelectFinding}
                />
              )}

              {activeTab === 'engagement' && (
                <EngagementView
                  findings={report.findings}
                  onSelectFinding={handleSelectFinding}
                />
              )}

              {activeTab === 'pages' && <PagesInspector pages={report.pages} />}

              {activeTab === 'recommendations' && (
                <RecommendationsView
                  findings={report.findings}
                  proactiveRecommendations={report.proactive_recommendations}
                  onSelectFinding={handleSelectFinding}
                />
              )}

              {activeTab === 'signal_map' && (
                <SignalMapView
                  findings={report.findings}
                  onSelectFinding={handleSelectFinding}
                />
              )}
            </div>
          </div>
        )}
      </main>

      {/* Raw Report Modal */}
      {showReportModal && report && (
        <RawReportModal
          report={report}
          onClose={() => setShowReportModal(false)}
        />
      )}

      {/* Forensic Workbench Footer */}
      <footer className="border-t border-workbench-800 bg-workbench-900/60 py-4 text-center text-xs font-mono text-workbench-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>WebVerity — AI Readiness & Website Intelligence Workbench • Adobe University Hackathon 2026</span>
          <span>Read-only evidence verification • RFC 9309 robots compliance</span>
        </div>
      </footer>
    </div>
  );
}
