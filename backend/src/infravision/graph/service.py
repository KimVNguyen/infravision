"""Graph query and assembly service for code visualizers."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infravision.db.models import CodeFile, FileDependency, GraphEdge, Symbol


class GraphService:
    """Provides structured graph datasets tailored for React Flow / Cytoscape."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_dependency_graph(self, repo_id: uuid.UUID) -> Dict[str, Any]:
        """Generate file-to-file and module-level dependency graph enriched with exact called symbols."""
        # Fetch all files in the repo
        stmt = (
            select(CodeFile)
            .where(CodeFile.repo_id == repo_id)
            .options(selectinload(CodeFile.symbols))
        )
        res = await self.session.execute(stmt)
        files = res.scalars().all()

        file_metrics = {
            f.id: {
                "symbols": len(f.symbols),
                "language": f.language,
                "size_bytes": f.size_bytes,
            }
            for f in files
        }

        # Query all file dependencies
        dep_stmt = (
            select(FileDependency)
            .where(FileDependency.repo_id == repo_id)
            .options(
                selectinload(FileDependency.source_file),
                selectinload(FileDependency.target_file),
            )
        )
        dep_res = await self.session.execute(dep_stmt)
        file_deps = dep_res.scalars().all()

        # Build adjacency for cycle detection and metric calculations
        file_adj: Dict[uuid.UUID, Dict[uuid.UUID, int]] = defaultdict(lambda: defaultdict(int))
        for dep in file_deps:
            if dep.source_file and dep.target_file:
                file_adj[dep.source_file_id][dep.target_file_id] += dep.import_count

        cycles = self._detect_cycles(file_adj)

        # Cross-file symbol calls: (src_file_id, tgt_file_id) -> set of target symbol names
        cross_calls_stmt = (
            select(GraphEdge)
            .join(Symbol, GraphEdge.source_symbol_id == Symbol.id)
            .join(CodeFile, Symbol.file_id == CodeFile.id)
            .where(CodeFile.repo_id == repo_id, GraphEdge.edge_type == "calls")
            .options(
                selectinload(GraphEdge.source_symbol).selectinload(Symbol.file),
                selectinload(GraphEdge.target_symbol).selectinload(Symbol.file),
            )
        )
        cross_res = await self.session.execute(cross_calls_stmt)
        cross_edges = cross_res.scalars().all()

        file_call_symbols: Dict[Tuple[uuid.UUID, uuid.UUID], Set[str]] = defaultdict(set)
        for ce in cross_edges:
            if ce.source_symbol and ce.target_symbol and ce.source_symbol.file and ce.target_symbol.file:
                s_fid = ce.source_symbol.file_id
                t_fid = ce.target_symbol.file_id
                if s_fid != t_fid:
                    file_call_symbols[(s_fid, t_fid)].add(ce.target_symbol.name)

        # Assemble React Flow nodes
        nodes = []
        for f in files:
            parts = f.relative_path.split("/")
            cluster = parts[0] if len(parts) > 1 else "root"
            nodes.append(
                {
                    "id": str(f.id),
                    "label": f.relative_path,
                    "cluster": cluster,
                    "language": f.language,
                    "metrics": file_metrics.get(f.id, {}),
                }
            )

        # Assemble React Flow edges with exact called symbols across files
        react_flow_edges = []
        for dep in file_deps:
            is_cycle = (dep.source_file_id, dep.target_file_id) in cycles
            called_syms = sorted(list(file_call_symbols.get((dep.source_file_id, dep.target_file_id), set())))
            
            if called_syms:
                label = f"{len(called_syms)} calls ({', '.join(called_syms[:2])}{'...' if len(called_syms) > 2 else ''})"
            else:
                label = f"{dep.import_count} imports" if dep.import_count > 1 else "imports"

            react_flow_edges.append(
                {
                    "id": f"e-{dep.source_file_id}-{dep.target_file_id}",
                    "source": str(dep.source_file_id),
                    "target": str(dep.target_file_id),
                    "label": label,
                    "weight": dep.import_count,
                    "is_cycle": is_cycle,
                    "called_symbols": called_syms,
                }
            )

        return {
            "summary": {
                "total_files": len(nodes),
                "total_dependencies": len(react_flow_edges),
                "connected_files_count": len(
                    set([d.source_file_id for d in file_deps] + [d.target_file_id for d in file_deps])
                ),
                "has_cycles": len(cycles) > 0,
                "cycle_count": len(cycles),
            },
            "nodes": nodes,
            "edges": react_flow_edges,
        }

    async def get_call_graph(
        self,
        repo_id: uuid.UUID,
        root_symbol_name: Optional[str] = None,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """Generate function/method call graph with explicit source file mapping on every node and edge."""
        stmt = (
            select(GraphEdge)
            .join(Symbol, GraphEdge.source_symbol_id == Symbol.id)
            .join(CodeFile, Symbol.file_id == CodeFile.id)
            .where(CodeFile.repo_id == repo_id, GraphEdge.edge_type == "calls")
            .options(
                selectinload(GraphEdge.source_symbol).selectinload(Symbol.file),
                selectinload(GraphEdge.target_symbol).selectinload(Symbol.file),
            )
        )
        res = await self.session.execute(stmt)
        edges = res.scalars().all()

        nodes_map = {}
        out_edges = []

        for edge in edges:
            src = edge.source_symbol
            tgt = edge.target_symbol
            if not src or not tgt:
                continue

            for s in (src, tgt):
                if s.id not in nodes_map:
                    file_rel = s.file.relative_path if s.file else ""
                    file_base = file_rel.split("/")[-1] if file_rel else ""
                    nodes_map[s.id] = {
                        "id": str(s.id),
                        "name": s.name,
                        "kind": s.kind,
                        "signature": s.signature,
                        "file_path": file_rel,
                        "file_id": str(s.file_id),
                        "label": f"{s.name} ({file_base})",
                        "cluster": file_rel.split("/")[0] if file_rel else "root",
                        "scope_path": s.scope_path,
                    }

            is_cross_file = src.file_id != tgt.file_id
            src_file_base = src.file.relative_path.split("/")[-1] if src.file else ""
            tgt_file_base = tgt.file.relative_path.split("/")[-1] if tgt.file else ""

            out_edges.append(
                {
                    "id": str(edge.id),
                    "source": str(src.id),
                    "target": str(tgt.id),
                    "type": "calls",
                    "is_cross_file": is_cross_file,
                    "label": f"calls from {src_file_base}" if is_cross_file else "calls",
                    "source_file": src.file.relative_path if src.file else "",
                    "target_file": tgt.file.relative_path if tgt.file else "",
                }
            )

        return {
            "summary": {
                "total_call_nodes": len(nodes_map),
                "total_call_edges": len(out_edges),
            },
            "nodes": list(nodes_map.values()),
            "edges": out_edges,
        }

    async def get_hierarchy_graph(self, repo_id: uuid.UUID) -> Dict[str, Any]:
        """Generate class inheritance and interface implementation hierarchy."""
        stmt = (
            select(GraphEdge)
            .join(Symbol, GraphEdge.source_symbol_id == Symbol.id)
            .join(CodeFile, Symbol.file_id == CodeFile.id)
            .where(
                CodeFile.repo_id == repo_id,
                GraphEdge.edge_type.in_(["extends", "implements"]),
            )
            .options(
                selectinload(GraphEdge.source_symbol).selectinload(Symbol.file),
                selectinload(GraphEdge.target_symbol).selectinload(Symbol.file),
            )
        )
        res = await self.session.execute(stmt)
        edges = res.scalars().all()

        nodes_map = {}
        out_edges = []
        for edge in edges:
            src = edge.source_symbol
            tgt = edge.target_symbol
            if not src or not tgt:
                continue

            for s in (src, tgt):
                if s.id not in nodes_map:
                    file_rel = s.file.relative_path if s.file else ""
                    nodes_map[s.id] = {
                        "id": str(s.id),
                        "name": s.name,
                        "kind": s.kind,
                        "file_path": file_rel,
                        "label": f"{s.name} ({file_rel.split('/')[-1]})" if file_rel else s.name,
                        "scope_path": s.scope_path,
                    }

            out_edges.append(
                {
                    "id": str(edge.id),
                    "source": str(src.id),
                    "target": str(tgt.id),
                    "relation": edge.edge_type,
                    "label": edge.edge_type,
                }
            )

        return {"nodes": list(nodes_map.values()), "edges": out_edges}

    async def get_treemap(self, repo_id: uuid.UUID) -> Dict[str, Any]:
        """Generate hierarchical folder/file tree with size and symbol count."""
        stmt = (
            select(CodeFile)
            .where(CodeFile.repo_id == repo_id)
            .options(selectinload(CodeFile.symbols))
        )
        res = await self.session.execute(stmt)
        files = res.scalars().all()

        root_tree: Dict[str, Any] = {"name": "root", "children": {}}

        for f in files:
            parts = f.relative_path.split("/")
            current = root_tree
            for part in parts[:-1]:
                if part not in current["children"]:
                    current["children"][part] = {"name": part, "children": {}}
                current = current["children"][part]

            file_leaf = parts[-1]
            current["children"][file_leaf] = {
                "name": file_leaf,
                "file_id": str(f.id),
                "language": f.language,
                "size_bytes": f.size_bytes,
                "symbols_count": len(f.symbols),
            }

        def _format_tree(node: Dict[str, Any]) -> Dict[str, Any]:
            if "children" in node:
                formatted_children = [
                    _format_tree(child) for child in node["children"].values()
                ]
                return {"name": node["name"], "children": formatted_children}
            return node

        return _format_tree(root_tree)

    def _detect_cycles(
        self, adj: Dict[uuid.UUID, Dict[uuid.UUID, int]]
    ) -> Set[Tuple[uuid.UUID, uuid.UUID]]:
        """Cycle detection via DFS."""
        visited: Set[uuid.UUID] = set()
        recursion_stack: Set[uuid.UUID] = set()
        cycle_edges: Set[Tuple[uuid.UUID, uuid.UUID]] = set()

        def dfs(node: uuid.UUID) -> None:
            visited.add(node)
            recursion_stack.add(node)

            for neighbor in adj.get(node, {}):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in recursion_stack:
                    cycle_edges.add((node, neighbor))

            recursion_stack.remove(node)

        for n in list(adj.keys()):
            if n not in visited:
                dfs(n)

        return cycle_edges
