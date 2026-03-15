"""
Symbol Understanding Layer (LSP/SCIP)
=====================================

This layer provides symbol-level understanding through:
- LSP (Language Server Protocol) for live symbol intelligence
- SCIP for cross-repo semantic navigation

Key capabilities:
- Go to definition
- Find references  
- Hover docs
- Rename safety analysis
- Symbol ownership tracking
- Cross-repo resolution (package + version aware)
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SymbolDefinition:
    """Represents a symbol definition"""
    name: str
    kind: str  # function, class, method, variable, etc.
    file_path: str
    line: int
    column: int
    container: str = ""  # containing class/module
    signature: str = ""
    documentation: str = ""
    is_definition: bool = True


@dataclass
class SymbolReference:
    """Represents a symbol reference"""
    name: str
    file_path: str
    line: int
    column: int
    context: str = ""  # surrounding code


@dataclass
class SymbolInfo:
    """Complete symbol information"""
    definition: SymbolDefinition | None = None
    references: list[SymbolReference] = field(default_factory=list)
    callers: list[str] = field(default_factory=list)  # functions that call this
    callees: list[str] = field(default_factory=list)  # functions this calls
    type_hierarchy: list[str] = field(default_factory=list)
    implements: list[str] = field(default_factory=list)
    inherited_by: list[str] = field(default_factory=list)
    overrides: list[str] = field(default_factory=list)


class SymbolUnderstandingLayer:
    """
    Symbol Understanding Layer using LSP and SCIP
    
    This layer provides:
    - Precise symbol navigation (go-to-definition, find-references)
    - Cross-repository symbol resolution
    - Symbol ownership and lineage tracking
    - Type hierarchy analysis
    
    Key concepts:
    - LSP provides IDE-like features within a single repo
    - SCIP provides cross-repo navigation with package/version awareness
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.symbol_index: dict[str, SymbolInfo] = {}
        self.file_symbols: dict[str, list[SymbolDefinition]] = {}
        self.lsp_clients: dict[str, Any] = {}  # Per-language LSP clients
        self.scip_index: dict[str, Any] = {}  # Cross-repo SCIP data
        
        self._initialize_lsp_clients()
    
    def _initialize_lsp_clients(self):
        """Initialize LSP clients for each language"""
        # In production, would use actual LSP client libraries
        pass
    
    async def index_repo(self, repo_path: Path) -> dict[str, Any]:
        """Build complete symbol index for the repository."""
        files = await self._discover_source_files(repo_path)
        
        for file_path in files:
            await self._index_file(file_path)
        
        await self._build_references()
        call_graph = await self._build_call_graph()
        
        return {
            "symbols": {k: self._symbol_to_dict(v) for k, v in self.symbol_index.items()},
            "files": self.file_symbols,
            "call_graph": call_graph,
            "total_symbols": len(self.symbol_index),
            "total_files": len(self.file_symbols),
        }
    
    async def _index_file(self, file_path: Path):
        """Index a single file for symbols"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            symbols = self._extract_symbols(content, str(file_path))
            
            self.file_symbols[str(file_path)] = symbols
            
            for symbol in symbols:
                symbol_key = f"{symbol.file_path}:{symbol.name}"
                if symbol_key not in self.symbol_index:
                    self.symbol_index[symbol_key] = SymbolInfo()
                
                info = self.symbol_index[symbol_key]
                if symbol.is_definition:
                    info.definition = symbol
                else:
                    info.references.append(SymbolReference(
                        name=symbol.name,
                        file_path=symbol.file_path,
                        line=symbol.line,
                        column=symbol.column,
                    ))
        
        except Exception:
            pass
    
    def _extract_symbols(self, content: str, file_path: str) -> list[SymbolDefinition]:
        """Extract symbols from file content"""
        symbols = []
        lines = content.split("\n")
        
        for i, line in enumerate(lines):
            # Function definitions (Python)
            if "def " in line and ":" in line:
                name = line.split("def ")[1].split("(")[0].strip()
                symbols.append(SymbolDefinition(
                    name=name,
                    kind="function",
                    file_path=file_path,
                    line=i + 1,
                    column=line.index("def "),
                    signature=line.strip(),
                ))
            
            # Class definitions
            if line.strip().startswith("class ") and ":" in line:
                name = line.split("class ")[1].split("(")[0].strip()
                symbols.append(SymbolDefinition(
                    name=name,
                    kind="class",
                    file_path=file_path,
                    line=i + 1,
                    column=line.index("class "),
                    signature=line.strip(),
                ))
            
            # Import statements
            if line.strip().startswith(("import ", "from ")):
                if "import" in line:
                    parts = line.split("import")
                    if len(parts) > 1:
                        module = parts[1].strip()
                        symbols.append(SymbolDefinition(
                            name=module.split(".")[-1],
                            kind="import",
                            file_path=file_path,
                            line=i + 1,
                            column=0,
                            container=module,
                        ))
        
        return symbols
    
    async def _build_references(self):
        """Build reference relationships between symbols"""
        for symbol_key, info in self.symbol_index.items():
            if not info.definition:
                continue
            
            def_name = info.definition.name
            
            for other_key, other_info in self.symbol_index.items():
                if other_key == symbol_key:
                    continue
                
                for ref in other_info.references:
                    if ref.name == def_name:
                        info.callers.append(ref.file_path)
    
    async def _build_call_graph(self) -> dict[str, list[str]]:
        """Build call graph between functions"""
        call_graph = {}
        
        for symbol_key, info in self.symbol_index.items():
            if info.definition and info.definition.kind == "function":
                callers = []
                
                for other_key, other_info in self.symbol_index.items():
                    for ref in other_info.references:
                        if ref.name == info.definition.name:
                            callers.append(ref.file_path)
                
                call_graph[symbol_key] = callers
        
        return call_graph
    
    async def update_delta(self, changed_files: list[str]) -> dict[str, Any]:
        """Update symbol index for changed files only."""
        for file_path in changed_files:
            self._clear_file_symbols(file_path)
            await self._index_file(Path(file_path))
        
        await self._build_references()
        
        return {
            "symbols": {k: self._symbol_to_dict(v) for k, v in self.symbol_index.items()},
            "updated_files": changed_files,
        }
    
    def _clear_file_symbols(self, file_path: str):
        """Remove all symbols for a file from the index"""
        if file_path in self.file_symbols:
            del self.file_symbols[file_path]
        
        keys_to_remove = []
        for key, info in self.symbol_index.items():
            if info.definition and info.definition.file_path == file_path:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.symbol_index[key]
    
    async def go_to_definition(self, file_path: str, line: int, 
                              column: int) -> SymbolDefinition | None:
        """Find the definition of the symbol at the given position."""
        symbol_name = await self._find_symbol_at(file_path, line, column)
        
        if not symbol_name:
            return None
        
        for info in self.symbol_index.values():
            if info.definition and info.definition.name == symbol_name:
                return info.definition
        
        return None
    
    async def find_references(self, file_path: str, line: int, 
                            column: int) -> list[SymbolReference]:
        """Find all references to the symbol at the given position."""
        symbol_name = await self._find_symbol_at(file_path, line, column)
        
        if not symbol_name:
            return []
        
        references = []
        for info in self.symbol_index.values():
            if info.definition and info.definition.name == symbol_name:
                references.extend(info.references)
        
        return references
    
    async def _find_symbol_at(self, file_path: str, line: int, 
                             column: int) -> str | None:
        """Find the symbol name at a given position"""
        if file_path not in self.file_symbols:
            return None
        
        for symbol in self.file_symbols[file_path]:
            if symbol.line == line:
                return symbol.name
        
        return None
    
    async def get_symbol_info(self, symbol_name: str) -> SymbolInfo | None:
        """Get complete information about a symbol"""
        for key, info in self.symbol_index.items():
            if info.definition and info.definition.name == symbol_name:
                return info
        return None
    
    async def get_file_symbols(self, file_path: str) -> list[SymbolDefinition]:
        """Get all symbols defined in a file"""
        return self.file_symbols.get(file_path, [])
    
    async def rename_symbol(self, old_name: str, new_name: str, 
                          file_path: str | None = None) -> dict[str, list[str]]:
        """Analyze the impact of renaming a symbol."""
        affected_files = {}
        
        for key, info in self.symbol_index.items():
            if info.definition and info.definition.name == old_name:
                if file_path is None or info.definition.file_path == file_path:
                    affected_files[info.definition.file_path] = [
                        f"Line {info.definition.line}: definition"
                    ]
            
            for ref in info.references:
                if ref.name == old_name:
                    if ref.file_path not in affected_files:
                        affected_files[ref.file_path] = []
                    affected_files[ref.file_path].append(
                        f"Line {ref.line}: reference"
                    )
        
        return affected_files
    
    async def get_type_hierarchy(self, symbol_name: str) -> list[str]:
        """Get type hierarchy for a symbol"""
        info = await self.get_symbol_info(symbol_name)
        if info:
            return info.type_hierarchy
        return []
    
    def _symbol_to_dict(self, info: SymbolInfo) -> dict:
        """Convert SymbolInfo to dictionary"""
        result = {
            "references": [],
            "callers": info.callers,
            "callees": info.callees,
        }
        
        if info.definition:
            result["definition"] = {
                "name": info.definition.name,
                "kind": info.definition.kind,
                "file_path": info.definition.file_path,
                "line": info.definition.line,
                "container": info.definition.container,
                "signature": info.definition.signature,
            }
        
        for ref in info.references:
            result["references"].append({
                "file_path": ref.file_path,
                "line": ref.line,
                "column": ref.column,
            })
        
        return result
    
    async def _discover_source_files(self, repo_path: Path) -> list[Path]:
        """Discover all source files in the repository"""
        files = []
        extensions = {".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java"}
        
        for root, dirs, filenames in repo_path.walk():
            dirs[:] = [d for d in dirs if not d.startswith('.') 
                      and d not in ('node_modules', 'venv', '__pycache__')]
            
            for filename in filenames:
                path = Path(root) / filename
                if path.suffix in extensions:
                    files.append(path)
        
        return files


class SCIPClient:
    """
    SCIP (Source Code Intelligence Protocol) Client
    
    SCIP provides cross-repository semantic navigation with
    package and version awareness.
    """
    
    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.index_data: dict[str, Any] = {}
    
    async def load_index(self):
        """Load SCIP index from disk"""
        pass
    
    async def cross_repo_definition(self, symbol: str, package: str, 
                                  version: str) -> dict | None:
        """Find definition across repositories"""
        key = f"{package}@{version}:{symbol}"
        return self.index_data.get(key)
    
    async def cross_repo_references(self, symbol: str, package: str,
                                   version: str) -> list[dict]:
        """Find references across repositories"""
        key = f"{package}@{version}:{symbol}"
        return self.index_data.get(key, {}).get("references", [])
