"""
tests/test_queue.py

Standalone test script for QueueManager.
No GPIO needed — runs on any machine.

Usage:
    python3 tests/test_queue.py
"""

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import Database
from core.queue_manager import QueueManager

# Use an in-memory database for testing
TEST_DB_PATH = ":memory:"

passed = 0
failed = 0


def test(name: str, condition: bool):
    global passed, failed
    if condition:
        print(f"  ✅  {name}")
        passed += 1
    else:
        print(f"  ❌  {name}")
        failed += 1


def main():
    global passed, failed
    print("=" * 60)
    print("  QueueManager Test Suite")
    print("=" * 60)

    # ── Setup ─────────────────────────────────────────────────────
    db = Database(db_path=TEST_DB_PATH)
    db.init_db()
    qm = QueueManager(db)

    # ── Test 1: Enqueue ───────────────────────────────────────────
    print("\n── enqueue() ──")
    id1 = qm.enqueue("stt.transcribe", '{"file": "audio/001.wav"}', priority=1)
    id2 = qm.enqueue("llm.classify", '{"text": "hello world"}', priority=5)
    id3 = qm.enqueue("log.save", '{"event": "test"}', priority=0)

    test("Returns row id", id1 == 1 and id2 == 2 and id3 == 3)
    test("Pending count is 3", qm.pending_count() == 3)

    # ── Test 2: get_next (priority ordering) ──────────────────────
    print("\n── get_next() ──")
    task = qm.get_next()
    test("Highest priority first (id=2, priority=5)", task["id"] == 2)
    test("Status is 'processing'", task["status"] == "processing")
    test("started_at is set", task["started_at"] is not None)
    test("Pending count is now 2", qm.pending_count() == 2)

    # ── Test 3: complete ──────────────────────────────────────────
    print("\n── complete() ──")
    qm.complete(task["id"])
    counts = qm.count_by_status()
    test("Completed count is 1", counts.get("completed", 0) == 1)
    test("Pending count is 2", counts.get("pending", 0) == 2)

    # ── Test 4: fail ──────────────────────────────────────────────
    print("\n── fail() ──")
    task2 = qm.get_next()
    test("Next task (id=1, priority=1)", task2["id"] == 1)
    qm.fail(task2["id"], "API timeout")
    counts = qm.count_by_status()
    test("Failed count is 1", counts.get("failed", 0) == 1)

    # Verify error message stored
    failed_tasks = qm.get_by_status("failed")
    test("Error message stored", failed_tasks[0]["error"] == "API timeout")

    # ── Test 5: retry ─────────────────────────────────────────────
    print("\n── retry() ──")
    retried = qm.retry(task2["id"])
    test("Retry returns True", retried is True)
    counts = qm.count_by_status()
    test("Failed count is 0 (moved back to pending)", counts.get("failed", 0) == 0)
    test("Pending count is 2", counts.get("pending", 0) == 2)

    # Verify retry_count incremented
    task_after_retry = qm.get_next()
    # Should get id=1 again (priority=1) or id=3 (priority=0)
    # id=1 has priority=1 so it comes first
    test("Retried task is back in queue", task_after_retry["id"] == 1)
    test("retry_count is 1", task_after_retry["retry_count"] == 1)

    # ── Test 6: max retries ───────────────────────────────────────
    print("\n── retry() max retries ──")
    qm.fail(task_after_retry["id"], "fail again")
    qm.retry(task_after_retry["id"])  # retry_count = 2
    t = qm.get_next()
    qm.fail(t["id"], "fail 3")
    qm.retry(t["id"])                 # retry_count = 3
    t = qm.get_next()
    qm.fail(t["id"], "fail 4")
    denied = qm.retry(t["id"])        # retry_count would be 4 > MAX_RETRIES=3
    test("Retry denied after MAX_RETRIES", denied is False)

    # ── Test 7: get_all and get_by_status ─────────────────────────
    print("\n── query helpers ──")
    all_tasks = qm.get_all()
    test("get_all returns 3 tasks", len(all_tasks) == 3)

    completed = qm.get_by_status("completed")
    test("get_by_status('completed') returns 1", len(completed) == 1)

    # ── Test 8: empty queue ───────────────────────────────────────
    print("\n── empty queue ──")
    # Process remaining pending task (id=3)
    remaining = qm.get_next()
    if remaining:
        qm.complete(remaining["id"])
    empty = qm.get_next()
    test("get_next returns None when empty", empty is None)

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  Results: {passed}/{total} passed")
    if failed:
        print(f"  ❌ {failed} test(s) failed")
    else:
        print("  ✅ All tests passed!")
    print("=" * 60)

    db.close()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
