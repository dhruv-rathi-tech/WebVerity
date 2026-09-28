import React, { useState } from 'react';
import { AuditReport } from '../types/audit';
import { X, Copy, Check, Download, FileText, Code } from 'lucide-react';

interface RawReportModalProps {
  report: AuditReport;
  onClose: () => void;
}

export const RawReportModal: React.FC<RawReportModalProps> = ({ report, onClose }) => {
  const [tab, setTab] = useState<'markdown' | 'json'>('markdown');
  const [copied, setCopied] = useState(false);

  const markdownContent = report.markdown_report || '# No Markdown Available';
  const jsonContent = JSON.stringify(report, null, 2);

  const activeContent = tab === 'markdown' ? markdownContent : jsonContent;

  const handleCopy = () => {
    navigator.clipboard.writeText(activeContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const filename = `audit-report-${report.site.replace(/[^a-z0-9]/gi, '_')}.${
      tab === 'markdown' ? 'md' : 'json'
    }`;
    const blob = new Blob([activeContent], {
      type: tab === 'markdown' ? 'text/markdown' : 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6">
      <div className="workbench-panel w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl border-workbench-700">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-workbench-800">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-100">
              Audit Report Inspector
            </span>
            {/* Format Toggle */}
            <div className="flex rounded bg-workbench-950 p-0.5 border border-workbench-800 text-xs font-mono">
              <button
                onClick={() => setTab('markdown')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded transition ${
                  tab === 'markdown'
                    ? 'bg-workbench-800 text-cyan-300 font-bold'
                    : 'text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Markdown</span>
              </button>
              <button
                onClick={() => setTab('json')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded transition ${
                  tab === 'json'
                    ? 'bg-workbench-800 text-cyan-300 font-bold'
                    : 'text-workbench-400 hover:text-workbench-200'
                }`}
              >
                <Code className="w-3.5 h-3.5" />
                <span>JSON DTO</span>
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopy}
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-workbench-800 hover:bg-workbench-700 text-workbench-200 border border-workbench-700 transition"
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
            <button
              onClick={handleDownload}
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-workbench-800 hover:bg-workbench-700 text-workbench-200 border border-workbench-700 transition"
              title="Download file"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded text-workbench-400 hover:text-workbench-100 hover:bg-workbench-800 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-4 flex-1 overflow-y-auto">
          <pre className="forensic-code-block max-h-[60vh] text-xs font-mono select-text">
            {activeContent}
          </pre>
        </div>
      </div>
    </div>
  );
};
