"""
core/queue_manager.py

Business logic for the task queue.
All DB access goes through DatabaseManager — zero raw SQL here.

Status lifecycle:
    pending → processing → completed
                         → failed → (retry) → pending

Usage:
    qm = QueueManager(db_manager, event_manager)
    task_id = qm.enqueue("stt.transcribe", '{"file": "audio/001.wav"}')
    task = qm.get_next()
    qm.complete(task["id"])
    qm.fail(task["id"], "API timeout")
    qm.retry(task["id"])
"""

from core.logger import logger


MAX_RETRIES = 3


class QueueManager:
    """
    Task queue business logic.
    DB operations delegated to DatabaseManager.
    Events emitted through EventManager.
    """

    def __init__(self, db_manager, event_manager=None):
        """
        Args:
            db_manager:    storage.DatabaseManager instance
            event_manager: optional core.EventManager for emitting queue events
        """
        self._db = db_manager
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
        """Add a new task to the queue. Returns the new task id."""
        task_id = self._db.save_queue(task_type, payload, priority)
        logger.info(f"[Queue] Enqueued: id={task_id} type={task_type} priority={priority}")
        self._emit("queue.enqueued", {"id": task_id, "task_type": task_type, "priority": priority})
        return task_id

    def get_next(self) -> dict | None:
        """
        Fetch and lock the next pending task (highest priority, then oldest).
        Returns task dict or None if queue is empty.
        """
        task = self._db.get_next_pending_task()
        if task is None:
            return None
        logger.info(f"[Queue] Processing: id={task['id']} type={task['task_type']}")
        self._emit("queue.processing", {"id": task["id"], "task_type": task["task_type"]})
        return task

    def complete(self, task_id: int) -> None:
        """Mark a task as completed."""
        self._db.complete_task(task_id)
        logger.info(f"[Queue] Completed: id={task_id}")
        self._emit("queue.completed", {"id": task_id})

    def fail(self, task_id: int, error: str = "") -> None:
        """Mark a task as failed with an error message."""
        self._db.fail_task(task_id, error)
        logger.info(f"[Queue] Failed: id={task_id} error={error}")
        self._emit("queue.failed", {"id": task_id, "error": error})

    def retry(self, task_id: int) -> bool:
        """
        Retry a failed task. Increments retry_count, resets to pending.
        Returns False if MAX_RETRIES exceeded.
        """
        task = self._db.get_task(task_id)

        if task is None:
            logger.warning(f"[Queue] Retry failed: id={task_id} not found")
            return False

        new_count = task["retry_count"] + 1

        if new_count > MAX_RETRIES:
            logger.warning(
                f"[Queue] Retry denied: id={task_id} "
                f"retry_count={new_count} exceeds MAX_RETRIES={MAX_RETRIES}"
            )
            return False

        self._db.reset_task_to_pending(task_id, new_count)
        logger.info(f"[Queue] Retried: id={task_id} attempt={new_count}/{MAX_RETRIES}")
        self._emit("queue.retried", {"id": task_id, "retry_count": new_count})
        return True

    # ------------------------------------------------------------------
    # Query helpers (delegate to DatabaseManager)
    # ------------------------------------------------------------------

    def get_by_status(self, status: str, limit: int = 50) -> list[dict]:
        """Fetch tasks filtered by status."""
        return self._db.get_queue_by_status(status, limit)

    def get_all(self, limit: int = 100) -> list[dict]:
        """Fetch all tasks, newest first."""
        return self._db.get_queue(limit)

    def count_by_status(self) -> dict:
        """Returns {status: count}."""
        return self._db.count_queue_by_status()

    def pending_count(self) -> int:
        """Number of pending tasks."""
        return self._db.pending_task_count()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, event_name: str, data: dict) -> None:
        """Emit a queue event if EventManager is available."""
        if self._event_manager:
            self._event_manager.emit(event_name, data)
