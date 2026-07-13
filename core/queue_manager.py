"""
core/queue_manager.py

Production-quality task queue for Octizen.
Every long-running task flows through here.

Status lifecycle:
    pending → processing → completed
                         → failed → (retry) → pending

Usage:
    qm = QueueManager(db, event_manager)
    task_id = qm.enqueue("stt.transcribe", '{"file": "audio/001.wav"}')
    task = qm.get_next()
    qm.complete(task["id"])
    # or
    qm.fail(task["id"], "API timeout")
    qm.retry(task["id"])
"""

from datetime import datetime
from core.logger import logger
from storage.database import Database


VALID_STATUSES = {"pending", "processing", "completed", "failed"}
MAX_RETRIES = 3


class QueueManager:
    """
    Manages the task queue. All methods operate on the `queue` table.
    Emits events through EventManager for observability.
    """

    def __init__(self, db: Database, event_manager=None):
        """
        Args:
            db:            Database instance (must be init_db'd)
            event_manager: optional EventManager for emitting queue events
        """
        self._db = db
        self._event_manager = event_manager

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def enqueue(
        self,
        task_type: str,
        payload: str = "",
        priority: int = 0,
    ) -> int:
        """
        Add a new task to the queue.

        Args:
            task_type: e.g. "stt.transcribe", "llm.classify", "log.save"
            payload:   JSON string or free text with task data
            priority:  higher = processed first (default 0)

        Returns:
            The new task row id.
        """
        conn = self._db.get_conn()
        cur = conn.execute(
            """
            INSERT INTO queue (task_type, payload, status, priority, created_at)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (task_type, payload, priority, datetime.utcnow().isoformat()),
        )
        conn.commit()
        task_id = cur.lastrowid
        logger.info(f"[Queue] Enqueued: id={task_id} type={task_type} priority={priority}")
        self._emit("queue.enqueued", {"id": task_id, "task_type": task_type, "priority": priority})
        return task_id

    def get_next(self) -> dict | None:
        """
        Fetch the next pending task (highest priority first, then oldest).
        Atomically sets its status to 'processing'.

        Returns:
            Task dict or None if queue is empty.
        """
        conn = self._db.get_conn()
        row = conn.execute(
            """
            SELECT * FROM queue
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            return None

        task = dict(row)
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE queue SET status = 'processing', started_at = ? WHERE id = ?",
            (now, task["id"]),
        )
        conn.commit()
        task["status"] = "processing"
        task["started_at"] = now
        logger.info(f"[Queue] Processing: id={task['id']} type={task['task_type']}")
        self._emit("queue.processing", {"id": task["id"], "task_type": task["task_type"]})
        return task

    def complete(self, task_id: int) -> None:
        """
        Mark a task as completed.

        Args:
            task_id: the queue row id
        """
        now = datetime.utcnow().isoformat()
        conn = self._db.get_conn()
        conn.execute(
            "UPDATE queue SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        conn.commit()
        logger.info(f"[Queue] Completed: id={task_id}")
        self._emit("queue.completed", {"id": task_id})

    def fail(self, task_id: int, error: str = "") -> None:
        """
        Mark a task as failed.

        Args:
            task_id: the queue row id
            error:   error message / traceback
        """
        now = datetime.utcnow().isoformat()
        conn = self._db.get_conn()
        conn.execute(
            "UPDATE queue SET status = 'failed', completed_at = ?, error = ? WHERE id = ?",
            (now, error, task_id),
        )
        conn.commit()
        logger.info(f"[Queue] Failed: id={task_id} error={error}")
        self._emit("queue.failed", {"id": task_id, "error": error})

    def retry(self, task_id: int) -> bool:
        """
        Retry a failed task. Increments retry_count, resets to 'pending'.
        Will not retry if MAX_RETRIES is reached.

        Args:
            task_id: the queue row id

        Returns:
            True if retried, False if max retries reached.
        """
        conn = self._db.get_conn()
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (task_id,)).fetchone()

        if row is None:
            logger.warning(f"[Queue] Retry failed: id={task_id} not found")
            return False

        task = dict(row)
        new_count = task["retry_count"] + 1

        if new_count > MAX_RETRIES:
            logger.warning(
                f"[Queue] Retry denied: id={task_id} "
                f"retry_count={new_count} exceeds MAX_RETRIES={MAX_RETRIES}"
            )
            return False

        conn.execute(
            """
            UPDATE queue
            SET status = 'pending', started_at = NULL, completed_at = NULL,
                error = NULL, retry_count = ?
            WHERE id = ?
            """,
            (new_count, task_id),
        )
        conn.commit()
        logger.info(f"[Queue] Retried: id={task_id} attempt={new_count}/{MAX_RETRIES}")
        self._emit("queue.retried", {"id": task_id, "retry_count": new_count})
        return True

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_by_status(self, status: str, limit: int = 50) -> list[dict]:
        """Fetch tasks filtered by status."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM queue WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all(self, limit: int = 100) -> list[dict]:
        """Fetch all tasks, newest first."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM queue ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def count_by_status(self) -> dict:
        """Returns a dict of {status: count}."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM queue GROUP BY status"
        ).fetchall()
        return {row["status"]: row["cnt"] for row in rows}

    def pending_count(self) -> int:
        """Number of pending tasks."""
        conn = self._db.get_conn()
        return conn.execute(
            "SELECT COUNT(*) FROM queue WHERE status = 'pending'"
        ).fetchone()[0]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, event_name: str, data: dict) -> None:
        """Emit a queue event if EventManager is available."""
        if self._event_manager:
            self._event_manager.emit(event_name, data)
