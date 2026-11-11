import React, { memo } from 'react';
import { Handle, Position, NodeProps, Node } from '@xyflow/react';
import { FileCode2, Layers, Terminal, Sparkles } from 'lucide-react';
import { GraphNodeData } from '../types';

export type CustomNodeType = Node<GraphNodeData, 'customNode'>;

export const CustomNode = memo(({ data }: NodeProps<CustomNodeType>) => {
  const isPython = data.language === 'python' || data.label?.endsWith('.py') || data.file_path?.endsWith('.py');
  const isTS = data.language === 'typescript' || data.label?.endsWith('.ts') || data.label?.endsWith('.tsx') || data.file_path?.endsWith('.ts') || data.file_path?.endsWith('.tsx');

  const isSymbolNode = !!data.file_path && !!data.name;
  const fileName = data.file_path ? data.file_path.split('/').pop() : data.label?.split('/').pop();
  const isActive = !!data.isActive;

  return (
    <div
      className={`relative px-3.5 py-3 rounded-xl transition-all duration-300 min-w-[220px] max-w-[280px] cursor-pointer ${
        isActive
          ? 'bg-[#1c2333] border-2 border-emerald-400 shadow-[0_0_30px_rgba(52,211,153,0.55)] ring-4 ring-emerald-400/25 scale-105 z-30'
          : 'bg-[#161b22] border border-[#30363d] shadow-lg hover:border-[#58a6ff] hover:shadow-cyan-500/10'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className={`!w-2.5 !h-2.5 !border-2 !border-[#0d1117] ${
          isActive ? '!bg-emerald-400' : '!bg-[#58a6ff]'
        }`}
      />

      {/* Header: Name / Label & Active Badge */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 overflow-hidden">
          {isSymbolNode ? (
            <Terminal className={`w-4 h-4 shrink-0 ${isActive ? 'text-emerald-300' : 'text-emerald-400'}`} />
          ) : (
            <FileCode2 className={`w-4 h-4 shrink-0 ${isPython ? 'text-amber-400' : isTS ? 'text-sky-400' : 'text-gray-400'}`} />
          )}
          <span
            className={`text-xs font-semibold truncate ${
              isActive ? 'text-emerald-200' : 'text-gray-200'
            }`}
            title={data.name || data.label}
          >
            {data.name || fileName || 'node'}
          </span>
        </div>

        {isActive ? (
          <span className="flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse shrink-0">
            <Sparkles className="w-2.5 h-2.5" />
            ACTIVE
          </span>
        ) : (
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-[#21262d] text-gray-400 shrink-0">
            {data.kind || data.cluster || 'root'}
          </span>
        )}
      </div>

      {/* Containing File Tag if it's a Symbol */}
      {isSymbolNode && data.file_path && (
        <div
          className={`text-[10px] font-mono truncate px-1.5 py-0.5 rounded border mb-1.5 ${
            isActive
              ? 'text-emerald-300 bg-emerald-950/40 border-emerald-500/40 font-medium'
              : 'text-emerald-400/90 bg-[#0d1117] border-[#21262d]'
          }`}
          title={data.file_path}
        >
          📄 {data.file_path}
        </div>
      )}

      {/* Full relative path for File Nodes */}
      {!isSymbolNode && (
        <div
          className={`text-[11px] font-mono truncate ${
            isActive ? 'text-gray-300' : 'text-gray-400'
          }`}
          title={data.label}
        >
          {data.label || ''}
        </div>
      )}

      {/* Metrics for File Nodes */}
      {data.metrics && (
        <div className="flex items-center gap-2 mt-2 pt-1.5 border-t border-[#21262d] text-[10px] text-gray-400">
          <span className="flex items-center gap-1 text-sky-300">
            <Layers className="w-3 h-3" />
            {data.metrics.symbols} symbols
          </span>
          <span className="text-gray-500">
            {(data.metrics.size_bytes / 1024).toFixed(1)} KB
          </span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className={`!w-2.5 !h-2.5 !border-2 !border-[#0d1117] ${
          isActive ? '!bg-emerald-400' : '!bg-[#58a6ff]'
        }`}
      />
    </div>
  );
});

CustomNode.displayName = 'CustomNode';
