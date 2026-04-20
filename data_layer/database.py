import sqlite3
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# DB path: stored under ~/.cpse/telemetry.db
#
# The workspace folder (mnt/) is a FUSE mount of the user's local filesystem.
# Most FUSE drivers don't support the fcntl file-locking that SQLite requires,
# so we store the DB in the session home directory instead — a real filesystem
# that supports all SQLite operations.  Data persists across Streamlit restarts.
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.expanduser("~"), ".cpse", "telemetry.db")


class LocalDatabaseManager:
    """
    SQLite-backed persistence layer.

    Drop-in replacement for the old SupabaseManager — identical public
    interface so the rest of the codebase (app.py, main.py) requires no
    changes to how the DB is called.

    The database file is created automatically on first use.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema()
        print(f"DEBUG: SQLite database ready → {self.db_path}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row          # rows behave like dicts
        return conn

    def _init_schema(self):
        """Create the table and indexes if they don't exist yet."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS crowd_telemetry (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    location_name TEXT    NOT NULL,
                    latitude      REAL    NOT NULL DEFAULT 0,
                    longitude     REAL    NOT NULL DEFAULT 0,
                    congestion    REAL    NOT NULL DEFAULT 0,
                    speed         REAL,
                    gradient      REAL,
                    velocity_var  REAL,
                    anomaly_score REAL,
                    state         TEXT    NOT NULL DEFAULT 'Unknown',
                    session_id    TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_location   ON crowd_telemetry(location_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_at ON crowd_telemetry(created_at)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Public interface  (mirrors SupabaseManager exactly)
    # ------------------------------------------------------------------

    def insert_telemetry(self, data: dict):
        """Insert one telemetry record."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO crowd_telemetry
                        (location_name, latitude, longitude, congestion, speed,
                         gradient, velocity_var, anomaly_score, state, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data.get("location_name", "Unknown"),
                        data.get("lat",           0.0),
                        data.get("lon",           0.0),
                        data.get("congestion",    0.0),
                        data.get("speed",         0.0),
                        data.get("gradient",      0.0),
                        data.get("velocity_var",  0.0),
                        data.get("anomaly_score", 0.0),
                        data.get("state",         "Unknown"),
                        datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    ),
                )
                conn.commit()
        except Exception as e:
            print(f"ERROR: SQLite insert failed: {e}")

    def fetch_history(self, location_name: str, limit: int = 50) -> list:
        """Fetch recent records for a specific location (chronological order)."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM crowd_telemetry
                    WHERE  location_name = ?
                    ORDER  BY created_at DESC
                    LIMIT  ?
                    """,
                    (location_name, limit),
                ).fetchall()
                data = [dict(r) for r in rows]
                return data[::-1]           # flip to chronological
        except Exception as e:
            print(f"ERROR: SQLite fetch_history failed: {e}")
            return []

    def fetch_recent_logs(self, limit: int = 100) -> list:
        """Fetch the most-recent global logs (no location filter)."""
        return self.fetch_filtered_logs(limit=limit)

    def fetch_filtered_logs(
        self,
        limit: int = 100,
        location: str = None,
        anomaly_only: bool = False,
    ) -> list:
        """Fetch logs with optional location and anomaly filters."""
        try:
            conditions = []
            params: list = []

            if location and location != "All":
                conditions.append("location_name = ?")
                params.append(location)

            if anomaly_only:
                conditions.append("anomaly_score > 2.5")

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            query = f"""
                SELECT * FROM crowd_telemetry
                {where}
                ORDER BY created_at DESC
                LIMIT ?
            """
            params.append(limit)

            with self._get_conn() as conn:
                rows = conn.execute(query, params).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"ERROR: SQLite fetch_filtered_logs failed: {e}")
            return []

    def fetch_unique_locations(self) -> list:
        """Return a sorted list of distinct location names."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT location_name FROM crowd_telemetry ORDER BY location_name"
                ).fetchall()
                return [r["location_name"] for r in rows]
        except Exception as e:
            print(f"ERROR: SQLite fetch_unique_locations failed: {e}")
            return []


# ---------------------------------------------------------------------------
# Backwards-compatibility alias (nothing outside this file imports the class
# by name, but keep it in case tests reference it)
# ---------------------------------------------------------------------------
SupabaseManager = LocalDatabaseManager


# Factory — used by app.py:  from data_layer.database import get_db_client
def get_db_client() -> LocalDatabaseManager:
    return LocalDatabaseManager()
