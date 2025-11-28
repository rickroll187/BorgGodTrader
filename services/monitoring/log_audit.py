import json
import os
from datetime import datetime

class AuditLogger:
    def __init__(self, audit_file="audit_log.jsonl"):
        self.audit_file = audit_file

    def log(self, event_type, details):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details,
        }
        with open(self.audit_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_logs(self):
        if not os.path.exists(self.audit_file):
            return []
        with open(self.audit_file, "r") as f:
            return [json.loads(l) for l in f if l.strip()]
