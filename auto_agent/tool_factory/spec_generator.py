"""Tool Factory"""
class ToolFactory:
    def __init__(self):
        self.specs = {}
    def create_spec(self, name, description, args):
        spec = {"name": name, "description": description, "args": args}
        self.specs[name] = spec
        return spec

tool_factory = ToolFactory()
