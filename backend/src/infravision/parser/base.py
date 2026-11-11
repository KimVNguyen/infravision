"""Base definitions and types for Tree-sitter AST extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedSymbol:
    name: str
    kind: str  # function, class, method, interface, type_alias, variable
    start_line: int
    end_line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    scope_path: Optional[str] = None


@dataclass
class ParsedEdge:
    source_symbol: str
    target_symbol: str
    edge_type: str  # calls, imports, extends, implements, references


@dataclass
class ParsedImport:
    module_specifier: str  # e.g. '../features/sites/useSites' or 'infravision.db.models'
    imported_symbols: List[str] = field(default_factory=list)
    is_type_only: bool = False


@dataclass
class ParsedChunk:
    start_line: int
    end_line: int
    content: str
    symbol_name: Optional[str] = None


@dataclass
class ParseResult:
    symbols: List[ParsedSymbol] = field(default_factory=list)
    edges: List[ParsedEdge] = field(default_factory=list)
    chunks: List[ParsedChunk] = field(default_factory=list)
    imports: List[ParsedImport] = field(default_factory=list)


class BaseLanguageParser(ABC):
    """Abstract interface for language-specific AST parsers."""

    @abstractmethod
    def parse_source(self, code: str, file_path: str = "") -> ParseResult:
        """Parse source code into symbols, relations, imports, and chunks."""
        pass
