"""Orchestrates scanning, Tree-sitter parsing, and storing graph metadata."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import os
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from infravision.db.models import CodeFile, FileDependency, GraphEdge, Repository, Symbol
from infravision.indexer.scanner import DiscoveredFile, RepositoryScanner
from infravision.parser.base import BaseLanguageParser, ParseResult, ParsedImport
from infravision.parser.python import PythonParser
from infravision.parser.typescript import TypeScriptParser


class IndexingPipeline:
    """Indexes a repository, extracting symbols, imports, and call edges into PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.parsers: Dict[str, BaseLanguageParser] = {
            "python": PythonParser(),
            "typescript": TypeScriptParser(is_tsx=True),
            "javascript": TypeScriptParser(is_tsx=True),
        }

    async def get_or_create_repo(self, root_path: str, name: Optional[str] = None) -> Repository:
        resolved_path = str(Path(root_path).resolve())
        stmt = select(Repository).where(Repository.root_path == resolved_path)
        res = await self.session.execute(stmt)
        repo = res.scalar_one_or_none()

        if not repo:
            repo_name = name or Path(resolved_path).name
            repo = Repository(name=repo_name, root_path=resolved_path)
            self.session.add(repo)
            await self.session.flush()
        return repo

    async def index_repository(self, repo_id: uuid.UUID) -> dict:
        """Run full scan and AST extraction for a registered repository."""
        stmt = select(Repository).where(Repository.id == repo_id)
        res = await self.session.execute(stmt)
        repo = res.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        repo_root = Path(repo.root_path).resolve()
        scanner = RepositoryScanner(repo_root)
        files = list(scanner.scan_files())

        # Clean existing file dependencies and symbols for fresh re-index
        await self.session.execute(
            delete(FileDependency).where(FileDependency.repo_id == repo.id)
        )

        indexed_files = 0
        indexed_symbols = 0
        indexed_edges = 0

        # In-memory lookup tables for resolution
        # rel_path -> CodeFile
        file_by_rel_path: Dict[str, CodeFile] = {}
        # (file_id, symbol_name) -> Symbol
        symbol_by_file_and_name: Dict[Tuple[uuid.UUID, str], Symbol] = {}
        # symbol_name -> list of (file_id, Symbol)
        symbol_global_index: Dict[str, List[Tuple[uuid.UUID, Symbol]]] = {}
        
        # Stored parsed data for phase 2 linkage: file_id -> (discovered_file, parse_result)
        parsed_cache: Dict[uuid.UUID, Tuple[DiscoveredFile, ParseResult]] = {}

        # -------------------------------------------------------------
        # Phase 1: Parse AST, extract and persist symbols & files
        # -------------------------------------------------------------
        for discovered in files:
            parser = self.parsers.get(discovered.language)
            if not parser:
                continue

            try:
                code_content = discovered.absolute_path.read_text(
                    encoding="utf-8", errors="replace"
                )
            except Exception:
                continue

            # Check if file exists in DB
            file_stmt = select(CodeFile).where(
                CodeFile.repo_id == repo.id,
                CodeFile.relative_path == discovered.relative_path,
            )
            file_res = await self.session.execute(file_stmt)
            code_file = file_res.scalar_one_or_none()

            if not code_file:
                code_file = CodeFile(
                    repo_id=repo.id,
                    relative_path=discovered.relative_path,
                    language=discovered.language,
                    file_hash=discovered.file_hash,
                    size_bytes=discovered.size_bytes,
                )
                self.session.add(code_file)
                await self.session.flush()
            else:
                code_file.file_hash = discovered.file_hash
                code_file.size_bytes = discovered.size_bytes
                code_file.language = discovered.language
                await self.session.execute(
                    delete(Symbol).where(Symbol.file_id == code_file.id)
                )

            file_by_rel_path[discovered.relative_path] = code_file

            # Parse AST
            parse_result: ParseResult = parser.parse_source(
                code_content, file_path=discovered.relative_path
            )
            parsed_cache[code_file.id] = (discovered, parse_result)

            # Store symbols
            for sym in parse_result.symbols:
                db_symbol = Symbol(
                    file_id=code_file.id,
                    name=sym.name,
                    kind=sym.kind,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    signature=sym.signature,
                    docstring=sym.docstring,
                    scope_path=sym.scope_path,
                )
                self.session.add(db_symbol)
                await self.session.flush()

                key = (code_file.id, sym.name)
                symbol_by_file_and_name[key] = db_symbol
                if sym.name not in symbol_global_index:
                    symbol_global_index[sym.name] = []
                symbol_global_index[sym.name].append((code_file.id, db_symbol))
                indexed_symbols += 1

            indexed_files += 1

        # Build path lookup index for fast module resolution
        # Keys: relative path with/without extension, and directory index
        path_resolver_map: Dict[str, CodeFile] = {}
        for rel_path, c_file in file_by_rel_path.items():
            path_resolver_map[rel_path] = c_file
            stem = rel_path.rsplit(".", 1)[0]
            path_resolver_map[stem] = c_file
            # If path ends with /index.ts or /index.js, also map directory itself
            if "/index." in rel_path:
                dir_key = rel_path.split("/index.")[0]
                path_resolver_map[dir_key] = c_file
            if rel_path.endswith("/__init__.py"):
                dir_key = rel_path[:-12]
                path_resolver_map[dir_key] = c_file

        # -------------------------------------------------------------
        # Phase 2: Resolve Imports -> FileDependencies
        # -------------------------------------------------------------
        # Track resolved file edges: (src_file_id, tgt_file_id) -> count
        file_deps_counts: Dict[Tuple[uuid.UUID, uuid.UUID], int] = {}
        # Track imported symbols per file: (src_file_id, symbol_name) -> target_file_id
        file_imported_symbols: Dict[Tuple[uuid.UUID, str], uuid.UUID] = {}

        for file_id, (disc, parse_result) in parsed_cache.items():
            current_file_dir = disc.absolute_path.parent

            for imp in parse_result.imports:
                target_file = self._resolve_import_to_file(
                    specifier=imp.module_specifier,
                    current_file_dir=current_file_dir,
                    repo_root=repo_root,
                    resolver_map=path_resolver_map,
                    language=disc.language,
                )

                if target_file and target_file.id != file_id:
                    edge_key = (file_id, target_file.id)
                    file_deps_counts[edge_key] = file_deps_counts.get(edge_key, 0) + 1

                    for sym_name in imp.imported_symbols:
                        file_imported_symbols[(file_id, sym_name)] = target_file.id

        # Persist FileDependency records
        for (src_id, tgt_id), count in file_deps_counts.items():
            file_dep = FileDependency(
                repo_id=repo.id,
                source_file_id=src_id,
                target_file_id=tgt_id,
                raw_import_path="import",
                import_count=count,
            )
            self.session.add(file_dep)

        # -------------------------------------------------------------
        # Phase 3: Resolve Call & Inheritance Edges
        # -------------------------------------------------------------
        for file_id, (disc, parse_result) in parsed_cache.items():
            for edge in parse_result.edges:
                source_sym = symbol_by_file_and_name.get((file_id, edge.source_symbol))
                if not source_sym:
                    continue

                target_sym: Optional[Symbol] = None

                # 1. Try local symbol in the same file
                target_sym = symbol_by_file_and_name.get((file_id, edge.target_symbol))

                # 2. Try explicitly imported symbol from another file
                if not target_sym and (file_id, edge.target_symbol) in file_imported_symbols:
                    tgt_file_id = file_imported_symbols[(file_id, edge.target_symbol)]
                    target_sym = symbol_by_file_and_name.get((tgt_file_id, edge.target_symbol))

                # 3. Fallback to global symbol match
                if not target_sym and edge.target_symbol in symbol_global_index:
                    matches = symbol_global_index[edge.target_symbol]
                    if len(matches) == 1:
                        target_sym = matches[0][1]

                if target_sym and source_sym.id != target_sym.id:
                    graph_edge = GraphEdge(
                        source_symbol_id=source_sym.id,
                        target_symbol_id=target_sym.id,
                        edge_type=edge.edge_type,
                    )
                    self.session.add(graph_edge)
                    indexed_edges += 1

        await self.session.commit()
        return {
            "files": indexed_files,
            "symbols": indexed_symbols,
            "edges": indexed_edges,
            "file_dependencies": len(file_deps_counts),
        }

    def _resolve_import_to_file(
        self,
        specifier: str,
        current_file_dir: Path,
        repo_root: Path,
        resolver_map: Dict[str, CodeFile],
        language: str,
    ) -> Optional[CodeFile]:
        """Resolves module specifier (relative, alias, or package) to a CodeFile."""
        candidates: List[str] = []

        if language == "python":
            if specifier.startswith("."):
                # Python relative import: .foo, ..bar.baz
                num_dots = len(specifier) - len(specifier.lstrip("."))
                subpath = specifier[num_dots:].replace(".", "/")
                target_dir = current_file_dir
                for _ in range(num_dots - 1):
                    target_dir = target_dir.parent
                resolved_path = (target_dir / subpath).resolve()
                try:
                    rel = resolved_path.relative_to(repo_root).as_posix()
                    candidates.append(rel)
                except ValueError:
                    pass
            else:
                # Python absolute import: e.g. infravision.db.models
                rel_py = specifier.replace(".", "/")
                candidates.append(rel_py)
                candidates.append("src/" + rel_py)
                candidates.append("backend/src/" + rel_py)
                candidates.append("backend/" + rel_py)

                # Try resolving relative to current file directory
                try:
                    local_cand = (current_file_dir / rel_py).resolve().relative_to(repo_root).as_posix()
                    candidates.append(local_cand)
                except ValueError:
                    pass

                # Check suffix matching against indexed keys in resolver_map:
                # E.g. backend/src/infravision/db/models matches infravision/db/models
                target_suffix = "/" + rel_py
                suffix_matches: List[Tuple[int, CodeFile]] = []
                for k, c_file in resolver_map.items():
                    if k.endswith(target_suffix) or k == rel_py:
                        try:
                            rel_curr = current_file_dir.relative_to(repo_root).as_posix()
                            common_len = len(os.path.commonpath([k, rel_curr]))
                        except Exception:
                            common_len = 0
                        suffix_matches.append((common_len, c_file))

                if suffix_matches:
                    suffix_matches.sort(key=lambda x: x[0], reverse=True)
                    return suffix_matches[0][1]

        else:
            # TypeScript / JavaScript / etc.
            if specifier.startswith("."):
                # Relative import: ./foo or ../bar/baz
                resolved_path = (current_file_dir / specifier).resolve()
                try:
                    rel = resolved_path.relative_to(repo_root).as_posix()
                    candidates.append(rel)
                except ValueError:
                    return None
            elif specifier.startswith("@/"):
                # Path alias commonly used in TS/React projects (@/ -> src/)
                rel_from_src = "src/" + specifier[2:]
                candidates.append(rel_from_src)
                candidates.append(specifier[2:])
            else:
                # Package or root-relative in TS
                candidates.append(specifier)
                candidates.append("src/" + specifier)
                target_suffix = "/" + specifier
                for k, c_file in resolver_map.items():
                    if k.endswith(target_suffix) or k == specifier:
                        return c_file

        # Check candidate variations against indexed files
        for cand in candidates:
            for ext in ("", ".py", "/__init__.py", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"):
                key = cand + ext
                if key in resolver_map:
                    return resolver_map[key]
        return None
