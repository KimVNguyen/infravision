"""SQLAlchemy 2.0 ORM models for code intelligence and index storage."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from infravision.config import settings


class Base(DeclarativeBase):
    pass


class Repository(Base):
    """A registered repository or codebase root."""

    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_path: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    files: Mapped[List["CodeFile"]] = relationship(
        "CodeFile", back_populates="repository", cascade="all, delete-orphan"
    )
    file_dependencies: Mapped[List["FileDependency"]] = relationship(
        "FileDependency", back_populates="repository", cascade="all, delete-orphan"
    )


class CodeFile(Base):
    """An indexed source file within a repository."""

    __tablename__ = "code_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'python', 'typescript', 'javascript'
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="files")
    symbols: Mapped[List["Symbol"]] = relationship(
        "Symbol", back_populates="file", cascade="all, delete-orphan"
    )
    chunks: Mapped[List["CodeChunk"]] = relationship(
        "CodeChunk", back_populates="file", cascade="all, delete-orphan"
    )
    outgoing_file_deps: Mapped[List["FileDependency"]] = relationship(
        "FileDependency",
        foreign_keys="FileDependency.source_file_id",
        back_populates="source_file",
        cascade="all, delete-orphan",
    )
    incoming_file_deps: Mapped[List["FileDependency"]] = relationship(
        "FileDependency",
        foreign_keys="FileDependency.target_file_id",
        back_populates="target_file",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_code_files_repo_path", "repo_id", "relative_path", unique=True),
        Index("idx_code_files_hash", "file_hash"),
    )


class FileDependency(Base):
    """Direct architectural dependency between two files (import, require)."""

    __tablename__ = "file_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_import_path: Mapped[str] = mapped_column(String(512), nullable=False)
    import_count: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="file_dependencies"
    )
    source_file: Mapped["CodeFile"] = relationship(
        "CodeFile", foreign_keys=[source_file_id], back_populates="outgoing_file_deps"
    )
    target_file: Mapped["CodeFile"] = relationship(
        "CodeFile", foreign_keys=[target_file_id], back_populates="incoming_file_deps"
    )

    __table_args__ = (
        Index("idx_file_deps_source", "source_file_id"),
        Index("idx_file_deps_target", "target_file_id"),
        Index("idx_file_deps_repo", "repo_id"),
    )


class Symbol(Base):
    """An extracted AST symbol (function, class, method, interface, type)."""

    __tablename__ = "symbols"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # 'function', 'class', 'method', 'interface', 'type_alias', 'variable'
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    file: Mapped["CodeFile"] = relationship("CodeFile", back_populates="symbols")
    outgoing_edges: Mapped[List["GraphEdge"]] = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.source_symbol_id",
        back_populates="source_symbol",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[List["GraphEdge"]] = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.target_symbol_id",
        back_populates="target_symbol",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_symbols_name", "name"),
        Index("idx_symbols_kind", "kind"),
        Index("idx_symbols_file_id", "file_id"),
    )


class GraphEdge(Base):
    """A semantic relationship between code symbols (calls, extends, implements)."""

    __tablename__ = "graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # 'calls', 'extends', 'implements', 'references'

    # Relationships
    source_symbol: Mapped["Symbol"] = relationship(
        "Symbol", foreign_keys=[source_symbol_id], back_populates="outgoing_edges"
    )
    target_symbol: Mapped["Symbol"] = relationship(
        "Symbol", foreign_keys=[target_symbol_id], back_populates="incoming_edges"
    )

    __table_args__ = (
        Index("idx_edges_source", "source_symbol_id"),
        Index("idx_edges_target", "target_symbol_id"),
        Index("idx_edges_type", "edge_type"),
    )


class CodeChunk(Base):
    """A semantic code chunk with full-text search capability and pgvector embedding."""

    __tablename__ = "code_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[Text] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )

    # Relationships
    file: Mapped["CodeFile"] = relationship("CodeFile", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_file_id", "file_id"),
        Index(
            "idx_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
