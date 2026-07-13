"""
tests/test_database.py

Standalone test script for DatabaseManager.
Verifies all tables (logs, notes, memories, queue) and CRUD methods work cleanly.

Usage:
    python3 tests/test_database.py
"""

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database_manager import DatabaseManager

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
    print("  DatabaseManager Test Suite")
    print("=" * 60)

    # ── Setup ─────────────────────────────────────────────────────
    db = DatabaseManager(db_path=TEST_DB_PATH)
    db.init_db()

    # ── Test 1: Logs ──────────────────────────────────────────────
    print("\n── Logs Table ──")
    id1 = db.save_log("event.one")
    id2 = db.save_log("event.two")
    test("Save logs returns incrementing IDs", id1 == 1 and id2 == 2)
    
    logs = db.get_logs(limit=10)
    test("get_logs retrieves saved entries in correct order", len(logs) == 2 and logs[0]["event"] == "event.two")

    # ── Test 2: Notes ─────────────────────────────────────────────
    print("\n── Notes Table ──")
    nid1 = db.save_note("Meeting Title", "This is the note content.")
    nid2 = db.save_note("Shopping List", "Eggs, Milk, Coffee")
    test("Save notes returns incrementing IDs", nid1 == 1 and nid2 == 2)

    note = db.get_note(nid1)
    test("get_note retrieves correct note by ID", note is not None and note["title"] == "Meeting Title" and note["content"] == "This is the note content.")

    notes = db.get_notes(limit=10)
    test("get_notes retrieves all entries", len(notes) == 2 and notes[0]["title"] == "Shopping List")

    # ── Test 3: Memories ──────────────────────────────────────────
    print("\n── Memories Table ──")
    mid1 = db.save_memory("Remember to water the plants", source="user", tags="chore,home")
    mid2 = db.save_memory("Python 3.13 was released in 2024", source="llm", tags="fact,python")
    mid3 = db.save_memory("Octizen is local first", source="user", tags="project,octizen")
    test("Save memories returns incrementing IDs", mid1 == 1 and mid2 == 2 and mid3 == 3)

    memories = db.get_memories(limit=10)
    test("get_memories retrieves all saved entries", len(memories) == 3 and memories[0]["content"] == "Octizen is local first")

    user_mems = db.get_memories_by_source("user")
    test("get_memories_by_source filters correctly", len(user_mems) == 2 and all(m["source"] == "user" for m in user_mems))

    search_res = db.search_memories("plants")
    test("search_memories finds memory by keyword in content", len(search_res) == 1 and search_res[0]["id"] == mid1)

    # ── Test 4: Wi-Fi Networks ────────────────────────────────────
    print("\n── Wi-Fi Networks Table ──")
    db.save_wifi_network("HomeWiFi", "pass123", priority=10)
    db.save_wifi_network("OfficeWiFi", "secretpass", priority=5)
    
    wifi_list = db.get_wifi_networks()
    test("get_wifi_networks retrieves all saved networks", len(wifi_list) == 2)
    test("get_wifi_networks orders by priority ASC (lowest number first)", wifi_list[0]["ssid"] == "OfficeWiFi")
    
    # Update priority of OfficeWiFi from 5 to 20 (making it lower priority than HomeWiFi at 10)
    db.save_wifi_network("OfficeWiFi", "newsecret", priority=20)
    wifi_list_updated = db.get_wifi_networks()
    test("save_wifi_network ON CONFLICT updates priority", wifi_list_updated[0]["ssid"] == "HomeWiFi" and wifi_list_updated[1]["ssid"] == "OfficeWiFi" and wifi_list_updated[1]["password"] == "newsecret")

    # Delete network
    db.delete_wifi_network("HomeWiFi")
    wifi_list_deleted = db.get_wifi_networks()
    test("delete_wifi_network removes the SSID key", len(wifi_list_deleted) == 1 and wifi_list_deleted[0]["ssid"] == "OfficeWiFi")

    # ── Cleanup ───────────────────────────────────────────────────
    db.close()

    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  Results: {passed}/{total} passed")
    if failed:
        print(f"  ❌ {failed} test(s) failed")
    else:
        print("  ✅ All DatabaseManager tests passed!")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
