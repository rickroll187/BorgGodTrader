import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logger for tracking all system actions for compliance and debugging.
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.audit_file = self.log_dir / "audit.jsonl"
        self.logs: List[Dict] = []
        self._load_existing()

    def _load_existing(self):
        """Load existing audit logs."""
        if self.audit_file.exists():
            try:
                with open(self.audit_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            self.logs.append(json.loads(line))
            except Exception as e:
                logger.error(f"Failed to load audit log: {e}")

    def log(self, action: str, details: Dict[str, Any] = None,
            user: str = "system", level: str = "info"):
        """Log an audit event."""
        entry = {
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "user": user,
            "level": level,
            "details": details or {},
        }

        self.logs.append(entry)

        try:
            with open(self.audit_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

        if level == "warning":
            logger.warning(f"AUDIT: {action}")
        elif level == "error":
            logger.error(f"AUDIT: {action}")
        else:
            logger.info(f"AUDIT: {action}")

    def log_trade(self, trade: Dict[str, Any]):
        """Log a trade action."""
        self.log(
            action="trade_executed",
            details=trade,
            level="info"
        )

    def log_config_change(self, setting: str, old_value: Any, new_value: Any):
        """Log a configuration change."""
        self.log(
            action="config_changed",
            details={
                "setting": setting,
                "old_value": old_value,
                "new_value": new_value,
            },
            level="warning"
        )

    def log_security_event(self, event_type: str, details: Dict = None):
        """Log a security-related event."""
        self.log(
            action=f"security_{event_type}",
            details=details,
            level="warning"
        )

    def log_error(self, error: str, context: Dict = None):
        """Log an error."""
        self.log(
            action="error",
            details={"error": error, "context": context},
            level="error"
        )

    def get_logs(self, limit: int = 100, action: str = None,
                 start_time: float = None) -> List[Dict]:
        """Get audit logs with optional filtering."""
        logs = self.logs.copy()

        if action:
            logs = [l for l in logs if l.get("action") == action]

        if start_time:
            logs = [l for l in logs if l.get("timestamp", 0) >= start_time]

        # Sort by timestamp descending
        logs.sort(key=lambda l: l.get("timestamp", 0), reverse=True)

        return logs[:limit]

    def get_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of audit events."""
        cutoff = time.time() - (hours * 3600)
        recent = [l for l in self.logs if l.get("timestamp", 0) >= cutoff]

        by_action = {}
        by_level = {}

        for l in recent:
            action = l.get("action", "unknown")
            level = l.get("level", "info")

            by_action[action] = by_action.get(action, 0) + 1
            by_level[level] = by_level.get(level, 0) + 1

        return {
            "period_hours": hours,
            "total_events": len(recent),
            "by_action": by_action,
            "by_level": by_level,
            "errors": by_level.get("error", 0),
            "warnings": by_level.get("warning", 0),
        }

    def export(self, filepath: str):
        """Export audit logs to file."""
        with open(filepath, 'w') as f:
            json.dump(self.logs, f, indent=2)
        logger.info(f"Exported {len(self.logs)} audit logs to {filepath}")
