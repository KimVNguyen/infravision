import React, { useEffect, useState } from 'react';
import {
  Network,
  GitFork,
  Boxes,
  Plus,
  RefreshCw,
  AlertTriangle,
  FolderTree,
  ArrowRightLeft,
} from 'lucide-react';
import {
  fetchRepositories,
  indexRepository,
  fetchDependencyGraph,
  fetchCallGraph,
  fetchHierarchyGraph,
  fetchFileDetails,
} from './api';
import { FileDetails, GraphResponse, Repository } from './types';
import { GraphCanvas } from './components/GraphCanvas';
import { FileDrawer } from './components/FileDrawer';

type ViewMode = 'dependencies' | 'calls' | 'hierarchy';

export function App() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('');
  const [viewMode, setViewMode] = useState<ViewMode>('dependencies');
  const [direction, setDirection] = useState<'LR' | 'TB'>('LR');
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileDetails | null>(null);
  const [fileHistory, setFileHistory] = useState<string[]>([]);
  const [highlightLine, setHighlightLine] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(false);
  const [newRepoPath, setNewRepoPath] = useState<string>('');
  const [showIndexModal, setShowIndexModal] = useState<boolean>(false);

  // Load repositories on initial mount
  const loadRepos = async () => {
    try {
      const data = await fetchRepositories();
      setRepos(data);
      if (data.length > 0 && !selectedRepoId) {
        setSelectedRepoId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load repositories', err);
    }
  };

  useEffect(() => {
    loadRepos();
  }, []);

  // Fetch graph whenever selected repo or view mode changes
  useEffect(() => {
    if (!selectedRepoId) return;

    const loadGraph = async () => {
      setLoading(true);
      try {
        let res: GraphResponse;
        if (viewMode === 'dependencies') {
          res = await fetchDependencyGraph(selectedRepoId);
        } else if (viewMode === 'calls') {
          res = await fetchCallGraph(selectedRepoId);
        } else {
          res = await fetchHierarchyGraph(selectedRepoId);
        }
        setGraphData(res);
      } catch (err) {
        console.error('Failed to fetch graph data', err);
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
  }, [selectedRepoId, viewMode]);

  // Handle clicking a node directly from canvas
  const handleSelectNode = async (nodeId: string) => {
    if (!selectedRepoId) return;
    try {
      const fileData = await fetchFileDetails(selectedRepoId, nodeId);
      setSelectedFile(fileData);
      setFileHistory([]);
      setHighlightLine(undefined);
    } catch (err) {
      console.log('Selected node is not directly a file ID', nodeId);
    }
  };

  // Handle clicking a caller, callee, or file link inside the drawer
  const handleNavigateToFile = async (fileId: string, line?: number) => {
    if (!selectedRepoId) return;
    try {
      const fileData = await fetchFileDetails(selectedRepoId, fileId);
      if (selectedFile) {
        setFileHistory((prev) => [...prev, selectedFile.id]);
      }
      setSelectedFile(fileData);
      setHighlightLine(line);
    } catch (err) {
      console.error('Failed to navigate to file', fileId, err);
    }
  };

  // Handle clicking Back button in drawer
  const handleBack = async () => {
    if (fileHistory.length === 0 || !selectedRepoId) return;
    const prevId = fileHistory[fileHistory.length - 1];
    setFileHistory((prev) => prev.slice(0, -1));
    try {
      const fileData = await fetchFileDetails(selectedRepoId, prevId);
      setSelectedFile(fileData);
      setHighlightLine(undefined);
    } catch (err) {
      console.error('Failed to go back to file', prevId, err);
    }
  };

  const handleIndexSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoPath.trim()) return;

    setLoading(true);
    try {
      const res = await indexRepository(newRepoPath.trim());
      await loadRepos();
      setSelectedRepoId(res.repo_id);
      setShowIndexModal(false);
      setNewRepoPath('');
    } catch (err: any) {
      alert(`Indexing failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0d1117] text-gray-200">
      {/* Top Navbar */}
      <header className="h-14 border-b border-[#30363d] bg-[#161b22] px-4 flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center">
              <Network className="w-5 h-5 text-sky-400" />
            </div>
            <span className="font-bold text-sm tracking-wide text-white">
              INFRAVISION
            </span>
          </div>

          <div className="h-5 w-px bg-[#30363d]" />

          {/* Repo Selector */}
          <div className="flex items-center gap-2">
            <select
              value={selectedRepoId}
              onChange={(e) => setSelectedRepoId(e.target.value)}
              className="bg-[#0d1117] border border-[#30363d] text-xs font-mono rounded-lg px-3 py-1.5 focus:outline-none focus:border-sky-500 text-gray-200"
            >
              {repos.length === 0 && <option value="">No codebases indexed</option>}
              {repos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.root_path.split('/').slice(-2).join('/')})
                </option>
              ))}
            </select>

            <button
              onClick={() => setShowIndexModal(true)}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-sky-600 hover:bg-sky-500 text-white transition shadow"
            >
              <Plus className="w-3.5 h-3.5" />
              Index Codebase
            </button>
          </div>
        </div>

        {/* View Mode & Controls */}
        <div className="flex items-center gap-3">
          {graphData?.summary && (
            <div className="flex items-center gap-2 text-xs font-mono mr-2">
              <span className="px-2 py-1 rounded bg-[#0d1117] border border-[#30363d] text-gray-300">
                {graphData.summary.total_files} files
              </span>
              <span className="px-2 py-1 rounded bg-[#0d1117] border border-[#30363d] text-gray-300">
                {graphData.summary.total_dependencies} links
              </span>
              {graphData.summary.has_cycles && (
                <span className="flex items-center gap-1 px-2 py-1 rounded bg-red-950/60 border border-red-800 text-red-400">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  {graphData.summary.cycle_count} cycles
                </span>
              )}
            </div>
          )}

          {/* Switcher: Dependencies / Calls / Hierarchy */}
          <div className="flex rounded-lg bg-[#0d1117] border border-[#30363d] p-0.5">
            <button
              onClick={() => setViewMode('dependencies')}
              className={`flex items-center gap-1 px-3 py-1 text-xs rounded-md font-medium transition ${
                viewMode === 'dependencies'
                  ? 'bg-[#21262d] text-sky-400 shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <FolderTree className="w-3.5 h-3.5" />
              Architecture
            </button>
            <button
              onClick={() => setViewMode('calls')}
              className={`flex items-center gap-1 px-3 py-1 text-xs rounded-md font-medium transition ${
                viewMode === 'calls'
                  ? 'bg-[#21262d] text-sky-400 shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <GitFork className="w-3.5 h-3.5" />
              Call Flow
            </button>
            <button
              onClick={() => setViewMode('hierarchy')}
              className={`flex items-center gap-1 px-3 py-1 text-xs rounded-md font-medium transition ${
                viewMode === 'hierarchy'
                  ? 'bg-[#21262d] text-sky-400 shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Boxes className="w-3.5 h-3.5" />
              Hierarchy
            </button>
          </div>

          {/* Direction toggle */}
          <button
            onClick={() => setDirection((d) => (d === 'LR' ? 'TB' : 'LR'))}
            className="p-1.5 rounded-lg border border-[#30363d] bg-[#0d1117] text-gray-400 hover:text-white transition"
            title={`Switch to ${direction === 'LR' ? 'Top-to-Bottom' : 'Left-to-Right'} Layout`}
          >
            <ArrowRightLeft className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Canvas Area */}
      <main className="flex-1 relative overflow-hidden">
        {loading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0d1117]/80 backdrop-blur-sm z-20">
            <RefreshCw className="w-8 h-8 text-sky-400 animate-spin mb-3" />
            <p className="text-sm font-mono text-gray-400">Analyzing AST & computing layout...</p>
          </div>
        ) : null}

        {repos.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <Network className="w-16 h-16 text-gray-600 mb-4" />
            <h2 className="text-lg font-semibold text-gray-200 mb-2">No Codebases Indexed Yet</h2>
            <p className="text-xs text-gray-400 max-w-md mb-4">
              Infravision indexes Python and TypeScript/Node.js source code, mapping module dependencies, call graphs, and type hierarchies.
            </p>
            <button
              onClick={() => setShowIndexModal(true)}
              className="px-4 py-2 text-xs font-medium rounded-lg bg-sky-600 hover:bg-sky-500 text-white transition"
            >
              Index a Codebase
            </button>
          </div>
        ) : (
          <GraphCanvas
            graphData={graphData}
            onSelectNode={handleSelectNode}
            direction={direction}
            activeNodeId={selectedFile?.id || null}
          />
        )}

        {/* Slide-over code & symbol drawer */}
        <FileDrawer
          file={selectedFile}
          onClose={() => {
            setSelectedFile(null);
            setFileHistory([]);
            setHighlightLine(undefined);
          }}
          onNavigateToFile={handleNavigateToFile}
          onBack={handleBack}
          canGoBack={fileHistory.length > 0}
          highlightLine={highlightLine}
        />
      </main>

      {/* Index Modal */}
      {showIndexModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-white mb-2">Index Codebase</h3>
            <p className="text-xs text-gray-400 mb-3">
              Enter directory path to scan, or pick a mounted shortcut below:
            </p>

            <div className="flex flex-wrap gap-1.5 mb-4">
              <button
                type="button"
                onClick={() => setNewRepoPath('/storybot-ui')}
                className="px-2 py-1 text-[11px] font-mono rounded bg-[#21262d] border border-[#30363d] text-sky-300 hover:border-sky-500 hover:bg-[#30363d] transition"
              >
                /storybot-ui
              </button>
              <button
                type="button"
                onClick={() => setNewRepoPath('/workspace/infravision/backend')}
                className="px-2 py-1 text-[11px] font-mono rounded bg-[#21262d] border border-[#30363d] text-amber-300 hover:border-amber-500 hover:bg-[#30363d] transition"
              >
                /workspace/infravision/backend
              </button>
              <button
                type="button"
                onClick={() => setNewRepoPath('/workspace/infravision/frontend')}
                className="px-2 py-1 text-[11px] font-mono rounded bg-[#21262d] border border-[#30363d] text-emerald-300 hover:border-emerald-500 hover:bg-[#30363d] transition"
              >
                /workspace/infravision/frontend
              </button>
            </div>

            <form onSubmit={handleIndexSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">
                  Directory Path
                </label>
                <input
                  type="text"
                  required
                  placeholder="/workspace/infravision/backend"
                  value={newRepoPath}
                  onChange={(e) => setNewRepoPath(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-[#0d1117] border border-[#30363d] rounded-lg text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowIndexModal(false)}
                  className="px-3 py-1.5 text-xs rounded-lg text-gray-400 hover:bg-[#21262d] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 text-xs font-medium rounded-lg bg-sky-600 hover:bg-sky-500 text-white transition"
                >
                  {loading ? 'Indexing...' : 'Start Indexing'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
