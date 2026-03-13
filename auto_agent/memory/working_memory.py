"""Memory System"""
class WorkingMemory:
    def __init__(self):
        self.variables = {}
    def set(self, k, v): self.variables[k] = v
    def get(self, k): return self.variables.get(k)

class SemanticMemory:
    def __init__(self):
        self.knowledge = {}
    def store(self, k, v): self.knowledge[k] = v
    def retrieve(self, q): return self.knowledge.get(q)

class MemorySystem:
    def __init__(self):
        self.working = WorkingMemory()
        self.semantic = SemanticMemory()

memory_system = MemorySystem()
