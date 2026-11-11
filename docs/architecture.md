# Infravision Architecture & Design

This document details the underlying architecture, data models, indexing pipeline, and graph rendering engine of Infravision.

---

## 1. High-Level Architecture

Infravision operates in three distinct phases:
1. **Scanning & Ingestion**: Traversing the repository, filtering non-code artifacts, and computing file hashes.
2. **AST Parsing & Graph Construction**: Extracting symbols, imports, and calls via Tree-sitter, resolving module paths, and persisting nodes and edges to PostgreSQL.
3. **Graph Querying & Visualization**: Transforming database relational models into directed acyclic graphs (DAGs) and rendering them on an interactive canvas with automated Dagre layout.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 1: Ingestion                              │
│                                                                        │
│   Source Code Files  ──►  RepositoryScanner  ──►  DiscoveredFiles       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 2: Indexing Pipeline                      │
│                                                                        │
│   Tree-sitter AST Parsers (Python & TypeScript)                        │
│   ├── Symbols (Classes, Functions, Interfaces, Types)                  │
│   ├── Imports (module_specifier, imported_symbols)                     │
│   └── Calls & Inheritance (source_symbol, target_symbol)               │
│                                                                        │
│   Module Resolver Engine                                               │
│   ├── Relative Imports (./, ../, .module, ..parent)                    │
│   ├── Path Aliases (@/* -> src/*)                                      │
│   └── Python Package Proximity Matching (pkg.mod -> path/to/pkg/mod)   │
│                                                                        │
│   PostgreSQL Persistence                                               │
│   ├── CodeFiles & Repositories                                         │
│   ├── FileDependencies (file_id -> file_id)                            │
│   ├── Symbols (start_line, end_line, signature, docstring)             │
│   └── GraphEdges (source_symbol_id -> target_symbol_id)                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 3: Visualization                          │
│                                                                        │
│   FastAPI Endpoints                                                    │
│   ├── /api/repos/{id}/graph/dependencies                               │
│   ├── /api/repos/{id}/graph/calls                                      │
│   ├── /api/repos/{id}/graph/hierarchy                                  │
│   └── /api/repos/{id}/files/{file_id}                                  │
│                                                                        │
│   Frontend Canvas (React 19 + React Flow + Dagre)                      │
│   ├── Automated LR / TB Hierarchical Layout                            │
│   ├── Active Node Glow & Camera Auto-Centering                         │
│   └── Inspector Drawer with VS Code Dark Syntax Highlighting           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema

The PostgreSQL database models the codebase as a hierarchical relational graph:

### `repositories`
Represents an indexed codebase.
- `id` (UUID, Primary Key)
- `name` (String)
- `root_path` (String, Unique)
- `last_indexed_at` (DateTime, UTC)

### `code_files`
Represents individual source files within a repository.
- `id` (UUID, Primary Key)
- `repo_id` (UUID, Foreign Key $\rightarrow$ `repositories.id`)
- `relative_path` (String, Indexed)
- `language` (String: `python`, `typescript`, `javascript`)
- `file_hash` (String, SHA-256 for change detection)
- `size_bytes` (Integer)

### `file_dependencies`
Represents direct import relationships between files.
- `id` (UUID, Primary Key)
- `repo_id` (UUID, Foreign Key)
- `source_file_id` (UUID, Foreign Key $\rightarrow$ `code_files.id`)
- `target_file_id` (UUID, Foreign Key $\rightarrow$ `code_files.id`)
- `raw_import_path` (String)
- `import_count` (Integer)

### `symbols`
Represents code declarations extracted from the AST.
- `id` (UUID, Primary Key)
- `file_id` (UUID, Foreign Key $\rightarrow$ `code_files.id`)
- `name` (String, Indexed)
- `kind` (String: `class`, `function`, `method`, `interface`, `type_alias`)
- `start_line` (Integer)
- `end_line` (Integer)
- `signature` (String, e.g. `def parse_source(code: str) -> ParseResult`)
- `docstring` (Text, optional)
- `scope_path` (String, e.g. `UserService.create_user`)

### `graph_edges`
Represents symbol-level relationships across or within files.
- `id` (UUID, Primary Key)
- `source_symbol_id` (UUID, Foreign Key $\rightarrow$ `symbols.id`)
- `target_symbol_id` (UUID, Foreign Key $\rightarrow$ `symbols.id`)
- `edge_type` (String: `calls`, `extends`, `implements`)

---

## 3. Tree-sitter AST Extraction

Infravision utilizes official Tree-sitter grammars compiled into native libraries:

### Python Parser (`infravision.parser.python`)
Recursively traverses the Python AST:
- **`class_definition`**: Extracts class name, docstring, scope, and superclasses (`superclasses` $\rightarrow$ `extends` edges).
- **`function_definition` / `async_function_definition`**: Identifies whether it is a function or method based on scope depth, extracts parameter list, return type annotation, and docstring.
- **`call`**: Resolves the callee name (handling dotted invocations like `self.validate` or `service.execute`) and attributes it to the current enclosing function/method.
- **`import_from_statement`**: Extracts `module_name` and list of `imported_symbols`.
- **`import_statement`**: Extracts package names and aliased imports.

### TypeScript / JavaScript Parser (`infravision.parser.typescript`)
Configured to support TSX/JSX syntax:
- **`interface_declaration`**: Extracts interface names and extends clauses.
- **`type_alias_declaration`**: Extracts custom type definitions.
- **`class_declaration`**: Extracts classes, methods, and heritage clauses (`extends`, `implements`).
- **`function_declaration` & `lexical_declaration`**: Extracts standard functions and arrow functions assigned to `const`/`let`.
- **`jsx_element` / `jsx_self_closing_element`**: Treats JSX component usages (`<Header />`, `<CustomNode />`) as function invocations so React component hierarchies are fully mapped into the call graph.
- **`import_statement` & `export_statement`**: Extracts source specifiers, default imports, and named imports.

---

## 4. Module Resolution Engine

The module resolution engine maps import specifiers to concrete files within the repository:

1. **Relative Imports**:
   - TypeScript/JS: Relative to the source file's directory (`./components/Header` $\rightarrow$ `src/components/Header.tsx`).
   - Python: Resolves leading dot depth (`.models` is sibling directory, `..indexer.pipeline` is parent directory).
2. **Path Aliases**:
   - Automatically translates `@/*` prefixes to `src/*`.
3. **Python Package Resolution**:
   - Supports monorepo structures where code lives in subfolders (e.g. `backend/src/infravision/...`).
   - Suffix matching locates the package stem (`infravision.db.models` matches any indexed file ending with `/infravision/db/models.py`).
   - Path proximity scoring resolves ambiguities if duplicate package names exist in separate directories.
4. **Index Files**:
   - Resolves directories importing an index file (`index.ts`, `index.tsx`, `index.js`, `__init__.py`).

---

## 5. Graph Rendering & UI Architecture

- **React Flow (`@xyflow/react`)**: Provides the infinite canvas, node rendering, zoom/pan handlers, and minimap.
- **Dagre Layout Engine**:
  - Automatically calculates `x` and `y` coordinates for every node and edge route.
  - Avoids manual node dragging by calculating optimal hierarchical spacing.
  - Supports dynamic switching between Left-to-Right (`LR`) and Top-to-Bottom (`TB`).
- **Active Node Synchronization**:
  - Selecting a node on the canvas updates the active node ID in the global React state.
  - The node is dynamically re-styled with an emerald glowing border and an animated `ACTIVE` badge.
  - The camera smoothly interpolates to center on the active node using React Flow's `setCenter()` API.
- **Integrated Code Viewer**:
  - Uses `react-syntax-highlighter` with Prism and the **VS Code Dark (`vscDarkPlus`)** theme.
  - Renders line numbers in the gutter.
  - Smoothly auto-scrolls to target lines when jumping from caller/callee links and renders an amber ribbon highlight.
