import time
from collections import defaultdict

class InMemoryStore:
    def __init__(self):
        self.sessions = defaultdict(list)
        self.workflows = {}
        self.metrics = {"requests": 0, "errors": 0, "latency_ms": []}

    def save_message(self, session_id, role, content):
        self.sessions[session_id].append({"role": role, "content": content, "ts": time.time()})

    def get_session(self, session_id):
        return self.sessions.get(session_id, [])

store = InMemoryStore()
