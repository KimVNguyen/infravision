# Infravision User & Exploration Guide

This guide walks through using Infravision to explore, understand, and navigate codebases visually.

---

## 1. Getting Started

1. Open your browser and navigate to **`http://localhost:5173`** (or your device hostname, e.g. `http://pi5:5173`).
2. Use the repository selector dropdown in the top navigation bar to choose an indexed project:
   - **`storybot-ui`**: Front-end React Native / TypeScript codebase.
   - **`infravision`**: The complete full-stack Infravision repository (Python backend + React frontend).
   - **`backend/src`**: Python backend package internals.

---

## 2. The Graph Canvas

### Navigation Controls
- **Pan**: Click and drag on the background canvas to pan around the graph.
- **Zoom**: Use your mouse wheel or the `+` / `-` controls in the bottom-left corner.
- **Fit View**: Click the expand icon in the bottom-left controls to fit all nodes on screen.
- **Minimap**: The bottom-right minimap displays your current camera viewport relative to the overall graph. Click anywhere on the minimap to jump directly there.

### Visual Metrics on Node Cards
Every node represents a source file and provides immediate at-a-glance metrics:
- **Language Badge**: Color-coded badge (`Python`, `TypeScript`, `JavaScript`).
- **File Name & Path**: Relative directory path within the repository.
- **Symbol Metric**: Total count of top-level functions, classes, and interfaces declared in the file.
- **Size Metric**: File size in bytes or kilobytes.

---

## 3. Visualization Modes

Switch between modes using the segmented pill buttons in the top navbar:

### Mode 1: Architecture Dependencies (`Dependencies`)
- **What it shows**: File-to-file local import dependencies.
- **Edge Badges**:
  - `imports`: General import statement connecting two files.
  - `X calls (fn1, fn2...)`: Displays the exact number of functions and methods called between those two files.
- **Use Cases**:
  - Understanding modularity and package structure.
  - Detecting architectural coupling between directories.
  - Identifying isolated or unused files.

### Mode 2: Function Call Flow (`Call Flow`)
- **What it shows**: Function-to-function invocation graph.
- **Nodes**: Individual functions, methods, and React components.
- **Edges**: Direct function calls (`fn_a` calls `fn_b`).
- **Use Cases**:
  - Tracing execution flow from API routes down to database models.
  - Tracing user interaction events in React down through state hooks and API clients.

### Mode 3: OOP & Type Hierarchy (`Hierarchy`)
- **What it shows**: Object-oriented class inheritance and TypeScript interface contracts.
- **Edges**:
  - `extends`: Class inheritance (e.g. `UserService extends BaseService`).
  - `implements`: TypeScript interface contracts (e.g. `UserRepository implements IRepository`).
- **Use Cases**:
  - Exploring domain models and service abstractions.
  - Understanding inheritance trees and base classes.

---

## 4. Deep Code Inspection & Tracing

Clicking any node on the canvas opens the **File Inspector Drawer** on the right side of the screen.

### 1. Active Node Glow & Camera Auto-Centering
- When you click a node, the canvas camera **automatically pans and zooms** to place the node in the center of the viewport.
- The active node is highlighted with an **emerald glowing border** and an animated **`ACTIVE`** badge.

### 2. Tab: Functions & Callers
- Displays every top-level function, method, class, interface, and type alias in the file.
- **Signatures & Docstrings**: Shows typed arguments, return types, and docstring documentation.
- **Cross-File Callers (`Called By`)**:
  - Lists every other file and function in the repository that calls this function.
  - Displays the caller file name and exact line number (e.g. `settings.tsx:97`).
  - **Clicking a caller link immediately jumps to that file**, focuses it on the canvas, opens its source code, and highlights that line.
- **Cross-File Callees (`Calls`)**:
  - Lists functions in other files called by this function.
  - Clicking any callee immediately jumps to the definition in that file.

### 3. Tab: File Links
- Displays high-level file dependencies:
  - **Inbound (`Files that import this file`)**: The upstream blast radius of the file.
  - **Outbound (`Files imported by this file`)**: Direct local imports.
  - Click any file in this tab to instantly switch the drawer to that file.

### 4. Tab: Source Code
- Full syntax-highlighted code viewer styled with the **VS Code Dark (`vscDarkPlus`)** theme.
- Line numbers displayed in the gutter.
- **Target Line Highlighting**: When jumping from a caller, callee, or symbol definition, the viewer automatically scrolls to the line and highlights it with an **amber ribbon**.

### 5. Breadcrumb Navigation (`← Back`)
- As you navigate through caller links across files, Infravision maintains your exploration history stack.
- Click the **`← Back`** button at the top of the drawer to return to the previous file and line.

---

## 5. Indexing New Codebases

To visualize any codebase on your computer:

1. **Mount the Directory**: Ensure the directory is accessible to Docker by adding it as a volume mount in `compose.yaml`:
   ```yaml
   volumes:
     - "/path/to/my/project:/my-project:ro"
   ```
2. **Apply Compose Update**:
   ```bash
   docker compose up -d
   ```
3. **Index from UI**:
   - In the web app, click **+ Index Path**.
   - Enter `/my-project`.
   - Click **Index Repository**.
   - Once indexing finishes (typically $1-3$ seconds), the codebase is added to your repository list and rendered immediately.
