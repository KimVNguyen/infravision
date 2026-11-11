import React, { useEffect, useRef, useState } from 'react';
import {
  X,
  Code2,
  Layers,
  Terminal,
  ArrowUpRight,
  ArrowDownLeft,
  ArrowLeft,
  ExternalLink,
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FileDetails } from '../types';

interface FileDrawerProps {
  file: FileDetails | null;
  onClose: () => void;
  onNavigateToFile: (fileId: string, highlightLine?: number) => void;
  onBack?: () => void;
  canGoBack?: boolean;
  highlightLine?: number;
}

function getLanguage(path: string, lang: string): string {
  if (path.endsWith('.tsx')) return 'tsx';
  if (path.endsWith('.ts')) return 'typescript';
  if (path.endsWith('.jsx')) return 'jsx';
  if (path.endsWith('.js')) return 'javascript';
  if (path.endsWith('.py')) return 'python';
  if (path.endsWith('.json')) return 'json';
  if (path.endsWith('.css')) return 'css';
  return lang || 'typescript';
}

export const FileDrawer: React.FC<FileDrawerProps> = ({
  file,
  onClose,
  onNavigateToFile,
  onBack,
  canGoBack = false,
  highlightLine,
}) => {
  const [activeTab, setActiveTab] = useState<'symbols' | 'deps' | 'code'>('symbols');
  const codeContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to highlighted line if code tab is active or when highlightLine changes
  useEffect(() => {
    if (highlightLine && highlightLine > 0) {
      setActiveTab('code');
      const timer = setTimeout(() => {
        const el = document.getElementById(`line-${highlightLine}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [highlightLine, file?.id]);

  if (!file) return null;

  const syntaxLang = getLanguage(file.relative_path, file.language);

  return (
    <div className="fixed inset-y-0 right-0 w-[650px] bg-[#161b22] border-l border-[#30363d] shadow-2xl z-50 flex flex-col transition-transform duration-300">
      {/* Header with Navigation and Back Button */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#30363d] bg-[#0d1117]">
        <div className="flex items-center gap-2.5 overflow-hidden">
          {canGoBack && onBack && (
            <button
              onClick={onBack}
              className="p-1 rounded bg-[#21262d] hover:bg-[#30363d] text-gray-300 hover:text-white transition"
              title="Go back to previous file"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}

          <Code2 className="w-5 h-5 text-sky-400 shrink-0" />
          <div className="overflow-hidden">
            <h3 className="text-sm font-semibold text-gray-200 truncate" title={file.relative_path}>
              {file.relative_path}
            </h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[11px] font-mono px-1.5 py-0.5 bg-[#21262d] text-sky-300 rounded">
                {file.language}
              </span>
              <span className="text-[11px] text-gray-500">
                {(file.size_bytes / 1024).toFixed(1)} KB
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#21262d] transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-[#30363d] bg-[#161b22] px-4 text-xs font-medium">
        <button
          onClick={() => setActiveTab('symbols')}
          className={`px-3 py-2.5 border-b-2 flex items-center gap-1.5 transition ${
            activeTab === 'symbols'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          Functions & Callers ({file.symbols.length})
        </button>
        <button
          onClick={() => setActiveTab('deps')}
          className={`px-3 py-2.5 border-b-2 flex items-center gap-1.5 transition ${
            activeTab === 'deps'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <ArrowRightLeftIcon className="w-3.5 h-3.5" />
          File Links ({file.incoming_files?.length || 0} in / {file.outgoing_files?.length || 0} out)
        </button>
        <button
          onClick={() => setActiveTab('code')}
          className={`px-3 py-2.5 border-b-2 flex items-center gap-1.5 transition ${
            activeTab === 'code'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          Source Code {highlightLine ? `(L${highlightLine})` : ''}
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === 'symbols' && (
          <div className="space-y-3">
            {file.symbols.length === 0 ? (
              <p className="text-xs text-gray-500 italic">No top-level functions or classes extracted.</p>
            ) : (
              file.symbols.map((sym) => (
                <div
                  key={sym.id}
                  className="p-3 rounded-lg bg-[#0d1117] border border-[#21262d] text-xs hover:border-[#30363d] transition space-y-2.5"
                >
                  {/* Symbol Title & Kind */}
                  <div className="flex items-center justify-between gap-2">
                    <button
                      onClick={() => {
                        setActiveTab('code');
                        setTimeout(() => {
                          const el = document.getElementById(`line-${sym.start_line}`);
                          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }, 120);
                      }}
                      className="font-mono font-semibold text-sky-300 text-sm hover:underline text-left flex items-center gap-1"
                      title="Jump to code definition"
                    >
                      {sym.name}
                      <ExternalLink className="w-3 h-3 text-sky-500 opacity-60" />
                    </button>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-[#21262d] text-gray-300 font-mono">
                      {sym.kind} (L{sym.start_line}-{sym.end_line})
                    </span>
                  </div>

                  {sym.signature && (
                    <div className="font-mono text-[11px] text-gray-400 truncate bg-[#161b22] px-2 py-1 rounded">
                      {sym.signature}
                    </div>
                  )}

                  {sym.docstring && (
                    <div className="text-[11px] text-gray-400 line-clamp-2 italic">
                      "{sym.docstring}"
                    </div>
                  )}

                  {/* Incoming Callers */}
                  <div className="pt-2 border-t border-[#21262d] space-y-1">
                    <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                      <ArrowDownLeft className="w-3.5 h-3.5" />
                      Called By ({sym.callers?.length || 0}):
                    </div>

                    {sym.callers && sym.callers.length > 0 ? (
                      <div className="space-y-1 pl-1">
                        {sym.callers.map((c, i) => (
                          <div
                            key={i}
                            onClick={() => {
                              if (c.caller_file_id) {
                                onNavigateToFile(c.caller_file_id, c.line);
                              }
                            }}
                            className={`flex items-center justify-between text-[11px] font-mono px-2.5 py-1.5 rounded border border-[#21262d] transition group ${
                              c.caller_file_id
                                ? 'bg-[#161b22] hover:bg-[#21262d] hover:border-emerald-500/50 cursor-pointer text-gray-200'
                                : 'bg-[#161b22] text-gray-400'
                            }`}
                            title={`Click to open ${c.caller_file} at line ${c.line}`}
                          >
                            <span className="truncate max-w-[260px] flex items-center gap-1">
                              📄 <span className="group-hover:text-emerald-300 font-medium">{c.caller_file}</span>
                            </span>
                            <span className="text-emerald-400 font-medium flex items-center gap-1 shrink-0">
                              {c.caller_symbol}() <span className="text-gray-500 text-[10px]">L{c.line}</span>
                              <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[11px] text-gray-500 italic pl-1">
                        No callers mapped inside indexed repo
                      </div>
                    )}
                  </div>

                  {/* Outgoing Calls */}
                  {sym.callees && sym.callees.length > 0 && (
                    <div className="pt-2 border-t border-[#21262d] space-y-1">
                      <div className="flex items-center gap-1 text-[11px] font-semibold text-amber-400">
                        <ArrowUpRight className="w-3.5 h-3.5" />
                        Calls ({sym.callees.length}):
                      </div>
                      <div className="space-y-1 pl-1">
                        {sym.callees.map((c, i) => (
                          <div
                            key={i}
                            onClick={() => {
                              if (c.callee_file_id) {
                                onNavigateToFile(c.callee_file_id, c.line);
                              }
                            }}
                            className={`flex items-center justify-between text-[11px] font-mono px-2.5 py-1.5 rounded border border-[#21262d] transition group ${
                              c.callee_file_id
                                ? 'bg-[#161b22] hover:bg-[#21262d] hover:border-amber-500/50 cursor-pointer text-gray-200'
                                : 'bg-[#161b22] text-gray-400'
                            }`}
                            title={`Click to open ${c.callee_file}`}
                          >
                            <span className="text-amber-300 font-medium flex items-center gap-1">
                              {c.callee_symbol}()
                              <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                            </span>
                            <span className="text-gray-400 text-[10px] truncate max-w-[240px]" title={c.callee_file}>
                              in {c.callee_file}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'deps' && (
          <div className="space-y-4">
            {/* Incoming File Dependencies */}
            <div className="p-3 bg-[#0d1117] border border-[#21262d] rounded-lg">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">
                <ArrowDownLeft className="w-4 h-4" />
                Files that Import this File ({file.incoming_files?.length || 0})
              </div>
              {!file.incoming_files || file.incoming_files.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No other files directly import this file.</p>
              ) : (
                <div className="space-y-1.5 max-h-56 overflow-y-auto">
                  {file.incoming_files.map((d) => (
                    <div
                      key={d.file_id}
                      onClick={() => onNavigateToFile(d.file_id)}
                      className="flex items-center justify-between px-2.5 py-2 rounded bg-[#161b22] hover:bg-[#21262d] border border-[#30363d] hover:border-emerald-500/60 cursor-pointer text-xs font-mono text-gray-300 transition group"
                      title="Click to jump to this file"
                    >
                      <span className="truncate max-w-[380px] group-hover:text-emerald-300 font-medium flex items-center gap-1.5">
                        📄 {d.relative_path}
                        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#0d1117] text-emerald-400 font-mono">
                        {d.import_count} imports
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Outgoing File Dependencies */}
            <div className="p-3 bg-[#0d1117] border border-[#21262d] rounded-lg">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-2">
                <ArrowUpRight className="w-4 h-4" />
                Files Imported by this File ({file.outgoing_files?.length || 0})
              </div>
              {!file.outgoing_files || file.outgoing_files.length === 0 ? (
                <p className="text-xs text-gray-500 italic">This file does not import any other local files.</p>
              ) : (
                <div className="space-y-1.5 max-h-56 overflow-y-auto">
                  {file.outgoing_files.map((d) => (
                    <div
                      key={d.file_id}
                      onClick={() => onNavigateToFile(d.file_id)}
                      className="flex items-center justify-between px-2.5 py-2 rounded bg-[#161b22] hover:bg-[#21262d] border border-[#30363d] hover:border-sky-500/60 cursor-pointer text-xs font-mono text-gray-300 transition group"
                      title="Click to jump to this file"
                    >
                      <span className="truncate max-w-[380px] group-hover:text-sky-300 font-medium flex items-center gap-1.5">
                        📄 {d.relative_path}
                        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#0d1117] text-sky-400 font-mono">
                        {d.import_count} imports
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'code' && (
          <div
            ref={codeContainerRef}
            className="rounded-lg bg-[#1e1e1e] border border-[#30363d] overflow-x-auto text-xs font-mono leading-relaxed max-h-[680px] overflow-y-auto shadow-inner"
          >
            <SyntaxHighlighter
              language={syntaxLang}
              style={vscDarkPlus}
              showLineNumbers
              wrapLines
              lineProps={(lineNumber) => {
                const isTarget = highlightLine === lineNumber;
                return {
                  id: `line-${lineNumber}`,
                  style: {
                    display: 'block',
                    backgroundColor: isTarget ? 'rgba(245, 158, 11, 0.22)' : undefined,
                    borderLeft: isTarget ? '3px solid #f59e0b' : '3px solid transparent',
                    paddingLeft: '6px',
                    transition: 'background-color 0.3s ease',
                  },
                };
              }}
              customStyle={{
                margin: 0,
                padding: '12px 4px',
                backgroundColor: '#1e1e1e',
                fontSize: '11.5px',
                lineHeight: '1.6',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              }}
              lineNumberStyle={{
                color: '#6e7681',
                paddingRight: '14px',
                minWidth: '36px',
                textAlign: 'right',
                userSelect: 'none',
              }}
            >
              {file.content || '// Empty file'}
            </SyntaxHighlighter>
          </div>
        )}
      </div>
    </div>
  );
};

function ArrowRightLeftIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  );
}
