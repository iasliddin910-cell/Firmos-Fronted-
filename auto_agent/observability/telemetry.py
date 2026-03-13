"""Observability"""
class Telemetry:
    def __init__(self):
        self.metrics = {"tasks": 0, "success": 0, "failed": 0}
    def record_task(self, task_id, success):
        self.metrics["tasks"] += 1
        if success: self.metrics["success"] += 1
        else: self.metrics["failed"] += 1
    def get_stats(self):
        return self.metrics

telemetry = Telemetry()
