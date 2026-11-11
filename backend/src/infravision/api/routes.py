"""FastAPI route handlers for repositories, graphs, and files."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infravision.db.models import CodeFile, FileDependency, GraphEdge, Repository, Symbol
from infravision.db.session import get_db_session
from infravision.graph.service import GraphService
from infravision.indexer.pipeline import IndexingPipeline

router = APIRouter(prefix="/api")


class RepoCreateRequest(BaseModel):
    path: str
    name: Optional[str] = None


class RepoResponse(BaseModel):
    id: str
    name: str
    root_path: str
    last_indexed_at: Optional[str]


@router.get("/repos", response_model=List[RepoResponse])
async def list_repositories(
    session: AsyncSession = Depends(get_db_session),
) -> List[RepoResponse]:
    stmt = select(Repository).order_by(Repository.created_at.desc())
    res = await session.execute(stmt)
    repos = res.scalars().all()
    return [
        RepoResponse(
            id=str(r.id),
            name=r.name,
            root_path=r.root_path,
            last_indexed_at=r.last_indexed_at.isoformat()
            if r.last_indexed_at
            else None,
        )
        for r in repos
    ]


@router.post("/repos", response_model=Dict[str, Any])
async def index_repository(
    req: RepoCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    path = Path(req.path).resolve()
    if not path.exists():
        raise HTTPException(
            status_code=400, detail=f"Directory not found: {req.path}"
        )

    pipeline = IndexingPipeline(session)
    repo = await pipeline.get_or_create_repo(str(path), req.name)
    stats = await pipeline.index_repository(repo.id)

    return {
        "repo_id": str(repo.id),
        "name": repo.name,
        "root_path": repo.root_path,
        "indexed_stats": stats,
    }


@router.get("/repos/{repo_id}/graph/dependencies")
async def get_dependency_graph(
    repo_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    svc = GraphService(session)
    return await svc.get_dependency_graph(repo_id)


@router.get("/repos/{repo_id}/graph/calls")
async def get_call_graph(
    repo_id: uuid.UUID,
    root_symbol: Optional[str] = None,
    depth: int = 3,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    svc = GraphService(session)
    return await svc.get_call_graph(
        repo_id, root_symbol_name=root_symbol, max_depth=depth
    )


@router.get("/repos/{repo_id}/graph/hierarchy")
async def get_hierarchy_graph(
    repo_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    svc = GraphService(session)
    return await svc.get_hierarchy_graph(repo_id)


@router.get("/repos/{repo_id}/treemap")
async def get_treemap(
    repo_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    svc = GraphService(session)
    return await svc.get_treemap(repo_id)


@router.get("/repos/{repo_id}/files/{file_id}")
async def get_file_details(
    repo_id: uuid.UUID,
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    stmt = (
        select(CodeFile)
        .where(CodeFile.id == file_id, CodeFile.repo_id == repo_id)
        .options(selectinload(CodeFile.symbols))
    )
    res = await session.execute(stmt)
    file_obj = res.scalar_one_or_none()
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    # Inbound file dependencies (who imports this file)
    in_stmt = (
        select(FileDependency)
        .where(FileDependency.target_file_id == file_id)
        .options(selectinload(FileDependency.source_file))
    )
    in_res = await session.execute(in_stmt)
    incoming_files = [
        {
            "file_id": str(d.source_file_id),
            "relative_path": d.source_file.relative_path,
            "import_count": d.import_count,
        }
        for d in in_res.scalars().all()
        if d.source_file
    ]

    # Outbound file dependencies (what this file imports)
    out_stmt = (
        select(FileDependency)
        .where(FileDependency.source_file_id == file_id)
        .options(selectinload(FileDependency.target_file))
    )
    out_res = await session.execute(out_stmt)
    outgoing_files = [
        {
            "file_id": str(d.target_file_id),
            "relative_path": d.target_file.relative_path,
            "import_count": d.import_count,
        }
        for d in out_res.scalars().all()
        if d.target_file
    ]

    # Query all cross-file and local calls involving symbols in this file
    sym_ids = [s.id for s in file_obj.symbols]

    callers_map: Dict[uuid.UUID, List[Dict[str, Any]]] = {s_id: [] for s_id in sym_ids}
    callees_map: Dict[uuid.UUID, List[Dict[str, Any]]] = {s_id: [] for s_id in sym_ids}

    if sym_ids:
        # Calls incoming to this file's symbols
        in_calls_stmt = (
            select(GraphEdge)
            .where(GraphEdge.target_symbol_id.in_(sym_ids), GraphEdge.edge_type == "calls")
            .options(
                selectinload(GraphEdge.source_symbol).selectinload(Symbol.file),
            )
        )
        in_calls_res = await session.execute(in_calls_stmt)
        for edge in in_calls_res.scalars().all():
            src = edge.source_symbol
            if src and src.file:
                callers_map[edge.target_symbol_id].append({
                    "caller_symbol": src.name,
                    "caller_file": src.file.relative_path,
                    "caller_file_id": str(src.file.id),
                    "caller_symbol_id": str(src.id),
                    "caller_kind": src.kind,
                    "line": src.start_line,
                })

        # Calls outgoing from this file's symbols
        out_calls_stmt = (
            select(GraphEdge)
            .where(GraphEdge.source_symbol_id.in_(sym_ids), GraphEdge.edge_type == "calls")
            .options(
                selectinload(GraphEdge.target_symbol).selectinload(Symbol.file),
            )
        )
        out_calls_res = await session.execute(out_calls_stmt)
        for edge in out_calls_res.scalars().all():
            tgt = edge.target_symbol
            if tgt and tgt.file:
                callees_map[edge.source_symbol_id].append({
                    "callee_symbol": tgt.name,
                    "callee_file": tgt.file.relative_path,
                    "callee_file_id": str(tgt.file.id),
                    "callee_symbol_id": str(tgt.id),
                    "callee_kind": tgt.kind,
                    "line": tgt.start_line,
                })

    content = ""
    repo_stmt = select(Repository).where(Repository.id == repo_id)
    repo_res = await session.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()
    if repo:
        disk_path = Path(repo.root_path) / file_obj.relative_path
        if disk_path.exists():
            try:
                content = disk_path.read_text(
                    encoding="utf-8", errors="replace"
                )
            except Exception:
                pass

    return {
        "id": str(file_obj.id),
        "relative_path": file_obj.relative_path,
        "language": file_obj.language,
        "size_bytes": file_obj.size_bytes,
        "content": content,
        "incoming_files": incoming_files,
        "outgoing_files": outgoing_files,
        "symbols": [
            {
                "id": str(s.id),
                "name": s.name,
                "kind": s.kind,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "signature": s.signature,
                "docstring": s.docstring,
                "callers": callers_map.get(s.id, []),
                "callees": callees_map.get(s.id, []),
            }
            for s in file_obj.symbols
        ],
    }
