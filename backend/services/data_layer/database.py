"""
data_layer/database.py
PostgreSQL persistence via Supabase. Reads SUPABASE_DB_URL from environment.
"""
import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)

_TABLE = "crowd_telemetry"

_SCHEMA_COLUMNS: dict[str, str] = {
    "speed":         "DOUBLE PRECISION",
    "gradient":      "DOUBLE PRECISION",
    "velocity_var":  "DOUBLE PRECISION",
    "anomaly_score": "DOUBLE PRECISION",
    "risk_score":    "DOUBLE PRECISION",
    "session_id":    "TEXT",
}


class SupabaseDatabaseManager:
    def __init__(self):
        self._dsn: Optional[str] = None
        self._connected: bool = False
        self._status: str = "Not initialised"

        dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_POOLER_URL")
        if not dsn:
            self._status = "SUPABASE_DB_URL not set — persistence disabled"
            log.warning(self._status)
            return

        self._dsn = dsn
        try:
            self._bootstrap_schema()
            self._connected = True
            self._status = "Connected — Supabase PostgreSQL"
        except Exception as exc:
            self._connected = False
            self._status = f"Connection failed: {exc}"
            log.error(f"Supabase bootstrap error: {exc}")

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def status_label(self) -> str:
        return self._status

    @contextmanager
    def _cursor(self, dict_cursor: bool = False):
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
        with self._cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    id            SERIAL           PRIMARY KEY,
                    created_at    TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
                    location_name TEXT             NOT NULL,
                    latitude      DOUBLE PRECISION NOT NULL DEFAULT 0,
                    longitude     DOUBLE PRECISION NOT NULL DEFAULT 0,
                    congestion    DOUBLE PRECISION NOT NULL DEFAULT 0,
                    speed         DOUBLE PRECISION,
                    gradient      DOUBLE PRECISION,
                    velocity_var  DOUBLE PRECISION,
                    anomaly_score DOUBLE PRECISION,
                    risk_score    DOUBLE PRECISION,
                    state         TEXT             NOT NULL DEFAULT 'Unknown',
                    session_id    TEXT
                )
            """)
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """, (_TABLE,))
            existing = {row[0] for row in cur.fetchall()}
            for col, typ in _SCHEMA_COLUMNS.items():
                if col not in existing:
                    cur.execute(
                        f"ALTER TABLE {_TABLE} ADD COLUMN IF NOT EXISTS {col} {typ}"
                    )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_location "
                f"ON {_TABLE} (location_name)"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_created_at "
                f"ON {_TABLE} (created_at DESC)"
            )

    def insert_telemetry(self, data: dict):
        if not self._connected:
            return
        try:
            with self._cursor() as cur:
                cur.execute(
                    f"""INSERT INTO {_TABLE}
                        (location_name, latitude, longitude, congestion, speed,
                         gradient, velocity_var, anomaly_score, risk_score,
                         state, created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        data.get("location_name", "Unknown"),
                        data.get("lat", 0.0),
                        data.get("lon", 0.0),
                        data.get("congestion", 0.0),
                        data.get("speed", 0.0),
                        data.get("gradient", 0.0),
                        data.get("velocity_var", 0.0),
                        data.get("anomaly_score", 0.0),
                        data.get("risk_score", 0.0),
                        data.get("state", "Unknown"),
                        datetime.now(timezone.utc),
                    ),
                )
        except Exception as exc:
            log.error(f"insert_telemetry failed: {exc}")
            self._connected = False
            self._status = f"Write error: {exc}"

    def fetch_filtered_logs(
        self,
        limit: int = 100,
        location: Optional[str] = None,
        anomaly_only: bool = False,
    ) -> list:
        if not self._connected:
            return []
        try:
            conditions, params = [], []
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


# Backward-compat alias
NeonDatabaseManager = SupabaseDatabaseManager


def get_db_client() -> SupabaseDatabaseManager:
    return SupabaseDatabaseManager()
