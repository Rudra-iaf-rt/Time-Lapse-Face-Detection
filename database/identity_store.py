"""
Identity Store
--------------
Persistent SQLite storage for multi-camera person tracking.

Compatible with:
    - pipeline.py
    - dashboard/app.py

Features:
    - Global person IDs
    - Embedding storage and matching
    - Sightings
    - Lost / Active / Resolved lifecycle
    - Reappearance events
    - Dashboard search
    - Notes
    - Event history
    - Safe database migration
"""

import json
import sqlite3
import threading
import time
import uuid
from typing import Optional, List, Dict, Tuple, Any

import numpy as np


class IdentityStore:
    """
    SQLite-backed persistent identity store.

    IMPORTANT:
        Track ID != Global Identity ID.

        Example:
            Camera 1 track: CAM01-T17
            Camera 2 track: CAM02-T08

        Both may belong to:
            PERSON_000001
    """

    def __init__(
        self,
        db_path: str = "database/identities.db",
        similarity_threshold: float = 0.70,
        lost_timeout: float = 30.0,
        lost_threshold_secs: Optional[float] = None
    ):
        self.db_path = db_path
        self.similarity_threshold = similarity_threshold
        # Support both the old/new parameter names.
        # dashboard/app.py currently uses lost_threshold_secs.
        if lost_threshold_secs is not None:
            self.lost_timeout = float(lost_threshold_secs)
        else:
            self.lost_timeout = float(lost_timeout)
        self._lock = threading.RLock()

        self._init_db()

    # ============================================================
    # DATABASE
    # ============================================================

    def _connect(self):
        """Create a SQLite connection."""

        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False,
        )

        conn.row_factory = sqlite3.Row

        # Better concurrent read/write behaviour.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        return conn

    def _init_db(self):
        """Create or migrate database schema safely."""

        with self._lock:
            conn = self._connect()

            try:
                # ------------------------------------------------
                # Main identities table
                # ------------------------------------------------

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS identities (
                        global_id TEXT PRIMARY KEY,
                        embedding BLOB NOT NULL,
                        status TEXT DEFAULT 'ACTIVE',
                        first_seen REAL,
                        last_seen REAL,
                        last_camera INTEGER,
                        last_frame INTEGER
                    )
                    """
                )

                # ------------------------------------------------
                # Sightings table
                # ------------------------------------------------

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sightings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        global_id TEXT NOT NULL,
                        camera_id INTEGER NOT NULL,
                        frame_idx INTEGER,
                        timestamp REAL,
                        bbox TEXT,
                        confidence REAL,
                        crop_path TEXT
                    )
                    """
                )

                # ------------------------------------------------
                # Events table
                # ------------------------------------------------

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        global_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        camera_id INTEGER,
                        occurred_at REAL NOT NULL,
                        detail TEXT
                    )
                    """
                )

                # ------------------------------------------------
                # Check existing identity columns
                # ------------------------------------------------

                identity_columns = self._get_columns(
                    conn,
                    "identities",
                )

                # These columns are required by dashboard.
                migrations = {
                    "notes": "TEXT",
                    "resolved_at": "REAL",
                    "best_crop_path": "TEXT",
                }

                for column, column_type in migrations.items():
                    if column not in identity_columns:
                        conn.execute(
                            f"""
                            ALTER TABLE identities
                            ADD COLUMN {column} {column_type}
                            """
                        )

                # ------------------------------------------------
                # Useful indexes
                # ------------------------------------------------

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_sightings_global_id
                    ON sightings(global_id)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_sightings_timestamp
                    ON sightings(timestamp)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_sightings_camera
                    ON sightings(camera_id)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_events_global_id
                    ON events(global_id)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_events_type
                    ON events(event_type)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_events_time
                    ON events(occurred_at)
                    """
                )

                conn.commit()

            finally:
                conn.close()

    @staticmethod
    def _get_columns(conn, table_name: str) -> set:
        """Return column names for a SQLite table."""

        rows = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        return {row["name"] for row in rows}

    # ============================================================
    # EMBEDDINGS
    # ============================================================

    @staticmethod
    def _serialize_embedding(embedding: np.ndarray) -> bytes:
        """Convert embedding into SQLite-compatible bytes."""

        arr = np.asarray(
            embedding,
            dtype=np.float32,
        ).reshape(-1)

        return arr.tobytes()

    @staticmethod
    def _deserialize_embedding(blob: bytes) -> np.ndarray:
        """Convert SQLite bytes back into embedding."""

        if blob is None:
            return np.array([], dtype=np.float32)

        return np.frombuffer(
            blob,
            dtype=np.float32,
        ).copy()

    @staticmethod
    def _normalize_embedding(
        embedding: np.ndarray,
    ) -> np.ndarray:
        """L2-normalize an embedding."""

        arr = np.asarray(
            embedding,
            dtype=np.float32,
        ).reshape(-1)

        norm = np.linalg.norm(arr)

        if norm < 1e-12:
            return arr

        return arr / norm

    @staticmethod
    def _cosine_similarity(
        a: np.ndarray,
        b: np.ndarray,
    ) -> float:
        """Calculate cosine similarity."""

        a = np.asarray(a, dtype=np.float32).reshape(-1)
        b = np.asarray(b, dtype=np.float32).reshape(-1)

        if a.size == 0 or b.size == 0:
            return 0.0

        if a.shape != b.shape:
            return 0.0

        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)

        if a_norm < 1e-12 or b_norm < 1e-12:
            return 0.0

        return float(
            np.dot(a, b) / (a_norm * b_norm)
        )

    # ============================================================
    # IDS
    # ============================================================

    def _new_global_id(self) -> str:
        """Generate a new global person identity."""

        conn = self._connect()

        try:
            while True:
                global_id = (
                    f"PERSON_{uuid.uuid4().hex[:8].upper()}"
                )

                exists = conn.execute(
                    """
                    SELECT 1
                    FROM identities
                    WHERE global_id = ?
                    LIMIT 1
                    """,
                    (global_id,),
                ).fetchone()

                if not exists:
                    return global_id

        finally:
            conn.close()

    # ============================================================
    # EVENTS
    # ============================================================

    def _add_event(
        self,
        conn,
        global_id: str,
        event_type: str,
        camera_id: Optional[int] = None,
        detail: Optional[str] = None,
        occurred_at: Optional[float] = None,
    ):
        """Insert an event."""

        if occurred_at is None:
            occurred_at = time.time()

        conn.execute(
            """
            INSERT INTO events (
                global_id,
                event_type,
                camera_id,
                occurred_at,
                detail
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                global_id,
                event_type,
                camera_id,
                occurred_at,
                detail,
            ),
        )

    # ============================================================
    # MATCH / CREATE
    # ============================================================

    def match_or_create(
        self,
        embedding: np.ndarray,
        camera_id: int,
        frame_idx: Optional[int] = None,
        timestamp: Optional[float] = None,
        bbox: Optional[Any] = None,
        confidence: Optional[float] = None,
        crop_path: Optional[str] = None,
    ) -> Tuple[str, bool, bool]:
        """
        Match an embedding to an existing global identity.

        Returns:
            (global_id, is_new, was_lost)

        is_new=True means a new PERSON/GID was created.
        was_lost=True means the person was previously LOST and has now reappeared.
        """

        if timestamp is None:
            timestamp = time.time()

        embedding = self._normalize_embedding(embedding)

        with self._lock:
            conn = self._connect()

            try:
                rows = conn.execute(
                    """
                    SELECT
                        global_id,
                        embedding,
                        status,
                        last_seen
                    FROM identities
                    """
                ).fetchall()

                best_id = None
                best_similarity = -1.0
                best_status = None

                for row in rows:
                    stored_embedding = (
                        self._deserialize_embedding(
                            row["embedding"]
                        )
                    )

                    similarity = self._cosine_similarity(
                        embedding,
                        stored_embedding,
                    )

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_id = row["global_id"]
                        best_status = row["status"]

                # ------------------------------------------------
                # Existing identity
                # ------------------------------------------------

                if (
                    best_id is not None
                    and best_similarity >= self.similarity_threshold
                ):
                    was_lost = (
                        str(best_status).upper()
                        == "LOST"
                    )

                    conn.execute(
                        """
                        UPDATE identities
                        SET
                            embedding = ?,
                            status = 'ACTIVE',
                            last_seen = ?,
                            last_camera = ?,
                            last_frame = ?,
                            best_crop_path =
                                COALESCE(?, best_crop_path)
                        WHERE global_id = ?
                        """,
                        (
                            self._serialize_embedding(
                                embedding
                            ),
                            timestamp,
                            camera_id,
                            frame_idx,
                            crop_path,
                            best_id,
                        ),
                    )

                    bbox_json = self._serialize_bbox(
                        bbox
                    )

                    conn.execute(
                        """
                        INSERT INTO sightings (
                            global_id,
                            camera_id,
                            frame_idx,
                            timestamp,
                            bbox,
                            confidence,
                            crop_path
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            best_id,
                            camera_id,
                            frame_idx,
                            timestamp,
                            bbox_json,
                            confidence,
                            crop_path,
                        ),
                    )

                    if was_lost:
                        self._add_event(
                            conn=conn,
                            global_id=best_id,
                            event_type="reappeared",
                            camera_id=camera_id,
                            detail=(
                                f"Identity reappeared "
                                f"on camera {camera_id}"
                            ),
                            occurred_at=timestamp,
                        )

                    conn.commit()

                    return best_id, False, was_lost

                # ------------------------------------------------
                # Create new identity
                # ------------------------------------------------

                global_id = self._new_global_id()

                conn.execute(
                    """
                    INSERT INTO identities (
                        global_id,
                        embedding,
                        status,
                        first_seen,
                        last_seen,
                        last_camera,
                        last_frame,
                        best_crop_path
                    )
                    VALUES (?, ?, 'ACTIVE', ?, ?, ?, ?, ?)
                    """,
                    (
                        global_id,
                        self._serialize_embedding(
                            embedding
                        ),
                        timestamp,
                        timestamp,
                        camera_id,
                        frame_idx,
                        crop_path,
                    ),
                )

                bbox_json = self._serialize_bbox(
                    bbox
                )

                conn.execute(
                    """
                    INSERT INTO sightings (
                        global_id,
                        camera_id,
                        frame_idx,
                        timestamp,
                        bbox,
                        confidence,
                        crop_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        global_id,
                        camera_id,
                        frame_idx,
                        timestamp,
                        bbox_json,
                        confidence,
                        crop_path,
                    ),
                )

                self._add_event(
                    conn=conn,
                    global_id=global_id,
                    event_type="first_seen",
                    camera_id=camera_id,
                    detail=(
                        f"Identity created on "
                        f"camera {camera_id}"
                    ),
                    occurred_at=timestamp,
                )

                conn.commit()

                return global_id, True, False

            finally:
                conn.close()

    # ============================================================
    # BBOX SERIALIZATION
    # ============================================================

    @staticmethod
    def _serialize_bbox(bbox) -> Optional[str]:
        """Serialize bounding box safely."""

        if bbox is None:
            return None

        try:
            if isinstance(bbox, np.ndarray):
                bbox = bbox.tolist()

            if isinstance(
                bbox,
                (list, tuple),
            ):
                return json.dumps(
                    list(bbox)
                )

            if isinstance(bbox, dict):
                return json.dumps(bbox)

            return str(bbox)

        except Exception:
            return str(bbox)

    @staticmethod
    def _deserialize_bbox(value):
        """Deserialize bounding box."""

        if value is None:
            return None

        try:
            return json.loads(value)
        except Exception:
            return value

    # ============================================================
    # LOST LIFECYCLE
    # ============================================================

    def promote_lost(
        self,
        timeout: Optional[float] = None,
    ) -> List[str]:
        """
        Mark inactive identities as LOST.

        Returns:
            list of identities promoted to LOST.
        """

        if timeout is None:
            timeout = self.lost_timeout

        now = time.time()
        cutoff = now - timeout

        promoted = []

        with self._lock:
            conn = self._connect()

            try:
                rows = conn.execute(
                    """
                    SELECT
                        global_id,
                        last_camera,
                        last_seen
                    FROM identities
                    WHERE status = 'ACTIVE'
                      AND last_seen < ?
                    """,
                    (cutoff,),
                ).fetchall()

                for row in rows:
                    global_id = row["global_id"]

                    conn.execute(
                        """
                        UPDATE identities
                        SET status = 'LOST'
                        WHERE global_id = ?
                        """,
                        (global_id,),
                    )

                    self._add_event(
                        conn=conn,
                        global_id=global_id,
                        event_type="lost",
                        camera_id=row["last_camera"],
                        detail=(
                            f"Identity marked LOST "
                            f"after {timeout:.1f}s"
                        ),
                        occurred_at=now,
                    )

                    promoted.append(global_id)

                conn.commit()

                return promoted

            finally:
                conn.close()

    # ============================================================
    # STATISTICS
    # ============================================================

    def stats(self) -> Dict[str, int]:
        """Return dashboard statistics."""

        with self._lock:
            conn = self._connect()

            try:
                active = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM identities
                    WHERE status = 'ACTIVE'
                    """
                ).fetchone()[0]

                lost = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM identities
                    WHERE status = 'LOST'
                    """
                ).fetchone()[0]

                resolved = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM identities
                    WHERE status = 'RESOLVED'
                    """
                ).fetchone()[0]

                sightings = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM sightings
                    """
                ).fetchone()[0]

                # Count actual LOST -> REAPPEARED events.
                reappearances = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM events
                    WHERE event_type = 'reappeared'
                    """
                ).fetchone()[0]

                return {
                    "active": int(active),
                    "lost": int(lost),
                    "resolved": int(resolved),
                    "sightings": int(sightings),
                    "reappearances": int(
                        reappearances
                    ),
                }

            finally:
                conn.close()

    # ============================================================
    # IDENTITY
    # ============================================================

    def get_identity(
        self,
        global_id: str,
    ) -> Optional[Dict]:
        """Get raw identity information."""

        with self._lock:
            conn = self._connect()

            try:
                row = conn.execute(
                    """
                    SELECT *
                    FROM identities
                    WHERE global_id = ?
                    """,
                    (global_id,),
                ).fetchone()

                if row is None:
                    return None

                result = dict(row)

                if result.get("embedding") is not None:
                    result["embedding"] = (
                        self._deserialize_embedding(
                            result["embedding"]
                        )
                    )

                return result

            finally:
                conn.close()

    # ============================================================
    # SIGHTINGS
    # ============================================================

    def get_sightings(
        self,
        global_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Return sightings for an identity."""

        with self._lock:
            conn = self._connect()

            try:
                query = """
                    SELECT
                        id,
                        global_id,
                        camera_id,
                        frame_idx,
                        timestamp,
                        bbox,
                        confidence,
                        crop_path
                    FROM sightings
                    WHERE global_id = ?
                    ORDER BY timestamp ASC
                """

                params = [global_id]

                if limit is not None:
                    query += " LIMIT ?"
                    params.append(int(limit))

                rows = conn.execute(
                    query,
                    params,
                ).fetchall()

                results = []

                for row in rows:
                    item = dict(row)

                    item["bbox"] = (
                        self._deserialize_bbox(
                            item["bbox"]
                        )
                    )

                    results.append(item)

                return results

            finally:
                conn.close()

    # ============================================================
    # EVENTS
    # ============================================================

    def get_events(
        self,
        global_id: str,
    ) -> List[Dict]:
        """Return event history."""

        with self._lock:
            conn = self._connect()

            try:
                rows = conn.execute(
                    """
                    SELECT
                        id,
                        global_id,
                        event_type,
                        camera_id,
                        occurred_at,
                        detail
                    FROM events
                    WHERE global_id = ?
                    ORDER BY occurred_at ASC
                    """,
                    (global_id,),
                ).fetchall()

                return [
                    dict(row)
                    for row in rows
                ]

            finally:
                conn.close()

    # ============================================================
    # PERSON VIEW
    # ============================================================

    def get_person(
        self,
        global_id: str,
    ) -> Optional[Dict]:
        """
        Return dashboard-friendly person object.
        """

        identity = self.get_identity(
            global_id
        )

        if identity is None:
            return None

        sightings = self.get_sightings(
            global_id
        )

        events = self.get_events(
            global_id
        )

        first_seen = identity.get(
            "first_seen"
        )

        last_seen = identity.get(
            "last_seen"
        )

        person = {
            "global_id": global_id,

            "status": str(
                identity.get(
                    "status",
                    "ACTIVE",
                )
            ).lower(),

            "first_seen_at": first_seen,
            "last_seen_at": last_seen,

            "last_camera_id": identity.get(
                "last_camera"
            ),

            "last_frame": identity.get(
                "last_frame"
            ),

            "best_crop_path": identity.get(
                "best_crop_path"
            ),

            "notes": identity.get(
                "notes"
            ),

            "resolved_at": identity.get(
                "resolved_at"
            ),

            "sightings": sightings,
            "events": events,
        }

        return person

    # ============================================================
    # GET ALL
    # ============================================================

    def get_all(
        self,
        status: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return all persons.

        status examples:
            active
            lost
            resolved
        """

        with self._lock:
            conn = self._connect()

            try:
                if status is None:
                    rows = conn.execute(
                        """
                        SELECT global_id
                        FROM identities
                        ORDER BY last_seen DESC
                        """
                    ).fetchall()

                else:
                    rows = conn.execute(
                        """
                        SELECT global_id
                        FROM identities
                        WHERE LOWER(status) = ?
                        ORDER BY last_seen DESC
                        """,
                        (
                            str(status).lower(),
                        ),
                    ).fetchall()

                persons = []

                for row in rows:
                    person = self.get_person(
                        row["global_id"]
                    )

                    if person is not None:
                        persons.append(person)

                return persons

            finally:
                conn.close()

    # ============================================================
    # RECENT REAPPEARANCES
    # ============================================================

    def get_recent_reappearances(
        self,
        since_seconds: int = 600,
    ) -> List[Dict]:
        """
        Return recent LOST -> REAPPEARED events.
        """

        cutoff = time.time() - since_seconds

        with self._lock:
            conn = self._connect()

            try:
                rows = conn.execute(
                    """
                    SELECT
                        e.id,
                        e.global_id,
                        e.camera_id,
                        e.occurred_at,
                        e.detail,
                        i.best_crop_path
                    FROM events e
                    LEFT JOIN identities i
                        ON e.global_id = i.global_id
                    WHERE e.event_type = 'reappeared'
                      AND e.occurred_at >= ?
                    ORDER BY e.occurred_at DESC
                    """,
                    (cutoff,),
                ).fetchall()

                return [
                    dict(row)
                    for row in rows
                ]

            finally:
                conn.close()

    # ============================================================
    # NOTES
    # ============================================================

    def add_note(
        self,
        global_id: str,
        note: str,
    ) -> bool:
        """Add or replace an identity note."""

        if not note:
            return False

        now = time.time()

        with self._lock:
            conn = self._connect()

            try:
                row = conn.execute(
                    """
                    SELECT notes
                    FROM identities
                    WHERE global_id = ?
                    """,
                    (global_id,),
                ).fetchone()

                if row is None:
                    return False

                old_notes = row["notes"]

                if old_notes:
                    new_notes = (
                        f"{old_notes}\n"
                        f"{note}"
                    )
                else:
                    new_notes = note

                conn.execute(
                    """
                    UPDATE identities
                    SET notes = ?
                    WHERE global_id = ?
                    """,
                    (
                        new_notes,
                        global_id,
                    ),
                )

                self._add_event(
                    conn=conn,
                    global_id=global_id,
                    event_type="note",
                    detail=note,
                    occurred_at=now,
                )

                conn.commit()

                return True

            finally:
                conn.close()

    # ============================================================
    # RESOLVE
    # ============================================================

    def resolve(
        self,
        global_id: str,
        note: Optional[str] = None,
    ) -> bool:
        """Mark an identity as resolved."""

        now = time.time()

        with self._lock:
            conn = self._connect()

            try:
                row = conn.execute(
                    """
                    SELECT global_id
                    FROM identities
                    WHERE global_id = ?
                    """,
                    (global_id,),
                ).fetchone()

                if row is None:
                    return False

                conn.execute(
                    """
                    UPDATE identities
                    SET
                        status = 'RESOLVED',
                        resolved_at = ?
                    WHERE global_id = ?
                    """,
                    (
                        now,
                        global_id,
                    ),
                )

                if note:
                    conn.execute(
                        """
                        UPDATE identities
                        SET notes =
                            CASE
                                WHEN notes IS NULL
                                OR notes = ''
                                THEN ?
                                ELSE notes || '\n' || ?
                            END
                        WHERE global_id = ?
                        """,
                        (
                            note,
                            note,
                            global_id,
                        ),
                    )

                self._add_event(
                    conn=conn,
                    global_id=global_id,
                    event_type="resolved",
                    detail=note,
                    occurred_at=now,
                )

                conn.commit()

                return True

            finally:
                conn.close()

    # ============================================================
    # REACTIVATE
    # ============================================================

    def reactivate(
        self,
        global_id: str,
    ) -> bool:
        """Reactivate a LOST or RESOLVED identity."""

        now = time.time()

        with self._lock:
            conn = self._connect()

            try:
                row = conn.execute(
                    """
                    SELECT status
                    FROM identities
                    WHERE global_id = ?
                    """,
                    (global_id,),
                ).fetchone()

                if row is None:
                    return False

                conn.execute(
                    """
                    UPDATE identities
                    SET
                        status = 'ACTIVE',
                        resolved_at = NULL
                    WHERE global_id = ?
                    """,
                    (global_id,),
                )

                self._add_event(
                    conn=conn,
                    global_id=global_id,
                    event_type="reactivated",
                    detail="Identity manually reactivated",
                    occurred_at=now,
                )

                conn.commit()

                return True

            finally:
                conn.close()

    # ============================================================
    # TIME SEARCH
    # ============================================================

    def search_by_time(
        self,
        since: Optional[float] = None,
        until: Optional[float] = None,
        camera_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Search identities observed during a time interval.

        Dashboard compatible.

        since:
            Unix timestamp.

        until:
            Unix timestamp.

        camera_id:
            Optional camera filter.
        """

        if since is None:
            since = 0

        if until is None:
            until = time.time()

        with self._lock:
            conn = self._connect()

            try:
                conditions = [
                    "timestamp >= ?",
                    "timestamp <= ?",
                ]

                params = [
                    since,
                    until,
                ]

                if camera_id is not None:
                    conditions.append(
                        "camera_id = ?"
                    )
                    params.append(
                        int(camera_id)
                    )

                where_clause = " AND ".join(
                    conditions
                )

                rows = conn.execute(
                    f"""
                    SELECT DISTINCT global_id
                    FROM sightings
                    WHERE {where_clause}
                    ORDER BY global_id
                    """,
                    params,
                ).fetchall()

                results = []

                for row in rows:
                    person = self.get_person(
                        row["global_id"]
                    )

                    if person is None:
                        continue

                    # Only return matching sightings
                    matching_sightings = []

                    for sighting in person[
                        "sightings"
                    ]:
                        ts = sighting.get(
                            "timestamp"
                        )

                        if ts is None:
                            continue

                        if (
                            since
                            <= ts
                            <= until
                        ):
                            if (
                                camera_id is None
                                or sighting.get(
                                    "camera_id"
                                )
                                == camera_id
                            ):
                                matching_sightings.append(
                                    sighting
                                )

                    person["sightings"] = (
                        matching_sightings
                    )

                    results.append(person)

                return results

            finally:
                conn.close()

    # ============================================================
    # DELETE / RESET HELPERS
    # ============================================================

    def delete_identity(
        self,
        global_id: str,
    ) -> bool:
        """
        Delete one identity and its history.

        Use carefully.
        """

        with self._lock:
            conn = self._connect()

            try:
                exists = conn.execute(
                    """
                    SELECT 1
                    FROM identities
                    WHERE global_id = ?
                    """,
                    (global_id,),
                ).fetchone()

                if exists is None:
                    return False

                conn.execute(
                    """
                    DELETE FROM sightings
                    WHERE global_id = ?
                    """,
                    (global_id,),
                )

                conn.execute(
                    """
                    DELETE FROM events
                    WHERE global_id = ?
                    """,
                    (global_id,),
                )

                conn.execute(
                    """
                    DELETE FROM identities
                    WHERE global_id = ?
                    """,
                    (global_id,),
                )

                conn.commit()

                return True

            finally:
                conn.close()

    def clear_database(self):
        """
        Delete all stored identity data.

        WARNING:
            This removes all identities, sightings and events.
        """

        with self._lock:
            conn = self._connect()

            try:
                conn.execute(
                    "DELETE FROM events"
                )

                conn.execute(
                    "DELETE FROM sightings"
                )

                conn.execute(
                    "DELETE FROM identities"
                )

                conn.commit()

            finally:
                conn.close()