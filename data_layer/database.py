"""
data_layer/database.py
PostgreSQL persistence layer backed by Neon DB.

Features
--------
* Auto-creates the `crowd_telemetry` table on first connection.
* Detects columns that are missing from an existing table and adds them
  non-destructively via ALTER TABLE (schema migration without data loss).
* Password resolved from Streamlit secrets → os.environ → raises clear error.
* `connected` property lets app.py surface a live status badge.
* Falls back silently (logs a warning, disables persistence) if the DB is
  unreachable — the rest of the app continues to function.
* Identical public interface to the previous SQLite manager so no other
  file requires changes.
"""

import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)

# ── Connection parameters ────────────────────────────────────────────────────
# Use the pooler endpoint for all application traffic; it multiplexes many
# short-lived Streamlit connections onto a handful of persistent Postgres
# connections, keeping Neon's "compute" awake and reducing cold-start latency.
_POOLER_HOST = "ep-aged-cherry-aoxn5nod-pooler.c-2.ap-southeast-1.aws.neon.tech"
_DIRECT_HOST = "ep-aged-cherry-aoxn5nod.c-2.ap-southeast-1.aws.neon.tech"
_DATABASE    = "neondb"
_ROLE        = "neondb_owner"
_PORT        = 5432

# ── Target schema ────────────────────────────────────────────────────────────
# Full column list. The auto-migration loop adds any column here that is absent
# from the live table, so new columns can be introduced just by extending this dict.
_TABLE = "crowd_telemetry"

_SCHEMA_COLUMNS: dict[str, str] = {
    # name            postgres type + constraints
    "speed":          "DOUBLE PRECISION",
    "gradient":       "DOUBLE PRECISION",
    "velocity_var":   "DOUBLE PRECISION",
    "anomaly_score":  "DOUBLE PRECISION",
    "risk_score":     "DOUBLE PRECISION",
    "session_id":     "TEXT",
}

# ── Streamlit import (optional — only available when running inside st) ───────
try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    _HAS_ST = False


# ─────────────────────────────────────────────────────────────────────────────
class NeonDatabaseManager:
    """
    Neon-backed PostgreSQL manager with auto schema bootstrap and migration.

    Public methods
    --------------
    insert_telemetry(data)          — write one telemetry record
    fetch_history(location, limit)  — chronological history for a location
    fetch_recent_logs(limit)        — latest N rows globally
    fetch_filtered_logs(...)        — query with location / anomaly filters
    fetch_unique_locations()        — distinct location names

    Properties
    ----------
    connected : bool   — True when the DB is reachable and schema is ready
    status_label : str — human-readable connection status for the UI
    """

    def __init__(self):
        self._dsn: Optional[str] = None
        self._connected: bool = False
        self._status: str = "Not initialised"

        # Resolve password
        password = self._resolve_password()
        if not password:
            self._status = "NEON_PASS not set — persistence disabled"
            log.warning(self._status)
            return

        self._dsn = (
            f"host={_POOLER_HOST} "
            f"port={_PORT} "
            f"dbname={_DATABASE} "
            f"user={_ROLE} "
            f"password={password} "
            f"sslmode=require "
            f"connect_timeout=10"
        )

        # Bootstrap schema
        try:
            self._bootstrap_schema()
            self._connected = True
            self._status = f"Connected — {_DATABASE}@{_POOLER_HOST.split('.')[0]}"
            log.info(f"Neon DB ready: {self._status}")
        except Exception as exc:
            self._connected = False
            self._status = f"Connection failed: {exc}"
            log.error(f"Neon DB bootstrap error: {exc}")

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def status_label(self) -> str:
        return self._status

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _resolve_password() -> Optional[str]:
        """Check Streamlit secrets then os.environ for NEON_PASS."""
        if _HAS_ST:
            try:
                pw = st.secrets.get("NEON_PASS")
                if pw:
                    return pw
            except Exception:
                pass
        return os.getenv("NEON_PASS")

    @contextmanager
    def _cursor(self, dict_cursor: bool = False):
        """
        Context manager that opens a connection, yields a cursor, commits on
        clean exit and rolls back + closes on exception.
        """
        factory = RealDictCursor if dict_cursor else None
        conn = psycopg2.connect(self._dsn)
        try:
            cur = conn.cursor(cursor_factory=factory) if factory else conn.cursor()
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _bootstrap_schema(self):
        """
        Step 1 — CREATE TABLE IF NOT EXISTS with full baseline schema.
        Step 2 — Introspect information_schema; ALTER TABLE for any column
                 that exists in _SCHEMA_COLUMNS but not yet in the live table.
        Step 3 — CREATE INDEX IF NOT EXISTS for the two common query patterns.
        """
        with self._cursor() as cur:

            # ── 1. Create base table ─────────────────────────────────────
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    id            SERIAL          PRIMARY KEY,
                    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
                    location_name TEXT            NOT NULL,
                    latitude      DOUBLE PRECISION NOT NULL DEFAULT 0,
                    longitude     DOUBLE PRECISION NOT NULL DEFAULT 0,
                    congestion    DOUBLE PRECISION NOT NULL DEFAULT 0,
                    speed         DOUBLE PRECISION,
                    gradient      DOUBLE PRECISION,
                    velocity_var  DOUBLE PRECISION,
                    anomaly_score DOUBLE PRECISION,
                    risk_score    DOUBLE PRECISION,
                    state         TEXT            NOT NULL DEFAULT 'Unknown',
                    session_id    TEXT
                )
            """)

            # ── 2. Schema migration — add missing columns ─────────────────
            cur.execute("""
                SELECT column_name
                FROM   information_schema.columns
                WHERE  table_schema = 'public'
                  AND  table_name   = %s
            """, (_TABLE,))
            existing_cols = {row[0] for row in cur.fetchall()}

            for col_name, col_type in _SCHEMA_COLUMNS.items():
                if col_name not in existing_cols:
                    cur.execute(
                        f"ALTER TABLE {_TABLE} "
                        f"ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                    )
                    log.info(f"Schema migration: added column '{col_name}' ({col_type})")

            # ── 3. Indexes ────────────────────────────────────────────────
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{_TABLE}_location
                ON {_TABLE} (location_name)
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{_TABLE}_created_at
                ON {_TABLE} (created_at DESC)
            """)

    # ── Public interface ─────────────────────────────────────────────────────

    def insert_telemetry(self, data: dict):
        """Persist one telemetry snapshot. Silently skips if not connected."""
        if not self._connected:
            return
        try:
            with self._cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {_TABLE}
                        (location_name, latitude, longitude,
                         congestion, speed, gradient,
                         velocity_var, anomaly_score, risk_score,
                         state, created_at)
                    VALUES
                        (%s, %s, %s,
                         %s, %s, %s,
                         %s, %s, %s,
                         %s, %s)
                """, (
                    data.get("location_name", "Unknown"),
                    data.get("lat",           0.0),
                    data.get("lon",           0.0),
                    data.get("congestion",    0.0),
                    data.get("speed",         0.0),
                    data.get("gradient",      0.0),
                    data.get("velocity_var",  0.0),
                    data.get("anomaly_score", 0.0),
                    data.get("risk_score",    0.0),
                    data.get("state",         "Unknown"),
                    datetime.now(timezone.utc),
                ))
        except Exception as exc:
            log.error(f"insert_telemetry failed: {exc}")
            self._connected = False          # flag degraded state
            self._status    = f"Write error: {exc}"

    def fetch_history(self, location_name: str, limit: int = 50) -> list:
        """Return up to `limit` rows for a location in ascending time order."""
        if not self._connected:
            return []
        try:
            with self._cursor(dict_cursor=True) as cur:
                cur.execute(f"""
                    SELECT * FROM (
                        SELECT * FROM {_TABLE}
                        WHERE  location_name = %s
                        ORDER  BY created_at DESC
                        LIMIT  %s
                    ) sub
                    ORDER BY created_at ASC
                """, (location_name, limit))
                return [dict(r) for r in cur.fetchall()]
        except Exception as exc:
            log.error(f"fetch_history failed: {exc}")
            return []

    def fetch_recent_logs(self, limit: int = 100) -> list:
        """Return the most recent `limit` rows globally."""
        return self.fetch_filtered_logs(limit=limit)

    def fetch_filtered_logs(
        self,
        limit: int = 100,
        location: Optional[str] = None,
        anomaly_only: bool = False,
    ) -> list:
        """Query with optional location filter and anomaly-score threshold."""
        if not self._connected:
            return []
        try:
            conditions: list[str] = []
            params:     list      = []

            if location and location != "All":
                conditions.append("location_name = %s")
                params.append(location)
            if anomaly_only:
                conditions.append("anomaly_score > 2.5")

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            params.append(limit)

            with self._cursor(dict_cursor=True) as cur:
                cur.execute(
                    f"SELECT * FROM {_TABLE} {where} "
                    f"ORDER BY created_at DESC LIMIT %s",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as exc:
            log.error(f"fetch_filtered_logs failed: {exc}")
            return []

    def fetch_unique_locations(self) -> list:
        """Return a sorted list of distinct location names."""
        if not self._connected:
            return []
        try:
            with self._cursor() as cur:
                cur.execute(
                    f"SELECT DISTINCT location_name FROM {_TABLE} "
                    f"ORDER BY location_name"
                )
                return [row[0] for row in cur.fetchall()]
        except Exception as exc:
            log.error(f"fetch_unique_locations failed: {exc}")
            return []


# ── Compatibility aliases ────────────────────────────────────────────────────
LocalDatabaseManager = NeonDatabaseManager
SupabaseManager      = NeonDatabaseManager


def get_db_client() -> NeonDatabaseManager:
    """Factory used by app.py and main.py."""
    return NeonDatabaseManager()
