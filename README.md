# Infravision

**Infravision** is an interactive, full-stack code architecture and graph visualization platform for **Python**, **TypeScript**, and **JavaScript** codebases.

It parses repositories into abstract syntax trees (ASTs) using **Tree-sitter**, extracts classes, functions, methods, interfaces, and imports, maps cross-file dependencies and function call hierarchies into **PostgreSQL**, and renders them on an interactive canvas powered by **React Flow** and **Dagre**.

---

## Key Features

- **Multi-Language AST Parsing**:
  - Python (`.py`): classes, functions, methods, docstrings, imports (`import`, `from ... import`, relative dot imports), function invocations, and class inheritance.
  - TypeScript & JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`): interfaces, type aliases, classes, functions, methods, JSX component tags (`<Component />`), imports, and path aliases (`@/*`).
- **Interactive Graph Canvas**:
  - **Hierarchical Layouts**: Automated Dagre Left-to-Right (`LR`) and Top-to-Bottom (`TB`) layout engines.
  - **Active Node Tracking**: The actively inspected node glows with an emerald border and an animated `ACTIVE` badge.
  - **Smooth Camera Auto-Centering**: Selecting any node or jumping from a caller/callee automatically pans and zooms the canvas to center on that node.
  - **Minimap & Navigation Controls**: Zoom, pan, fit-to-view, and cluster grouping.
- **Three Specialized Visualization Modes**:
  1. **Architecture Dependencies**: File-to-file import relationships with badge counts showing local functions called across each edge.
  2. **Function Call Flow**: Direct symbol-to-symbol invocation graph mapping exact call paths across files.
  3. **OOP & Type Hierarchy**: Class inheritance (`extends`) and TypeScript interface contracts (`implements`).
- **Deep Inspector Drawer**:
  - **Functions & Callers Tab**: Detailed symbol cards showing parameters, return types, docstrings, and cross-file callers (`Called By`) and callees (`Calls`).
  - **Click-to-Jump Navigation**: Clicking any caller or callee immediately jumps to that file, centers the node on the canvas, opens the code viewer, and auto-scrolls directly to the line of the call.
  - **File Links Tab**: Direct incoming and outgoing local file imports with click-to-navigate.
  - **Source Code Tab**: Integrated code viewer featuring **VS Code Dark (`vscDarkPlus`)** syntax highlighting, line numbers, and an amber highlight ribbon on targeted lines.
  - **Navigation History Stack**: `← Back` breadcrumb navigation allows tracing call chains forward and backward seamlessly.
- **Enterprise-Grade Container Security**:
  - 100% rootless: All containers (`backend`, `frontend`, `postgres`) run under dedicated non-root users (`UID 1000` / `UID 999`).
  - Closed host ports: Database (`5432`) and backend API (`8000`) are closed from the host and communicate exclusively over private Docker internal networking.
  - Only the frontend port (`5173`) is exposed to the host machine.
- **Configurable Hot Reloading (`DEV_MODE`)**:
  - Controlled by a single flag in `.env`.
  - When `DEV_MODE=true`: Live bind mounts with Uvicorn `WatchFiles` reload on backend and Vite instant Hot Module Replacement (HMR) on frontend.
  - When `DEV_MODE=false`: High-performance multi-worker production Uvicorn and pre-compiled static bundle.

---

## System Architecture

```
                          Host Machine / Browser
                                   │
                                   ▼
                   http://localhost:5173 (Port 5173)
┌────────────────────────────────────────────────────────────────────────┐
│                        DOCKER BRIDGE NETWORK                           │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ infravision-frontend (Vite Dev Server / Nginx)                 │   │
│   │ - User: node (UID 1000)                                        │   │
│   │ - Serves React Flow, Dagre, & VS Code Dark Syntax Highlighting │   │
│   │ - Reverse proxies /api/* internally to backend:8000            │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ http://backend:8000/api            │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ infravision-backend (FastAPI + Tree-sitter)                    │   │
│   │ - User: appuser (UID 1000)                                     │   │
│   │ - Closed to host (no open host port)                           │   │
│   │ - Tree-sitter Python & TypeScript AST extractors               │   │
│   │ - Module resolver (relative imports, aliases, package stems)   │   │
│   │ - Graph assembly & cycle detection service                     │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ postgresql://postgres:5432         │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ infravision-postgres (PostgreSQL 16)                           │   │
│   │ - User: postgres (UID 999)                                     │   │
│   │ - Closed to host (no open host port)                           │   │
│   │ - Stores Repositories, CodeFiles, Symbols, Edges, Dependencies │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Quickstart

### Prerequisites
- Docker Engine $\ge 24.0$
- Docker Compose $\ge 2.20$

### 1. Configure Environment Secrets
Copy the example environment configuration:
```bash
cp .env.example .env
```

Review or modify `.env` as desired:
```env
# Development / Hot Reload Mode (true = instant reload, false = production build)
DEV_MODE=true

# Database credentials
POSTGRES_USER=infravision
POSTGRES_PASSWORD=infravision_secret_change_me
POSTGRES_DB=infravision

# Directories mounted into container for indexing
HOST_WORKSPACE=..
STORYBOT_UI_PATH=../story_bot/frontend

# Frontend exposed port
FRONTEND_PORT=5173
```

### 2. Launch the Application
Start the containers in the background:
```bash
docker compose up --build -d
```

### 3. Open the Web Interface
Navigate to **[http://localhost:5173](http://localhost:5173)** in your browser (or your machine's hostname, e.g. `http://pi5:5173`).

---

## Using the Interface

### 1. Selecting or Indexing a Codebase
Use the repository dropdown in the top navigation bar to select an indexed codebase. Preset buttons allow one-click switching between mounted directories:
- **`storybot-ui`**: React Native / Expo TypeScript codebase.
- **`infravision`**: The full Infravision monorepo (Python backend + TypeScript frontend).
- **`backend/src`**: Infravision Python package internals.

To index a custom folder mounted into the container:
1. Click **+ Index Path**.
2. Enter the absolute path inside the container (e.g. `/workspace/my-project`).
3. Click **Index Repository**. The AST pipeline will scan, parse, resolve dependencies, and render the graph.

### 2. Switching Graph Modes
Use the mode segmented control in the top bar:
- **Dependencies**: Shows file-level architecture. Edges indicate import dependencies. Numbers on edges show how many function/symbol calls occur between those files.
- **Call Flow**: Displays individual functions, methods, and components. Edges trace exact execution and call relationships.
- **Hierarchy**: Displays class inheritance (`class A extends B`) and TypeScript interfaces.

### 3. Layout Direction
Toggle between **LR** (Left to Right) and **TB** (Top to Bottom) using the layout orientation button in the top bar to reorganize the Dagre layout.

### 4. Inspecting Files & Tracing Calls
1. **Click any node** on the canvas:
   - The node is highlighted with an **emerald border** and an **`ACTIVE`** badge.
   - The canvas smoothly centers on that node.
   - The right drawer slides open with the file's details.
2. In the **Functions & Callers** tab:
   - Browse all top-level classes, methods, and functions.
   - Click a **Called By** or **Calls** entry to jump directly to the calling file and highlight the exact line.
   - Use the **`← Back`** button at the top of the drawer to navigate back through your exploration history.
3. In the **Source Code** tab:
   - View code formatted with **VS Code Dark (`vscDarkPlus`)** syntax highlighting.
   - Target lines from caller links are automatically highlighted with an amber ribbon and scrolled into view.

---

## Project Structure

```
infravision/
├── compose.yaml                   # Rootless multi-container orchestration
├── .env.example                   # Environment template
├── .env                           # Active environment configuration
├── docs/                          # Detailed technical documentation
│   ├── architecture.md            # Data pipeline & AST parsing design
│   └── user_guide.md              # Navigation & code exploration guide
├── backend/                       # Python FastAPI Backend
│   ├── Dockerfile                 # Rootless Python 3.12 container
│   ├── entrypoint.sh              # DEV_MODE hot reload vs production switcher
│   ├── pyproject.toml             # uv package manifest and dependencies
│   ├── src/infravision/
│   │   ├── api/                   # FastAPI application & route endpoints
│   │   │   ├── app.py             # App lifecycle & CORS middleware
│   │   │   └── routes.py          # Repositories, files, and graph endpoints
│   │   ├── config.py              # Pydantic environment configuration
│   │   ├── db/                    # SQLAlchemy database layer
│   │   │   ├── models.py          # PostgreSQL schema (CodeFile, Symbol, Edges)
│   │   │   └── session.py         # Async engine & session dependency
│   │   ├── graph/                 # Graph assembly & analytics
│   │   │   └── service.py         # Dependency graphs, call graphs, cycles
│   │   ├── indexer/               # Code scanner & pipeline
│   │   │   ├── scanner.py         # Directory walker & language detector
│   │   │   └── pipeline.py        # AST orchestrator & module resolver
│   │   └── parser/                # Tree-sitter AST extractors
│   │       ├── base.py            # Parser interfaces & data structures
│   │       ├── python.py          # Python AST parser
│   │       └── typescript.py      # TypeScript / TSX / JavaScript AST parser
│   └── tests/                     # Parser and resolver unit tests
│       └── test_parsers.py        # Pytest test suite
└── frontend/                      # React TypeScript Frontend
    ├── Dockerfile                 # Rootless Node 22 container
    ├── entrypoint.sh              # DEV_MODE Vite HMR vs production preview
    ├── nginx.conf                 # Nginx reverse proxy configuration
    ├── package.json               # Frontend dependencies & scripts
    ├── vite.config.ts             # Vite dev server, allowedHosts, & API proxy
    ├── src/
    │   ├── api.ts                 # Typed backend client
    │   ├── types.ts               # Shared TypeScript models
    │   ├── App.tsx                # Main application layout, navbar, & state
    │   ├── index.css              # Tailwind CSS styles & animations
    │   └── components/
    │       ├── CustomNode.tsx     # Custom React Flow node with active styling
    │       ├── GraphCanvas.tsx    # React Flow canvas with Dagre layout & auto-center
    │       └── FileDrawer.tsx     # File inspector with VS Code Dark code viewer
```

---

## Technical Details

### AST Extraction
Infravision relies on official Tree-sitter parsers (`tree-sitter-python` and `tree-sitter-typescript`):
- **Python**: Extracts `class_definition`, `function_definition`, `async_function_definition`, `call`, `import_statement`, `import_from_statement`, docstrings, and superclass inheritance.
- **TypeScript & JavaScript**: Extracts `interface_declaration`, `type_alias_declaration`, `class_declaration`, `function_declaration`, `lexical_declaration` (arrow functions), `jsx_element` / `jsx_self_closing_element`, `import_statement`, and `export_statement`.

### Module Resolution Engine
The resolution engine ([`pipeline.py`](backend/src/infravision/indexer/pipeline.py)) resolves raw import strings to indexed files:
- **Relative Imports**: Translates `.`, `..`, `./`, and `../` based on source file directory depth.
- **TypeScript Path Aliases**: Automatically maps `@/*` to `src/*`.
- **Python Package Names**: Resolves absolute module identifiers (e.g. `infravision.db.models`) against repository package locations (e.g. `backend/src/infravision/db/models.py`) using suffix and path proximity matching.
- **Directory Index Files**: Resolves `index.ts`, `index.tsx`, `index.js`, and `__init__.py`.

---

## Docker Commands Cheat Sheet

| Task | Command |
| :--- | :--- |
| **Start stack** | `docker compose up -d` |
| **Rebuild containers** | `docker compose up --build -d` |
| **View logs** | `docker compose logs -f` |
| **View backend logs** | `docker compose logs -f backend` |
| **View frontend logs** | `docker compose logs -f frontend` |
| **Stop stack** | `docker compose down` |
| **Reset database volume** | `docker compose down -v` |
| **Run unit tests** | `docker compose exec backend python /workspace/infravision/backend/tests/test_parsers.py` |

---

## License

MIT
