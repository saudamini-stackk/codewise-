import sqlite3
import json
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Generator, List, Optional, Dict, Any
from .config import DB_PATH

def get_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """Initialize database tables with indexes."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Code versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_versions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                code TEXT NOT NULL,
                language TEXT NOT NULL,
                filename TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            );
        """)

        # Analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                code_version_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                overview TEXT NOT NULL,
                logic_workflow TEXT NOT NULL,
                line_by_line_json TEXT NOT NULL,
                inputs_text TEXT NOT NULL,
                outputs_text TEXT NOT NULL,
                variables_functions_json TEXT NOT NULL,
                concepts_json TEXT NOT NULL,
                limitations_json TEXT NOT NULL,
                complexity_time TEXT NOT NULL,
                complexity_space TEXT NOT NULL,
                complexity_explanation TEXT NOT NULL,
                learning_takeaway TEXT NOT NULL,
                diagnostics_json TEXT NOT NULL,
                suggested_code TEXT,
                explanation_of_changes TEXT,
                dry_run_json TEXT,
                loop_details_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (code_version_id) REFERENCES code_versions (id) ON DELETE CASCADE
            );
        """)

        # Migration: ensure dry_run_json and loop_details_json exist
        try:
            cursor.execute("ALTER TABLE analyses ADD COLUMN dry_run_json TEXT;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE analyses ADD COLUMN loop_details_json TEXT;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE analyses ADD COLUMN expected_io_json TEXT;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE analyses ADD COLUMN viva_questions_json TEXT;")
        except Exception:
            pass

        # Practice Assessment Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_tests (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                session_id TEXT,
                code_hash TEXT NOT NULL,
                questions_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_evaluations (
                id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                user_id TEXT,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                score_percentage REAL NOT NULL,
                evaluations_json TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES practice_tests (id) ON DELETE CASCADE
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_practice_tests_session ON practice_tests (session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_practice_evals_test ON practice_evaluations (test_id);")

        # Migration: enhance sessions and code_versions for VS Code File Explorer model
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN filename TEXT;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN language TEXT;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN is_runnable INTEGER DEFAULT 1;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE code_versions ADD COLUMN execution_result_json TEXT;")
        except Exception:
            pass

        # Perform one-time migration for legacy records
        RUNNABLE_LANGS = {
            "python", "py", "javascript", "js", "typescript", "ts",
            "java", "c", "cpp", "c++", "csharp", "cs", "go", "rust",
            "rs", "php", "ruby", "rb", "kotlin", "kt", "swift", "bash", "sh"
        }
        DEFAULT_FILENAMES = {
            "python": "main.py", "javascript": "app.js", "typescript": "index.ts",
            "java": "Main.java", "cpp": "main.cpp", "c": "main.c", "csharp": "Program.cs",
            "go": "main.go", "rust": "main.rs", "php": "index.php", "ruby": "app.rb",
            "kotlin": "Main.kt", "swift": "main.swift", "bash": "script.sh",
            "html": "index.html", "css": "styles.css", "scss": "styles.scss",
            "sql": "query.sql", "json": "data.json", "yaml": "config.yaml",
            "xml": "data.xml", "markdown": "README.md", "toml": "config.toml",
            "dockerfile": "Dockerfile"
        }

        cursor.execute("SELECT id, title, filename, language FROM sessions WHERE filename IS NULL OR filename = '';")
        legacy_rows = cursor.fetchall()
        for s in legacy_rows:
            sid = s["id"]
            title = s["title"] or ""
            # Get latest version for this session
            cursor.execute(
                "SELECT language, filename FROM code_versions WHERE session_id = ? ORDER BY version_number DESC LIMIT 1;",
                (sid,)
            )
            v_row = cursor.fetchone()
            v_lang = (v_row["language"] if v_row and v_row["language"] else "python").lower()
            v_fn = v_row["filename"] if v_row and v_row["filename"] else None

            is_runnable = 1 if v_lang in RUNNABLE_LANGS else 0

            # Derive clean filename
            clean_fn = None
            if v_fn and "." in v_fn and len(v_fn) > 2:
                clean_fn = v_fn
            elif "." in title and not title.startswith("SQL Query") and not title.startswith("Python:"):
                clean_fn = title
            elif "Dockerfile" in title:
                clean_fn = "Dockerfile"
                v_lang = "dockerfile"
                is_runnable = 0
            elif "SQL" in title or v_lang == "sql":
                clean_fn = "query.sql"
                v_lang = "sql"
                is_runnable = 0
            elif "HTML" in title or v_lang == "html":
                clean_fn = "index.html"
                v_lang = "html"
                is_runnable = 0
            elif "CSS" in title or v_lang in {"css", "scss"}:
                clean_fn = "styles.css"
                is_runnable = 0
            elif "JSON" in title or v_lang == "json":
                clean_fn = "data.json"
                is_runnable = 0
            else:
                clean_fn = DEFAULT_FILENAMES.get(v_lang, f"file.{v_lang}")

            cursor.execute(
                "UPDATE sessions SET filename = ?, language = ?, is_runnable = ? WHERE id = ?;",
                (clean_fn, v_lang, is_runnable, sid)
            )

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                code_version_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (code_version_id) REFERENCES code_versions (id) ON DELETE SET NULL
            );
        """)

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                recovery_key_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # User authentication sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # Migration: ensure user_id exists on sessions
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT;")
        except Exception:
            pass

        # Indexes for fast lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions (updated_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_session ON code_versions (session_id, version_number ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_version ON analyses (code_version_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, created_at ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions (token, expires_at);")

        # Automatically seed the Demo Account if it does not already exist
        DEMO_EMAIL = "demo@codewise.dev"
        DEMO_PASSWORD = "DemoUser2026!"
        DEMO_RECOVERY_KEY = "CW-DEMO-2026-RECOVER"
        DEMO_USER_ID = "demo-user-0000-0000-000000000001"

        cursor.execute("SELECT id FROM users WHERE lower(email) = ?;", (DEMO_EMAIL.lower(),))
        demo_row = cursor.fetchone()
        if not demo_row:
            from .auth import hash_password, hash_recovery_key
            demo_pw_hash = hash_password(DEMO_PASSWORD)
            demo_rec_hash = hash_recovery_key(DEMO_RECOVERY_KEY)
            now_ts = get_iso_now()
            cursor.execute("""
                INSERT INTO users (id, name, email, password_hash, recovery_key_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (DEMO_USER_ID, "Demo Developer", DEMO_EMAIL, demo_pw_hash, demo_rec_hash, now_ts, now_ts))
            demo_id = DEMO_USER_ID
        else:
            demo_id = demo_row["id"]

        # Ensure existing legacy sessions without a user_id belong to demo user so no user data is lost
        cursor.execute("UPDATE sessions SET user_id = ? WHERE user_id IS NULL OR user_id = '';", (demo_id,))

def deduplicate_sessions() -> int:
    """
    Safely consolidates duplicate sessions by filename.
    Preserves all distinct code revisions, analyses, and chat messages.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename, COUNT(*) as cnt 
            FROM sessions 
            WHERE filename IS NOT NULL AND filename != '' 
            GROUP BY filename 
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        consolidated_count = 0

        for dup in duplicates:
            fname = dup["filename"]
            cursor.execute("SELECT * FROM sessions WHERE filename = ? ORDER BY created_at ASC", (fname,))
            all_sess = cursor.fetchall()
            if not all_sess or len(all_sess) <= 1:
                continue

            best_sess = None
            best_score = -1
            for s in all_sess:
                cursor.execute("SELECT COUNT(*) as v_cnt FROM code_versions WHERE session_id = ?", (s["id"],))
                v_cnt = cursor.fetchone()["v_cnt"]
                cursor.execute("SELECT COUNT(*) as m_cnt FROM messages WHERE session_id = ?", (s["id"],))
                m_cnt = cursor.fetchone()["m_cnt"]
                score = (m_cnt * 10) + v_cnt
                if score > best_score:
                    best_score = score
                    best_sess = s

            primary_id = best_sess["id"]

            cursor.execute("SELECT code, version_number FROM code_versions WHERE session_id = ? ORDER BY version_number ASC", (primary_id,))
            primary_versions = cursor.fetchall()
            existing_codes = {v["code"]: v["version_number"] for v in primary_versions}
            max_v = max([v["version_number"] for v in primary_versions], default=0)

            for s in all_sess:
                if s["id"] == primary_id:
                    continue

                cursor.execute("SELECT * FROM code_versions WHERE session_id = ? ORDER BY version_number ASC", (s["id"],))
                dup_versions = cursor.fetchall()

                for dv in dup_versions:
                    if dv["code"] not in existing_codes:
                        max_v += 1
                        existing_codes[dv["code"]] = max_v
                        cursor.execute(
                            "UPDATE code_versions SET session_id = ?, version_number = ? WHERE id = ?",
                            (primary_id, max_v, dv["id"])
                        )
                    else:
                        target_v_num = existing_codes[dv["code"]]
                        cursor.execute(
                            "SELECT id FROM code_versions WHERE session_id = ? AND version_number = ?",
                            (primary_id, target_v_num)
                        )
                        target_v = cursor.fetchone()
                        if target_v:
                            cursor.execute("SELECT id FROM analyses WHERE code_version_id = ?", (target_v["id"],))
                            prim_a = cursor.fetchone()
                            if not prim_a:
                                cursor.execute("UPDATE analyses SET code_version_id = ? WHERE code_version_id = ?", (target_v["id"], dv["id"]))

                cursor.execute("UPDATE messages SET session_id = ? WHERE session_id = ?", (primary_id, s["id"]))
                cursor.execute("DELETE FROM sessions WHERE id = ?", (s["id"],))
                consolidated_count += 1

        return consolidated_count
