# Infravision Backend

FastAPI graph intelligence engine and Tree-sitter AST indexing pipeline for Python and TypeScript/JavaScript codebases.

---

## Responsibilities

1. **Repository Scanning & Filtering** ([`indexer/scanner.py`](src/infravision/indexer/scanner.py)):
   - Traverses directories, pruning build artifacts, virtual environments, and caches.
   - Detects languages and computes SHA-256 hashes for incremental indexing.
2. **Tree-sitter AST Parsing** ([`parser/`](src/infravision/parser/)):
   - **`python.py`**: Extracts classes, functions, methods, docstrings, imports, call expressions, and inheritance.
   - **`typescript.py`**: Extracts interfaces, types, classes, functions, arrow functions, JSX component tags, and imports.
3. **Module & Import Resolution** ([`indexer/pipeline.py`](src/infravision/indexer/pipeline.py)):
   - Resolves relative imports (`./`, `../`, `.mod`), TypeScript aliases (`@/*`), and Python package hierarchy.
   - Discovers cross-file symbol calls and inheritance edges.
4. **Relational Graph Persistence** ([`db/models.py`](src/infravision/db/models.py)):
   - Stores repositories, files, file dependencies, symbols, and graph edges in PostgreSQL 16.
5. **Graph Projections & Analytics** ([`graph/service.py`](src/infravision/graph/service.py)):
   - Generates file dependency DAGs, function call flow graphs, and class inheritance hierarchies.
   - Performs cycle detection to highlight architectural coupling.

---

## API Endpoints

- `GET /api/repos`: Lists all indexed repositories.
- `POST /api/repos`: Indexes or re-indexes a directory path.
- `GET /api/repos/{id}/graph/dependencies`: Direct file dependencies with called symbol metrics.
- `GET /api/repos/{id}/graph/calls`: Function-to-function invocation graph.
- `GET /api/repos/{id}/graph/hierarchy`: OOP class inheritance and interface implementation hierarchy.
- `GET /api/repos/{id}/files/{file_id}`: File source code, incoming/outgoing dependencies, and symbol callers/callees.

---

## Testing

Run the test suite inside the container:
```bash
docker compose exec backend python /workspace/infravision/backend/tests/test_parsers.py
```
