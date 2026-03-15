"""
Semantic Graph Layer (CPG/Joern)
==============================

This layer provides comprehensive semantic understanding through:
- Code Property Graph (CPG) construction
- Control Flow Analysis
- Data Flow Analysis
- Cross-function/cross-file relationship tracking
- Red-zone identification for dangerous areas

Key capabilities:
- Build unified graph of syntax + control-flow + data-flow
- Identify which functions call which
- Track data from source to sink
- Detect security-sensitive areas
- Calculate blast radius for changes
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class NodeType(Enum):
    """Types of nodes in the semantic graph"""
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    RETURN = "return"
    CALL = "call"
    IMPORT = "import"
    TYPE = "type"
    LITERAL = "literal"
    OPERATOR = "operator"


class EdgeType(Enum):
    """Types of edges in the semantic graph"""
    AST = "ast"              # Abstract Syntax Tree parent-child
    CALLS = "calls"          # Function calls
    CALLED_BY = "called_by"  # Reverse of calls
    IMPORT = "imports"        # Import relationships
    CFG = "cfg"              # Control Flow Graph
    DFG = "dfg"              # Data Flow Graph
    READS = "reads"          # Variable reads
    WRITES = "writes"        # Variable writes
    TYPE_OF = "type_of"      # Type relationships
    TEST_COVERS = "test_covers"  # Test covers function
    OWNS = "owns"            # Module owns function
    TOUCHES = "touches"      # Function touches resource
    USES_TOOL = "uses_tool"  # Uses external tool/API


class CriticalityLevel(Enum):
    """Criticality levels for code areas"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    RED_ZONE = "red_zone"  # Extremely dangerous to modify


# Red zone patterns - areas that should be treated with extreme caution
RED_ZONE_PATTERNS = [
    "auth", "authentication", "login", "password", "credential",
    "billing", "payment", "invoice", "subscription",
    "deployment", "deploy", "ci/cd", "pipeline",
    "secret", "token", "api_key", "encryption", "crypto",
    "core", "kernel", "runtime", "engine",
    "self_edit", "self_modify", "agent_core",
]


@dataclass
class GraphNode:
    """Represents a node in the semantic graph"""
    id: str
    node_type: NodeType
    name: str
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    
    # Metadata
    criticality: CriticalityLevel = CriticalityLevel.MEDIUM
    is_red_zone: bool = False
    documentation: str = ""
    properties: dict = field(default_factory=dict)
    
    # Relationships
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)
    reads_variables: list[str] = field(default_factory=list)
    writes_variables: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.node_type.value,
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "criticality": self.criticality.value,
            "is_red_zone": self.is_red_zone,
            "properties": self.properties,
        }


@dataclass
class GraphEdge:
    """Represents an edge in the semantic graph"""
    source_id: str
    target_id: str
    edge_type: EdgeType
    label: str = ""
    properties: dict = field(default_factory=dict)


@dataclass
class ControlFlowPath:
    """Represents a control flow path"""
    nodes: list[str]
    edges: list[str]
    is_loop: bool = False
    is_branch: bool = False
    conditions: list[str] = field(default_factory=list)


@dataclass
class DataFlowPath:
    """Represents a data flow path from source to sink"""
    source: str
    sink: str
    path: list[str]
    sanitizers: list[str] = field(default_factory=list)
    is_taint: bool = False


class SemanticGraphLayer:
    """
    Semantic Graph Layer using Code Property Graph (CPG)
    
    This layer provides:
    - Unified graph of AST + CFG + DFG
    - Control flow analysis
    - Data flow analysis (for security)
    - Cross-function/cross-file relationships
    - Critical area identification (red zones)
    - Blast radius calculation
    
    Implementation uses Joern-style CPG architecture:
    - Layered property graph
    - Edge types for different relationships
    - Efficient traversal queries
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.cpg_server_url = config.cpg_server_url
        
        # Graph storage
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        
        # Indexes for fast lookup
        self.file_nodes: dict[str, list[str]] = {}
        self.function_nodes: dict[str, GraphNode] = {}
        self.call_graph: dict[str, list[str]] = {}
        self.data_flows: list[DataFlowPath] = []
        
        # Red zones
        self.red_zone_nodes: set[str] = set()
        
        # Joern connection (in production, would connect to Joern server)
        self.joern_client = None
    
    async def build_graph(self, repo_path: Path) -> dict[str, Any]:
        """
        Build complete semantic graph for the repository.
        
        This performs:
        1. File discovery
        2. AST construction
        3. Control flow analysis
        4. Data flow analysis
        5. Import resolution
        6. Call graph building
        7. Red zone identification
        8. Test-function relationship mapping
        """
        # Discover all source files
        files = await self._discover_files(repo_path)
        
        # Build AST for each file
        for file_path in files:
            await self._build_file_ast(file_path)
        
        # Build control flow
        await self._build_control_flow()
        
        # Build data flow
        await self._build_data_flow()
        
        # Build call graph
        await self._build_call_graph()
        
        # Identify red zones
        self._identify_red_zones()
        
        # Build import relationships
        await self._build_import_graph()
        
        # Map tests to functions
        await self._map_tests_to_functions()
        
        return self._graph_to_dict()
    
    async def _discover_files(self, repo_path: Path) -> list[Path]:
        """Discover all source files in repository"""
        files = []
        extensions = {".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java"}
        
        for root, dirs, filenames in repo_path.walk():
            dirs[:] = [d for d in dirs if not d.startswith('.') 
                      and d not in ('node_modules', 'venv', '__pycache__', 'test', 'tests')]
            
            for filename in filenames:
                path = Path(root) / filename
                if path.suffix in extensions:
                    files.append(path)
        
        return files
    
    async def _build_file_ast(self, file_path: Path):
        """Build AST for a single file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Create file node
            file_node_id = f"file:{file_path}"
            file_node = GraphNode(
                id=file_node_id,
                node_type=NodeType.FILE,
                name=str(file_path.name),
                file_path=str(file_path),
                criticality=CriticalityLevel.MEDIUM,
            )
            self.nodes[file_node_id] = file_node
            self.file_nodes[str(file_path)] = [file_node_id]
            
            # Parse and create AST nodes
            await self._parse_to_ast(content, file_path)
            
        except Exception:
            pass
    
    async def _parse_to_ast(self, content: str, file_path: Path):
        """Parse content and create AST nodes"""
        lines = content.split("\n")
        
        # Track current function/class context
        current_function = None
        current_class = None
        
        for i, line in enumerate(lines, 1):
            # Function definitions
            if "def " in line and ":" in line and not line.strip().startswith("#"):
                func_name = line.split("def ")[1].split("(")[0].strip()
                func_id = f"func:{file_path}:{func_name}:{i}"
                
                func_node = GraphNode(
                    id=func_id,
                    node_type=NodeType.FUNCTION,
                    name=func_name,
                    file_path=str(file_path),
                    line_start=i,
                    line_end=i + self._count_function_lines(lines, i),
                    criticality=self._calculate_function_criticality(func_name),
                )
                
                self.nodes[func_id] = func_node
                self.function_nodes[f"{func_name}@{file_path}"] = func_node
                self.call_graph[func_id] = []
                
                # Add AST edge from file to function
                self.edges.append(GraphEdge(
                    source_id=f"file:{file_path}",
                    target_id=func_id,
                    edge_type=EdgeType.AST,
                ))
                
                current_function = func_id
            
            # Class definitions
            elif line.strip().startswith("class ") and ":" in line:
                class_name = line.split("class ")[1].split("(")[0].strip()
                class_id = f"class:{file_path}:{class_name}:{i}"
                
                class_node = GraphNode(
                    id=class_id,
                    node_type=NodeType.CLASS,
                    name=class_name,
                    file_path=str(file_path),
                    line_start=i,
                    criticality=self._calculate_class_criticality(class_name),
                )
                
                self.nodes[class_id] = class_node
                current_class = class_id
                
                # Add AST edge
                self.edges.append(GraphEdge(
                    source_id=f"file:{file_path}",
                    target_id=class_id,
                    edge_type=EdgeType.AST,
                ))
            
            # Function calls
            elif current_function and "(" in line:
                # Extract function calls
                call_name = self._extract_call_name(line)
                if call_name:
                    call_id = f"call:{file_path}:{call_name}:{i}"
                    call_node = GraphNode(
                        id=call_id,
                        node_type=NodeType.CALL,
                        name=call_name,
                        file_path=str(file_path),
                        line_start=i,
                    )
                    self.nodes[call_id] = call_node
                    
                    # Add CALL edge
                    self.edges.append(GraphEdge(
                        source_id=current_function,
                        target_id=call_id,
                        edge_type=EdgeType.CALLS,
                    ))
                    
                    # Update call graph
                    if current_function in self.call_graph:
                        self.call_graph[current_function].append(call_name)
            
            # Import statements
            if line.strip().startswith(("import ", "from ")):
                import_name = self._extract_import_name(line)
                if import_name:
                    import_id = f"import:{file_path}:{import_name}:{i}"
                    import_node = GraphNode(
                        id=import_id,
                        node_type=NodeType.IMPORT,
                        name=import_name,
                        file_path=str(file_path),
                        line_start=i,
                    )
                    self.nodes[import_id] = import_node
                    
                    # Add IMPORT edge
                    self.edges.append(GraphEdge(
                        source_id=f"file:{file_path}",
                        target_id=import_id,
                        edge_type=EdgeType.IMPORT,
                    ))
    
    def _count_function_lines(self, lines: list[str], start_line: int) -> int:
        """Count lines in a function body"""
        indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
        
        for i in range(start_line, len(lines)):
            if lines[i].strip() and not lines[i].startswith(" " * (indent + 1)):
                return i - start_line
        
        return len(lines) - start_line
    
    def _extract_call_name(self, line: str) -> str | None:
        """Extract function call name from line"""
        # Simple extraction - in production use proper parsing
        import re
        match = re.search(r'(\w+)\s*\(', line)
        if match:
            return match.group(1)
        return None
    
    def _extract_import_name(self, line: str) -> str | None:
        """Extract import name from line"""
        line = line.strip()
        
        if line.startswith("import "):
            return line.split("import ")[1].strip().split(".")[0]
        elif line.startswith("from "):
            parts = line.split("import ")
            if len(parts) > 1:
                return parts[1].strip().split(".")[0]
        
        return None
    
    def _calculate_function_criticality(self, name: str) -> CriticalityLevel:
        """Calculate criticality based on function name"""
        name_lower = name.lower()
        
        # Check for red zone patterns
        for pattern in RED_ZONE_PATTERNS:
            if pattern in name_lower:
                return CriticalityLevel.RED_ZONE
        
        # Check for critical prefixes
        if name.startswith(("__", "_")):
            return CriticalityLevel.HIGH
        
        return CriticalityLevel.MEDIUM
    
    def _calculate_class_criticality(self, name: str) -> CriticalityLevel:
        """Calculate criticality based on class name"""
        return self._calculate_function_criticality(name)
    
    async def _build_control_flow(self):
        """Build control flow graph for functions"""
        # In production, would use CFG analysis from parsed AST
        # This creates basic CFG edges
        
        for node_id, node in self.nodes.items():
            if node.node_type == NodeType.FUNCTION:
                # Create basic CFG - in production, do proper analysis
                cfg_entry = f"cfg:{node_id}:entry"
                cfg_exit = f"cfg:{node_id}:exit"
                
                # Entry edge
                self.edges.append(GraphEdge(
                    source_id=cfg_entry,
                    target_id=node_id,
                    edge_type=EdgeType.CFG,
                ))
                
                # Exit edge
                self.edges.append(GraphEdge(
                    source_id=node_id,
                    target_id=cfg_exit,
                    edge_type=EdgeType.CFG,
                ))
    
    async def _build_data_flow(self):
        """Build data flow graph"""
        # Track variable definitions and uses
        variable_defs: dict[str, list[str]] = {}
        
        for node_id, node in self.nodes.items():
            if node.node_type == NodeType.CALL:
                # Check if this is a potentially dangerous call
                if self._is_sink_function(node.name):
                    # Find source of data flow
                    sources = self._find_data_sources(node)
                    
                    for source in sources:
                        self.data_flows.append(DataFlowPath(
                            source=source,
                            sink=node_id,
                            path=[source, node_id],
                            is_taint=True,
                        ))
    
    def _is_sink_function(self, name: str) -> bool:
        """Check if function is a security sink"""
        sink_functions = {
            # SQL
            "execute", "query", "raw", "cursor",
            # Command execution
            "exec", "system", "popen", "run",
            # File operations
            "open", "write", "read", "file",
            # Network
            "request", "fetch", "curl", "send",
            # Serialization
            "loads", "dumps", "deserialize", "eval", "exec",
        }
        return name.lower() in sink_functions
    
    def _find_data_sources(self, sink_node: GraphNode) -> list[str]:
        """Find data sources that flow to a sink"""
        sources = []
        
        # Walk backwards through graph
        for edge in self.edges:
            if edge.target_id == sink_node.id:
                sources.append(edge.source_id)
        
        return sources
    
    async def _build_call_graph(self):
        """Build complete call graph"""
        # Call graph already built in _parse_to_ast
        # Add reverse edges (callee -> caller)
        
        for caller_id, callees in self.call_graph.items():
            for callee in callees:
                # Find the callee node
                for node_id, node in self.nodes.items():
                    if node.name == callee:
                        # Add CALLED_BY edge
                        self.edges.append(GraphEdge(
                            source_id=node_id,
                            target_id=caller_id,
                            edge_type=EdgeType.CALLED_BY,
                        ))
    
    def _identify_red_zones(self):
        """Identify red zone nodes - dangerous areas"""
        for node_id, node in self.nodes.items():
            name_lower = node.name.lower()
            
            for pattern in RED_ZONE_PATTERNS:
                if pattern in name_lower:
                    node.is_red_zone = True
                    node.criticality = CriticalityLevel.RED_ZONE
                    self.red_zone_nodes.add(node_id)
                    break
    
    async def _build_import_graph(self):
        """Build import dependency graph"""
        # Import edges already added in _parse_to_ast
        pass
    
    async def _map_tests_to_functions(self):
        """Map test files to the functions they test"""
        test_files = []
        
        # Find test files
        for node_id, node in self.nodes.items():
            if node.node_type == NodeType.FILE and "test" in node.file_path.lower():
                test_files.append(node)
        
        # For each test, find what it tests
        for test_file in test_files:
            # Find functions in same module
            module = str(Path(test_file.file_path).parent)
            
            for node_id, node in self.nodes.items():
                if node.node_type == NodeType.FUNCTION:
                    func_module = str(Path(node.file_path).parent)
                    
                    if module == func_module:
                        # Test likely covers this function
                        self.edges.append(GraphEdge(
                            source_id=test_file.id,
                            target_id=node_id,
                            edge_type=EdgeType.TEST_COVERS,
                        ))
    
    async def update_graph_delta(self, changed_files: list[str]) -> dict[str, Any]:
        """Update graph for changed files only"""
        # Clear old nodes for changed files
        nodes_to_remove = []
        
        for node_id, node in self.nodes.items():
            if node.file_path in changed_files:
                nodes_to_remove.append(node_id)
        
        for node_id in nodes_to_remove:
            del self.nodes[node_id]
        
        # Rebuild for changed files
        for file_path in changed_files:
            await self._build_file_ast(Path(file_path))
        
        # Rebuild relationships
        await self._build_call_graph()
        self._identify_red_zones()
        
        return self._graph_to_dict()
    
    def _graph_to_dict(self) -> dict:
        """Convert graph to dictionary format"""
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type.value,
                }
                for e in self.edges
            ],
            "call_graph": self.call_graph,
            "data_flows": [
                {
                    "source": df.source,
                    "sink": df.sink,
                    "path": df.path,
                    "is_taint": df.is_taint,
                }
                for df in self.data_flows
            ],
            "red_zones": list(self.red_zone_nodes),
            "statistics": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "red_zone_count": len(self.red_zone_nodes),
                "data_flow_count": len(self.data_flows),
            },
        }
    
    # Query methods
    
    def get_callers(self, function_id: str) -> list[str]:
        """Get all functions that call this function"""
        callers = []
        
        for edge in self.edges:
            if edge.edge_type == EdgeType.CALLED_BY and edge.source_id == function_id:
                callers.append(edge.target_id)
        
        return callers
    
    def get_callees(self, function_id: str) -> list[str]:
        """Get all functions this function calls"""
        return self.call_graph.get(function_id, [])
    
    def get_data_flow_to(self, sink_id: str) -> list[DataFlowPath]:
        """Get all data flows that reach a sink"""
        return [df for df in self.data_flows if df.sink == sink_id]
    
    def get_red_zones(self) -> list[GraphNode]:
        """Get all red zone nodes"""
        return [self.nodes[rid] for rid in self.red_zone_nodes if rid in self.nodes]
    
    def get_function_criticality(self, function_id: str) -> CriticalityLevel:
        """Get the criticality level of a function"""
        node = self.nodes.get(function_id)
        if node:
            return node.criticality
        return CriticalityLevel.MEDIUM
    
    def find_affected_functions(self, changed_node_id: str) -> set[str]:
        """Find all functions that would be affected by changing a node"""
        affected = set()
        
        # Direct callers
        affected.update(self.get_callers(changed_node_id))
        
        # Indirect callers (recursive)
        to_check = list(affected)
        checked = set()
        
        while to_check:
            caller = to_check.pop()
            if caller in checked:
                continue
            checked.add(caller)
            
            for indirect_caller in self.get_callers(caller):
                if indirect_caller not in checked:
                    affected.add(indirect_caller)
                    to_check.append(indirect_caller)
        
        return affected
    
    def calculate_blast_radius(self, node_ids: list[str]) -> dict:
        """Calculate blast radius for changing certain nodes"""
        affected_nodes = set()
        affected_functions = set()
        red_zones_affected = []
        
        for node_id in node_ids:
            # Add the node itself
            affected_nodes.add(node_id)
            
            # Find affected functions
            if node_id in self.function_nodes:
                affected_functions.add(node_id)
            
            # Find downstream functions
            affected_functions.update(self.find_affected_functions(node_id))
            
            # Check if red zone affected
            if node_id in self.red_zone_nodes:
                red_zones_affected.append(node_id)
        
        return {
            "affected_nodes": list(affected_nodes),
            "affected_functions": list(affected_functions),
            "red_zones_affected": red_zones_affected,
            "blast_radius": "critical" if red_zones_affected else "moderate",
        }


class JoernClient:
    """
    Client for connecting to Joern CPG server
    
    In production, this would connect to a Joern server instance
    for more advanced graph queries.
    """
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.connected = False
    
    async def connect(self):
        """Connect to Joern server"""
        # In production: Establish connection to Joern
        self.connected = True
    
    async def query(self, cpg_query: str) -> list[dict]:
        """Execute a CPG query"""
        # In production: Send query to Joern and return results
        return []
    
    async def run_taint_analysis(self, source: str, sink: str) -> list[DataFlowPath]:
        """Run taint analysis between source and sink"""
        # In production: Use Joern's taint analysis
        return []
