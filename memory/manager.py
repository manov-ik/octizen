from datetime import datetime, timezone
from storage.database import db, Database
from memory.models import MemoryCreate, Memory, LogCreate, Log

class MemoryManager:
    def __init__(self, database: Database):
        self.db = database

    def get_memories(self) -> list[Memory]:
        raw_memories = self.db.fetch_all_memories()
        return [Memory(**m) for m in raw_memories]

    def add_memory(self, memory_in: MemoryCreate) -> Memory:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_memory = self.db.insert_memory(
            title=memory_in.title,
            content=memory_in.content,
            m_type=memory_in.type,
            source=memory_in.source,
            created_at=now_str,
            updated_at=now_str,
            favorite=0
        )
        return Memory(**raw_memory)

    def delete_memory(self, memory_id: int) -> bool:
        return self.db.delete_memory(memory_id)

    def get_logs(self) -> list[Log]:
        raw_logs = self.db.fetch_all_logs()
        return [Log(**l) for l in raw_logs]

    def add_log(self, log_in: LogCreate) -> Log:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_log = self.db.insert_log(
            message=log_in.message,
            level=log_in.level,
            created_at=now_str
        )
        return Log(**raw_log)

# Shared global instance of MemoryManager using the shared db instance
memory_manager = MemoryManager(db)
