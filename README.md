# codewise

> **understand the code. master the logic.**

**codewise** is an intelligent code explanation, diagnostics, execution, and learning assistant web application. It transforms raw source code into clear, structured mental models: step-by-step logic workflows, input/output specifications, variable tracking, computational complexity, isolated sandboxed execution, and interactive tutoring.

---

## 🎯 Key Capabilities

### 1. Code Editor Workspace (VS Code-Inspired)
- Direct editor with synchronized line numbers and Tab-indentation support.
- File explorer on the left organizing **Source Files** and **Documents & Data**.
- Automatic language detection with manual searchable override across 24+ languages and formats.
- Safe file upload with validation (`.py`, `.js`, `.ts`, `.cpp`, `.c`, `.java`, `.html`, `.css`, `.sql`, `.json`, etc.).
- Active filename reference pill, autosave indicator (`Saved` / `Saving...`), and revision tabs (`v1`, `v2`, ...).
- Quick demonstration samples loader for Python, JavaScript, and C++.

### 2. User Authentication & Session Security
- **Polished Split-Screen Login Experience**: Minimal, developer-first authentication page with black/charcoal surfaces, purple/pink accents, and a syntax-highlighted code editor showcase.
- **Preconfigured Demo Account**: Ready for instant demonstration out of the box (`demo@codewise.dev` / `DemoUser2026!`) with a 1-click "Fill Demo Credentials" button.
- **Cryptographic Password Hashing**: Server-side PBKDF2-HMAC-SHA256 hashing (100,000 iterations) with unique per-user salts and timing-safe comparison (`hmac.compare_digest`).
- **Secure Token Session Management**: Cryptographically secure 256-bit session tokens stored in SQLite with configurable expiration (extended 30-day sessions with "Remember me").
- **Local Security Recovery Keys**: Complete offline password recovery without external email dependencies. Each user receives a unique recovery key (`CW-XXXX-XXXX`) during registration.
- **Strict Protected Routes**: Protected workspace resources require authentication, redirecting unauthenticated users to sign in while preserving all historical user data.
- **In-App Sign Out**: Clean user profile badge and instant logout button in the top navigation bar.

### 3. Structured Code Explanation
- **Program Purpose & Overview**: Identifies problem domain and intent without inventing ambiguous claims.
- **How the Logic Works**: Step-by-step chronological execution flow.
- **Inputs & Outputs**: Classifies input sources, expected types, validation caveats, return values, and console outputs.
- **Line-by-Line Breakdown**: Optional line-referenced drawer mapping exact statements to their computational roles.
- **Dry Run**: Trace table showing step-by-step variable transformations across iterations.
- **Complexity Analysis**: Big-O time and space complexity with derivations (shown only when meaningful for algorithmic code).
- **Key Concepts & Limitations**: Tags key programming concepts and highlights boundary risks (e.g., zero, negative numbers, unvalidated input types).

### 3. Error Detection & Diagnostics
- Parser-level syntax errors with line/column pointers.
- Logic bug detection: division by zero, off-by-one loop indexing, unhandled input conversions, missing headers.
- Severity classification: `error`, `warning`, `suggestion`.
- **Suggested Optimized Code**: Full corrected snippet with detailed notes on what changed and why, with a one-click "Apply Fix" button.

### 4. Sandboxed Code Execution & Runtime Diagnostics
- **Restricted Sandbox**: Code executes in an isolated temporary directory with scrubbed environment variables (all API keys and host secrets stripped).
- **Process Group Isolation**: Spawns isolated process group sessions (`os.setsid()`) terminating entire runaway child trees on timeout with `os.killpg()`.
- **Kernel Resource Limits**: Enforced OS limits (`RLIMIT_CPU` at 6s, `RLIMIT_FSIZE` at 10 MB).
- **Standardized Execution Statuses**: Returns genuine status flags: `success`, `error`, `compilation_error`, `timeout`, `runtime_missing`, `unsupported_runtime`, `unsupported_language`, `backend_unavailable`, and `empty_code`.
- **Runtime Traceback Extraction**: Structured exception parser extracts runtime exception types, error messages, and line numbers into structured `runtime_traceback` diagnostics.
- **Strict Normalized Verification**: `/api/verify-sample` enforces exact character matching (line-ending normalized) requiring `exit_code == 0` and non-timeout, eliminating false-positive substring matching.

### 5. Interactive Learning Assistant & Diagnostics
- Context-aware follow-up tutor drawer anchored along the bottom with vertical resizing and expand/maximize controls.
- Automatically retains the active file code, language, analysis, runtime execution results, and the most recent 10 messages of conversation history.
- Standardized diagnostic detection sources: `confirmed_parser`, `static_type_analysis`, `static_heuristic`, `runtime_traceback`, and `llm_inferred`.
- Strict AI provider isolation honoring `AI_PROVIDER` (`openai` vs `gemini`).

### 6. Persistence, Revision History & IDOR Security
- All sessions, code revisions, analyses, and conversations persist in SQLite (`data/codewise.db`).
- **IDOR Protection**: Strict user session ownership verification across all session endpoints, preventing unauthorized cross-user access or tampering.
- Revisions are created only when code content actually changes; repeated runs or analyses never duplicate versions.
- Built-in backup and restore tool (export/import JSON snapshots with schema validation).

---

## 🎨 Visual Design System

- **Palette**: Professional developer-focused black and pink theme:
  - Primary Background: `#090909`
  - Sidebar / Drawer Background: `#101010`
  - Editor & Panel Surface: `#141414`
  - Subtle Charcoal Borders: `#292329`
  - Primary Pink Accent: `#F472B6`
  - Brighter Pink for Primary Actions: `#EC4899`
  - Soft Pink Highlights: `#F9A8D4`
  - Primary Text: `#F5F5F5`
  - Muted Text: `#A1A1AA` and `#71717A`
- **Clean Layout**: Four clearly separated regions:
  1. File Explorer on the left (collapsible, resizable, 250px default).
  2. Code Editor & Execution Console in the center.
  3. Analysis Panel on the right.
  4. Follow-up Learning Assistant along the bottom.

---

## 💻 Tech Stack

- **Frontend**: React 18, Vite 6, JavaScript (ES Modules), pure CSS variables.
- **Backend**: Python 3.10+ (tested on Python 3.14), FastAPI, Uvicorn, Pydantic v2.
- **Database**: SQLite with foreign key enforcement (`PRAGMA foreign_keys = ON;`) and indexed queries.
- **Analysis**: Python `ast`, regex-based static code scanners, heuristic complexity engines, optional `httpx` LLM client.
- **Sandbox Execution**: Python `subprocess` with isolated `tempfile`, environment scrubbing, timeouts, and `resource.setrlimit`.

---

## 🚀 Quick Start (Local Setup)

### Prerequisites

- Mac with Apple Silicon or Intel (macOS 12+)
- **Python 3.10+** (Python 3.14 recommended)
- **Node.js 18+** & **npm**

### 1. Navigate to Project Directory

```bash
cd ~/Documents/codewise
```

### 2. Configure Environment (Optional)

**No API key is required to use codewise!** The application operates in full Local Mode by default.

To optionally connect an AI provider:
```bash
cp .env.example .env
```
Edit `.env` and set your key:
```env
OPENAI_API_KEY=your_key_here
# or
GEMINI_API_KEY=your_key_here
```

### 3. Start the Application

Run the included startup script:
```bash
./start.sh
```

The script automatically:
1. Verifies Python 3 and Node.js are available.
2. Creates the Python virtual environment in `backend/venv` and installs dependencies if needed.
3. Installs frontend `node_modules` if needed.
4. Starts the backend on `http://127.0.0.1:8000`.
5. Starts the frontend on `http://127.0.0.1:5173`.

### 4. Stop the Application

To shut down codewise cleanly:
```bash
./stop.sh
```
Or press `Ctrl+C` in the terminal where `./start.sh` is running. All saved sessions in `data/codewise.db` remain fully intact.

---

## 🖥 Manual Startup Commands

If you prefer starting backend and frontend in separate terminals:

#### Terminal 1 — Backend:
```bash
source backend/venv/bin/activate
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
- Health Check: [http://127.0.0.1:8000/api/system/status](http://127.0.0.1:8000/api/system/status)
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Terminal 2 — Frontend:
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
- Web Application: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Automated Testing

Run the automated backend test suite inside the Python virtual environment:
```bash
source backend/venv/bin/activate
PYTHONPATH=. pytest backend/tests/ -v
```

**Test Coverage (64 automated tests)**:
- Authentication & login flows, invalid passwords, session persistence, and logout
- Protected route security guards and unauthenticated 401 rejection
- Offline password recovery with Security Recovery Key verification
- Pre-seeded demo account verification (`demo@codewise.dev`)
- API endpoint contracts and HTTP status codes
- AST code analyzers for Python, JavaScript, and C++
- Parser-level syntax and boundary diagnostic checks
- Sandbox environment scrubbing (asserts host secrets are stripped)
- Output size clamping (asserts 64 KB limit)
- Process timeout termination
- Stdin input passing
- Honest rejection for non-runnable formats (SQL, JSON, YAML, Markdown, Dockerfile)
- Honest runtime checks for uninstalled host compilers (Java, C#, Go, Rust)
- Revision deduplication and non-destructive version restoration
- Test database isolation (never pollutes production `codewise.db`)

To verify the frontend production build:
```bash
cd frontend
npm run build
```

---

## 📂 Project Directory Structure

```
codewise/
├── backend/
│   ├── app/
│   │   ├── analyzer/
│   │   │   ├── base.py                 # Abstract analyzer interfaces
│   │   │   ├── python_analyzer.py      # Python AST parsing & static analysis
│   │   │   ├── js_analyzer.py          # JavaScript Acorn AST & boundary scanner
│   │   │   ├── cpp_analyzer.py         # C++ stream & syntax scanner
│   │   │   ├── web_analyzer.py         # HTML/CSS/SCSS DOM & ruleset parser
│   │   │   ├── sql_analyzer.py         # SQL statement & index analyzer
│   │   │   ├── data_analyzer.py        # JSON/YAML/XML/TOML validator
│   │   │   ├── devops_analyzer.py      # Dockerfile & Bash analyzer
│   │   │   ├── general_code_analyzer.py# Java/C#/Go/Rust general code analyzer
│   │   │   ├── static_engine.py        # Language detector & orchestrator
│   │   │   ├── ai_provider.py          # Optional LLM integration with local fallback
│   │   │   └── chat_engine.py          # Learning assistant conversational logic
│   │   ├── routes/
│   │   │   ├── analysis.py             # POST /api/analyze, POST /api/run
│   │   │   ├── sessions.py             # File session CRUD, revisions, restore
│   │   │   ├── chat.py                 # POST /api/sessions/{id}/chat
│   │   │   ├── samples.py              # Built-in demo sample definitions
│   │   │   └── system.py               # Health & mode status endpoint
│   │   ├── config.py                   # Portable paths and environment configuration
│   │   ├── database.py                 # SQLite schema, migrations, connection pool
│   │   ├── detector.py                 # Language registry & capability detection
│   │   ├── executor.py                 # Isolated sandbox runner with resource limits
│   │   ├── models.py                   # Pydantic request & response schemas
│   │   └── main.py                     # FastAPI application setup & CORS
│   ├── tests/
│   │   ├── conftest.py                 # Test database isolation fixture
│   │   ├── test_api.py                 # 22 integration & security tests
│   │   ├── test_python_analyzer.py     # Python AST analyzer tests
│   │   ├── test_js_analyzer.py         # JavaScript bug detection tests
│   │   └── test_cpp_analyzer.py        # C++ stream analyzer tests
│   ├── venv/                           # Python virtual environment (gitignored)
│   └── requirements.txt                # Pinned backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx              # Navigation, mode badge, sample selector
│   │   │   ├── Sidebar.jsx             # File explorer with search, rename, delete
│   │   │   ├── CodeEditor.jsx          # Multi-language editor, run, overflow menu
│   │   │   ├── LanguageDropdown.jsx    # Searchable language selector
│   │   │   ├── AnalysisView.jsx        # Structured explanation & explore drawers
│   │   │   ├── ExecutionConsole.jsx    # Terminal console with stdout/stderr/time
│   │   │   ├── HtmlPreviewModal.jsx    # Sandboxed live HTML/CSS preview
│   │   │   ├── ChatAssistant.jsx       # Interactive follow-up tutor drawer
│   │   │   ├── ResizableDivider.jsx    # Draggable splitter handles
│   │   │   ├── AboutModal.jsx          # Project information modal
│   │   │   ├── BackupModal.jsx         # SQLite history export/import
│   │   │   └── Icons.jsx               # Crisp SVG interface icons
│   │   ├── services/
│   │   │   └── api.js                  # Frontend API service layer
│   │   ├── utils/
│   │   │   └── languageCapabilities.js # Capability sets & extension mappings
│   │   ├── App.jsx                     # 4-region layout & application state
│   │   ├── main.jsx                    # Vite entrypoint
│   │   └── index.css                   # Black & pink theme styles
│   ├── package.json                    # Frontend dependencies
│   ├── package-lock.json               # Locked dependency tree
│   ├── vite.config.js                  # Vite configuration
│   └── index.html                      # HTML entry template
├── data/                               # Local SQLite database (codewise.db)
├── samples/                            # Demo source files
├── .env.example                        # Template for environment variables
├── .gitignore                          # Git ignore rules
├── requirements.txt                    # Root-level requirements mirror
├── start.sh                            # One-click startup script (macOS/Linux)
├── stop.sh                             # Clean shutdown script
└── README.md                           # Documentation
```

---

## 🍏 Transferring to Another Mac

To transfer **codewise** to a new Mac computer:

### 1. Copy the Project Folder
Copy the `codewise` folder to the target Mac (e.g., to `~/Documents/codewise`). Exclude `backend/venv` and `frontend/node_modules` for a lightweight transfer.

### 2. Verify System Prerequisites
Ensure the target Mac has:
- **Python 3.10+**: Run `python3 --version`. (Install from [python.org](https://www.python.org) or `brew install python` if missing).
- **Node.js 18+**: Run `node -v`. (Install from [nodejs.org](https://nodejs.org) or `brew install node` if missing).

### 3. Run Startup Script
Open Terminal and run:
```bash
cd ~/Documents/codewise
./start.sh
```
`start.sh` automatically creates the Python virtual environment, installs backend dependencies, installs frontend dependencies, and launches the application.

---

## 💾 Backing Up & Transferring History

There are two easy methods to transfer your saved sessions, code revisions, and chat history:

### Method A: In-App Backup (Recommended)
1. On the source Mac, open codewise in your browser.
2. Click **Backup** in the top navigation bar.
3. Click **Download Backup** to save a `.json` file containing all files, code revisions, analyses, and messages.
4. On the target Mac, open codewise, click **Backup**, and select **Upload Backup JSON**.

### Method B: Direct Database Copy
1. Copy the file `data/codewise.db` from your source Mac to `data/codewise.db` on the new Mac.
2. Start codewise. The database will automatically load with all saved files intact.

---

## 🔒 Security & Privacy Principles

- **Zero Secret Exposure**: User-submitted code executes with a scrubbed environment (`get_sanitized_env`), ensuring API keys, project environment variables, and host credentials are never accessible.
- **Sandboxed Execution**: Executed code runs inside an isolated temporary directory with enforced timeouts (5.0s), CPU limits (6s/8s), and file creation caps (10 MB).
- **Local-First Privacy**: Code analysis, explanations, complexity estimation, and tutor conversations operate 100% locally by default without transmitting data to third-party servers.
- **Strictly Local Scope**: No GitHub connections, remote databases, or cloud deployments (e.g. Render) have been provisioned or configured.
