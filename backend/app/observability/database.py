import os
import sqlite3
from pathlib import Path


# Store the observability database in the backend directory.
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "observability.db"

DB_PATH = Path(
    os.getenv("OBSERVABILITY_DB_PATH", str(DEFAULT_DB_PATH))
).resolve()


def get_connection() -> sqlite3.Connection:
    """Create a configured SQLite connection."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        str(DB_PATH),
        timeout=10,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    # Improve reliability for concurrent reads and writes.
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")

    return connection


def init_observability_db() -> None:
    """Create the observability database and its initial tables."""

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS application_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                level TEXT NOT NULL DEFAULT 'INFO',
                service TEXT NOT NULL DEFAULT 'retail-promotion-backend',
                environment TEXT NOT NULL DEFAULT 'development',
                request_id TEXT,
                trace_id TEXT,
                session_id TEXT,
                user_id TEXT,
                conversation_id TEXT,
                agent_run_id TEXT,
                agent_name TEXT,
                tool_name TEXT,
                model_name TEXT,
                endpoint TEXT,
                message TEXT NOT NULL,
                latency_ms REAL,
                status TEXT,
                error_type TEXT,
                details_json TEXT
            );

            CREATE TABLE IF NOT EXISTS request_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                request_id TEXT NOT NULL,
                trace_id TEXT,
                session_id TEXT,
                endpoint TEXT,
                method TEXT,
                status_code INTEGER,
                status TEXT,
                latency_ms REAL,
                environment TEXT DEFAULT 'development',
                error_type TEXT
            );

            CREATE TABLE IF NOT EXISTS llm_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                request_id TEXT,
                trace_id TEXT,
                session_id TEXT,
                agent_run_id TEXT,
                agent_name TEXT,
                provider TEXT,
                model_name TEXT,
                prompt_version TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cached_tokens INTEGER DEFAULT 0,
                reasoning_tokens INTEGER DEFAULT 0,
                latency_ms REAL,
                time_to_first_token_ms REAL,
                tokens_per_second REAL,
                retry_count INTEGER DEFAULT 0,
                status TEXT,
                error_type TEXT,
                estimated_cost REAL DEFAULT 0,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS agent_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_run_id TEXT NOT NULL,
                request_id TEXT,
                trace_id TEXT,
                session_id TEXT,
                agent_name TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                duration_ms REAL,
                status TEXT,
                step_count INTEGER DEFAULT 0,
                llm_call_count INTEGER DEFAULT 0,
                tool_call_count INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                human_approval_required INTEGER DEFAULT 0,
                human_approval_duration_ms REAL,
                error_type TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS tool_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                request_id TEXT,
                trace_id TEXT,
                agent_run_id TEXT,
                agent_name TEXT,
                tool_name TEXT NOT NULL,
                tool_type TEXT,
                input_json TEXT,
                output_json TEXT,
                start_time TEXT,
                end_time TEXT,
                latency_ms REAL,
                status TEXT,
                retry_count INTEGER DEFAULT 0,
                error_type TEXT
            );

            CREATE TABLE IF NOT EXISTS rag_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                request_id TEXT,
                trace_id TEXT,
                query TEXT,
                rewritten_query TEXT,
                documents_retrieved INTEGER DEFAULT 0,
                top_k INTEGER,
                retrieval_latency_ms REAL,
                vector_search_latency_ms REAL,
                context_size INTEGER,
                context_tokens INTEGER,
                top_similarity_score REAL,
                average_similarity_score REAL,
                source_documents_json TEXT,
                status TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                request_id TEXT,
                session_id TEXT,
                user_id TEXT,
                conversation_id TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_ms REAL,
                status TEXT,
                root_span_id TEXT,
                environment TEXT DEFAULT 'development',
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                parent_span_id TEXT,
                span_name TEXT NOT NULL,
                span_type TEXT,
                service_name TEXT,
                agent_name TEXT,
                model_name TEXT,
                tool_name TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_ms REAL,
                status TEXT,
                input_json TEXT,
                output_json TEXT,
                error TEXT,
                metadata_json TEXT,
                FOREIGN KEY (trace_id)
                    REFERENCES traces(trace_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS human_approval_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                workflow_id TEXT,
                request_id TEXT,
                trace_id TEXT,
                promotion_id TEXT,
                reviewer TEXT,
                decision TEXT,
                status TEXT,
                escalation_reason TEXT,
                duration_ms REAL,
                comment TEXT
            );

            CREATE TABLE IF NOT EXISTS guardrail_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                guardrail_name TEXT NOT NULL,
                guardrail_type TEXT,
                request_id TEXT,
                trace_id TEXT,
                decision TEXT,
                reason TEXT,
                severity TEXT,
                action_taken TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                event_type TEXT NOT NULL,
                severity TEXT,
                request_id TEXT,
                trace_id TEXT,
                description TEXT,
                action_taken TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS error_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                request_id TEXT,
                trace_id TEXT,
                endpoint TEXT,
                service TEXT,
                agent_name TEXT,
                tool_name TEXT,
                error_type TEXT,
                message TEXT,
                stack_trace TEXT,
                status TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS cost_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                request_id TEXT,
                trace_id TEXT,
                session_id TEXT,
                agent_name TEXT,
                model_name TEXT,
                provider TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                pricing_version TEXT
            );

            CREATE TABLE IF NOT EXISTS drift_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                drift_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                feature_name TEXT,
                baseline_value REAL,
                current_value REAL,
                drift_score REAL,
                status TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                alert_name TEXT NOT NULL,
                metric_name TEXT,
                threshold REAL,
                observed_value REAL,
                severity TEXT,
                status TEXT DEFAULT 'NORMAL',
                message TEXT,
                resolved_at TEXT
            );

            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                cpu_percent REAL,
                memory_percent REAL,
                process_memory_mb REAL,
                process_cpu_percent REAL,
                disk_usage_percent REAL,
                database_size_bytes INTEGER,
                active_connections INTEGER,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS token_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                ),
                request_id TEXT,
                trace_id TEXT,
                agent_run_id TEXT,
                model_name TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cached_tokens INTEGER DEFAULT 0,
                reasoning_tokens INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_logs_timestamp
                ON application_logs(timestamp);

            CREATE INDEX IF NOT EXISTS idx_logs_request
                ON application_logs(request_id);

            CREATE INDEX IF NOT EXISTS idx_logs_trace
                ON application_logs(trace_id);

            CREATE INDEX IF NOT EXISTS idx_logs_level
                ON application_logs(level);

            CREATE INDEX IF NOT EXISTS idx_requests_timestamp
                ON request_metrics(timestamp);

            CREATE INDEX IF NOT EXISTS idx_requests_trace
                ON request_metrics(trace_id);

            CREATE INDEX IF NOT EXISTS idx_llm_timestamp
                ON llm_metrics(timestamp);

            CREATE INDEX IF NOT EXISTS idx_agents_run
                ON agent_metrics(agent_run_id);

            CREATE INDEX IF NOT EXISTS idx_tools_timestamp
                ON tool_metrics(timestamp);

            CREATE INDEX IF NOT EXISTS idx_rag_timestamp
                ON rag_metrics(timestamp);

            CREATE INDEX IF NOT EXISTS idx_traces_request
                ON traces(request_id);

            CREATE INDEX IF NOT EXISTS idx_spans_trace
                ON spans(trace_id);

            CREATE INDEX IF NOT EXISTS idx_spans_parent
                ON spans(parent_span_id);

            CREATE INDEX IF NOT EXISTS idx_approval_trace
                ON human_approval_events(trace_id);

            CREATE INDEX IF NOT EXISTS idx_errors_timestamp
                ON error_events(timestamp);

            CREATE INDEX IF NOT EXISTS idx_drift_timestamp
                ON drift_observations(timestamp);
            """
        )


if __name__ == "__main__":
    init_observability_db()
    print(f"Observability database initialized: {DB_PATH}")
