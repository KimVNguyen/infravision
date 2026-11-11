export interface Repository {
  id: string;
  name: string;
  root_path: string;
  last_indexed_at: string | null;
}

export interface GraphNodeData extends Record<string, unknown> {
  id: string;
  label: string;
  cluster: string;
  language?: string;
  isActive?: boolean;
  metrics?: {
    symbols: number;
    language: string;
    size_bytes: number;
  };
  name?: string;
  kind?: string;
  signature?: string;
  file_path?: string;
  file_id?: string;
  scope_path?: string;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  label?: string;
  weight?: number;
  is_cycle?: boolean;
  type?: string;
  called_symbols?: string[];
  is_cross_file?: boolean;
  source_file?: string;
  target_file?: string;
}

export interface GraphResponse {
  summary?: {
    total_files?: number;
    total_dependencies?: number;
    connected_files_count?: number;
    total_call_nodes?: number;
    total_call_edges?: number;
    has_cycles?: boolean;
    cycle_count?: number;
  };
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}

export interface SymbolCaller {
  caller_symbol: string;
  caller_file: string;
  caller_file_id?: string;
  caller_symbol_id?: string;
  caller_kind: string;
  line: number;
}

export interface SymbolCallee {
  callee_symbol: string;
  callee_file: string;
  callee_file_id?: string;
  callee_symbol_id?: string;
  callee_kind: string;
  line: number;
}

export interface SymbolInfo {
  id: string;
  name: string;
  kind: string;
  start_line: number;
  end_line: number;
  signature: string | null;
  docstring: string | null;
  callers: SymbolCaller[];
  callees: SymbolCallee[];
}

export interface FileDependencyRef {
  file_id: string;
  relative_path: string;
  import_count: number;
}

export interface FileDetails {
  id: string;
  relative_path: string;
  language: string;
  size_bytes: number;
  content: string;
  incoming_files: FileDependencyRef[];
  outgoing_files: FileDependencyRef[];
  symbols: SymbolInfo[];
}
