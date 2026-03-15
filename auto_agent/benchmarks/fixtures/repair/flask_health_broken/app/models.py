# Health Status Model
class HealthStatus:
    def __init__(self):
        self.status = "healthy"
        self.timestamp = None
    
    def to_dict(self):
        return {
            "status": self.status,
            "timestamp": self.timestamp
        }
