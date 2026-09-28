import React, { useState } from 'react';
import { PageDto } from '../types/audit';
import { Globe, FileText, ExternalLink, Hash, Clock, CheckCircle2, AlertCircle, Code, Layers } from 'lucide-react';

interface PagesInspectorProps {
  pages: PageDto[];
}

export const PagesInspector: React.FC<PagesInspectorProps> = ({ pages }) => {
  const [selectedPageIndex, setSelectedPageIndex] = useState<number>(0);
  const selectedPage = pages[selectedPageIndex] || null;

  if (pages.length === 0) {
    return (
      <div className="workbench-panel p-8 text-center text-workbench-500 font-mono text-xs">
        <Globe className="w-8 h-8 text-workbench-700 mx-auto mb-2" />
        <span>No pages recorded in the crawl context.</span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Pages Table / List (Left / Top) */}
      <div className="lg:col-span-6 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-workbench-800">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-workbench-300">
            Crawled Pages ({pages.length})
          </div>
          <span className="text-[11px] font-mono text-workbench-500">
            Click row to inspect page telemetry
          </span>
        </div>

        <div className="space-y-1.5 overflow-y-auto max-h-[calc(100vh-250px)] pr-1 font-mono text-xs">
          {pages.map((page, idx) => {
            const isSelected = selectedPageIndex === idx;
            const isSuccess = page.status_code >= 200 && page.status_code < 300;
            return (
              <div
                key={idx}
                onClick={() => setSelectedPageIndex(idx)}
                className={`p-3 rounded border cursor-pointer transition text-left space-y-1.5 ${
                  isSelected
                    ? 'bg-workbench-800 border-cyan-500 ring-1 ring-cyan-500/30'
                    : 'bg-workbench-900/70 border-workbench-800 hover:bg-workbench-850 hover:border-workbench-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 truncate">
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                        isSuccess ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'
                      }`}
                    >
                      {page.status_code || 'ERR'}
                    </span>
                    <span className="text-workbench-200 font-bold truncate">
                      {page.url}
                    </span>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-workbench-950 text-cyan-400 border border-workbench-800 shrink-0 uppercase">
                    {page.page_archetype.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-workbench-400 pt-1 border-t border-workbench-800/60">
                  <span className="truncate max-w-[200px] text-workbench-300">
                    {page.title || 'Untitled Page'}
                  </span>
                  <div className="flex items-center space-x-3 text-workbench-500 shrink-0">
                    <span>{page.headings_count} Headings</span>
                    <span>{page.response_time_ms}ms</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Page Telemetry Inspector (Right / Bottom) */}
      <div className="lg:col-span-6">
        {selectedPage ? (
          <div className="workbench-panel p-5 space-y-5 overflow-y-auto max-h-[calc(100vh-250px)]">
            <div className="flex items-center justify-between border-b border-workbench-800 pb-3">
              <div className="space-y-1 truncate mr-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold text-cyan-400 uppercase">
                    {selectedPage.page_archetype.replace(/_/g, ' ')}
                  </span>
                  {selectedPage.is_primary_page && (
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-950 text-amber-400 border border-amber-800">
                      Primary
                    </span>
                  )}
                </div>
                <h4 className="text-xs font-mono font-bold text-workbench-100 truncate">
                  {selectedPage.url}
                </h4>
              </div>
              <a
                href={selectedPage.url}
                target="_blank"
                rel="noreferrer noopener"
                className="p-1.5 rounded bg-workbench-800 hover:bg-workbench-700 text-workbench-300 transition shrink-0"
                title="Open URL"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Core Metadata */}
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                <span className="text-workbench-500 block text-[10px] uppercase">Status Code</span>
                <span className="text-workbench-200 font-bold">{selectedPage.status_code}</span>
              </div>
              <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                <span className="text-workbench-500 block text-[10px] uppercase">Response Time</span>
                <span className="text-workbench-200 font-bold">{selectedPage.response_time_ms} ms</span>
              </div>
              <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                <span className="text-workbench-500 block text-[10px] uppercase">Internal Links</span>
                <span className="text-workbench-200 font-bold">{selectedPage.internal_links_count}</span>
              </div>
              <div className="p-2.5 bg-workbench-950 rounded border border-workbench-800">
                <span className="text-workbench-500 block text-[10px] uppercase">External Links</span>
                <span className="text-workbench-200 font-bold">{selectedPage.external_links_count}</span>
              </div>
            </div>

            {/* Title & Description */}
            <div className="space-y-2 text-xs">
              <div>
                <span className="font-mono text-workbench-400 text-[11px] block">Page Title:</span>
                <p className="p-2 bg-workbench-950 rounded border border-workbench-800 text-workbench-200 font-mono text-xs">
                  {selectedPage.title || '<No title tag>'}
                </p>
              </div>

              <div>
                <span className="font-mono text-workbench-400 text-[11px] block">Meta Description:</span>
                <p className="p-2 bg-workbench-950 rounded border border-workbench-800 text-workbench-300 text-xs">
                  {selectedPage.meta_description || '<No meta description provided>'}
                </p>
              </div>

              {selectedPage.canonical_url && (
                <div>
                  <span className="font-mono text-workbench-400 text-[11px] block">Canonical URL:</span>
                  <p className="p-2 bg-workbench-950 rounded border border-workbench-800 text-workbench-300 font-mono text-xs truncate">
                    {selectedPage.canonical_url}
                  </p>
                </div>
              )}
            </div>

            {/* Schema Types */}
            <div className="space-y-1.5">
              <span className="font-mono text-workbench-400 text-xs font-bold uppercase tracking-wider block">
                Detected Schema.org Types ({selectedPage.schema_types.length})
              </span>
              <div className="flex flex-wrap gap-1.5 font-mono text-xs">
                {selectedPage.schema_types.length > 0 ? (
                  selectedPage.schema_types.map((st, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 text-[11px]"
                    >
                      {st}
                    </span>
                  ))
                ) : (
                  <span className="text-workbench-600 text-xs italic">No JSON-LD structured data blocks detected.</span>
                )}
              </div>
            </div>

            {/* Heading Hierarchy Tree */}
            <div className="space-y-2">
              <span className="font-mono text-workbench-400 text-xs font-bold uppercase tracking-wider block">
                Heading Tree ({selectedPage.headings.length})
              </span>
              <div className="space-y-1 font-mono text-xs max-h-48 overflow-y-auto pr-1">
                {selectedPage.headings.length > 0 ? (
                  selectedPage.headings.map((h, i) => (
                    <div
                      key={i}
                      className="p-1.5 bg-workbench-950 rounded border border-workbench-850 flex items-center space-x-2"
                      style={{ marginLeft: `${Math.max(0, (h.level - 1) * 12)}px` }}
                    >
                      <span className="text-[10px] px-1 rounded bg-workbench-800 text-workbench-300 uppercase shrink-0">
                        {h.tag}
                      </span>
                      <span className="text-workbench-200 truncate">{h.text}</span>
                    </div>
                  ))
                ) : (
                  <span className="text-workbench-600 text-xs italic">No heading elements extracted.</span>
                )}
              </div>
            </div>

            {/* Extracted Facts */}
            {selectedPage.extracted_facts && Object.keys(selectedPage.extracted_facts).length > 0 && (
              <div className="space-y-1.5">
                <span className="font-mono text-workbench-400 text-xs font-bold uppercase tracking-wider block">
                  Extracted Facts & Attributes
                </span>
                <div className="forensic-code-block max-h-40">
                  {JSON.stringify(selectedPage.extracted_facts, null, 2)}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};
