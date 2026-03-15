"""
Syntax Understanding Layer (Tree-sitter)
=====================================

This layer provides fast syntax parsing and incremental diff analysis
using Tree-sitter.

Key capabilities:
- Parse code into CST/AST
- Identify syntax errors
- Perform incremental parsing (only parse changed files)
- Query syntax patterns using Tree-sitter's query language
- Track changes between versions

Tree-sitter is a parser generator and incremental parsing library that:
- Builds syntax trees efficiently
- Handles erroneous code gracefully
- Supports pattern matching via query syntax
- Provides fast incremental updates
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Note: In production, you would use the actual tree-sitter library
# This is a comprehensive interface/implementation outline

try:
    import tree_sitter
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


# Language configurations
LANGUAGE_CONFIGS = {
    "python": {
        "extension": ".py",
        "tree_sitter_lang": "tree-sitter-python",
    },
    "javascript": {
        "extension": ".js",
        "tree_sitter_lang": "tree-sitter-javascript",
    },
    "typescript": {
        "extension": ".ts",
        "tree_sitter_lang": "tree-sitter-typescript",
    },
    "tsx": {
        "extension": ".tsx",
        "tree_sitter_lang": "tree-sitter-typescript",
    },
    "go": {
        "extension": ".go",
        "tree_sitter_lang": "tree-sitter-go",
    },
    "rust": {
        "extension": ".rs",
        "tree_sitter_lang": "tree-sitter-rust",
    },
    "java": {
        "extension": ".java",
        "tree_sitter_lang": "tree-sitter-java",
    },
    "c": {
        "extension": ".c",
        "tree_sitter_lang": "tree-sitter-c",
    },
    "cpp": {
        "extension": ".cpp",
        "tree_sitter_lang": "tree-sitter-cpp",
    },
}


@dataclass
class SyntaxNode:
    """Represents a node in the syntax tree"""
    type: str
    text: str
    start_point: tuple[int, int]
    end_point: tuple[int, int]
    children: list["SyntaxNode"] = field(default_factory=list)
    parent: "SyntaxNode | None" = None
    
    def __repr__(self):
        return f"SyntaxNode(type={self.type}, text={self.text[:30]}...)"


@dataclass
class SyntaxError:
    """Represents a syntax error in the code"""
    message: str
    line: int
    column: int
    node_type: str = ""


@dataclass
class ParseResult:
    """Result of parsing a file"""
    file_path: str
    language: str
    tree: SyntaxNode | None = None
    errors: list[SyntaxError] = field(default_factory=list)
    parse_time_ms: float = 0.0
    is_incremental: bool = False
    
    def get_functions(self) -> list[dict]:
        """Extract all functions from the parse tree"""
        functions = []
        
        def visit(node: SyntaxNode):
            if node.type in ("function_definition", "function_declaration", 
                           "method_definition", "arrow_function"):
                functions.append({
                    "name": self._get_function_name(node),
                    "start_line": node.start_point[0],
                    "end_line": node.end_point[0],
                    "params": self._get_parameters(node),
                    "body": node.text,
                })
            for child in node.children:
                visit(child)
        
        if self.tree:
            visit(self.tree)
        
        return functions
    
    def get_classes(self) -> list[dict]:
        """Extract all classes from the parse tree"""
        classes = []
        
        def visit(node: SyntaxNode):
            if node.type in ("class_definition", "class_declaration"):
                classes.append({
                    "name": self._get_class_name(node),
                    "start_line": node.start_point[0],
                    "end_line": node.end_point[0],
                    "body": node.text,
                })
            for child in node.children:
                visit(child)
        
        if self.tree:
            visit(self.tree)
        
        return classes
    
    def get_imports(self) -> list[dict]:
        """Extract all imports from the parse tree"""
        imports = []
        
        def visit(node: SyntaxNode):
            if node.type in ("import_statement", "import_from_statement",
                           "require_call", "using_declaration"):
                imports.append({
                    "module": self._get_import_module(node),
                    "names": self._get_import_names(node),
                    "line": node.start_point[0],
                })
            for child in node.children:
                visit(child)
        
        if self.tree:
            visit(self.tree)
        
        return imports
    
    def get_calls(self) -> list[dict]:
        """Extract all function/method calls"""
        calls = []
        
        def visit(node: SyntaxNode):
            if node.type in ("call", "method_call", "function_call"):
                calls.append({
                    "function": self._get_call_name(node),
                    "line": node.start_point[0],
                    "args": self._get_arguments(node),
                })
            for child in node.children:
                visit(child)
        
        if self.tree:
            visit(self.tree)
        
        return calls
    
    def _get_function_name(self, node: SyntaxNode) -> str:
        """Extract function name from node"""
        for child in node.children:
            if child.type in ("identifier", "attribute"):
                return child.text
        return ""
    
    def _get_class_name(self, node: SyntaxNode) -> str:
        """Extract class name from node"""
        for child in node.children:
            if child.type == "identifier":
                return child.text
        return ""
    
    def _get_parameters(self, node: SyntaxNode) -> list[str]:
        """Extract function parameters"""
        params = []
        for child in node.children:
            if child.type in ("parameters", "parameter_list"):
                for param in child.children:
                    if param.type == "identifier":
                        params.append(param.text)
        return params
    
    def _get_import_module(self, node: SyntaxNode) -> str:
        """Extract imported module name"""
        for child in node.children:
            if child.type in ("module", "module_name", "string"):
                return child.text.strip('"').strip("'")
        return ""
    
    def _get_import_names(self, node: SyntaxNode) -> list[str]:
        """Extract imported names"""
        names = []
        for child in node.children:
            if child.type in ("dotted_name", "name", "alias"):
                names.append(child.text)
        return names
    
    def _get_call_name(self, node: SyntaxNode) -> str:
        """Extract called function/method name"""
        for child in node.children:
            if child.type in ("attribute", "identifier"):
                return child.text
        return ""
    
    def _get_arguments(self, node: SyntaxNode) -> list[str]:
        """Extract function arguments"""
        args = []
        for child in node.children:
            if child.type in ("arguments", "argument_list"):
                for arg in child.children:
                    if arg.type != ",":
                        args.append(arg.text)
        return args


class SyntaxUnderstandingLayer:
    """
    Syntax Understanding Layer using Tree-sitter
    
    This layer provides:
    - Fast, incremental parsing of source code
    - Syntax tree construction
    - Error detection and reporting
    - Pattern matching via Tree-sitter queries
    - Diff analysis between versions
    
    Key optimizations:
    - Changed-file first reparse
    - Full parse only when necessary
    - Parallel parsing for large codebases
    - Aggressive caching of parse results
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.parsers: dict[str, Any] = {}
        self.parse_cache: dict[str, ParseResult] = {}
        self.language_handlers = LANGUAGE_CONFIGS
        
        # Initialize parsers for configured languages
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """Initialize Tree-sitter parsers for configured languages"""
        if not TREE_SITTER_AVAILABLE:
            return
        
        for lang in self.config.tree_sitter_languages:
            if lang in LANGUAGE_CONFIGS:
                try:
                    # In production, load actual Tree-sitter language
                    # parser = Parser(Language(language_libs[f"tree-sitter-{lang}"]))
                    # self.parsers[lang] = parser
                    pass
                except Exception as e:
                    pass
    
    async def parse_repo(self, repo_path: Path) -> dict[str, Any]:
        """
        Parse all files in the repository.
        
        This performs a full parse of the entire codebase,
        building comprehensive syntax trees for all supported files.
        """
        results = {}
        files = await self._discover_files(repo_path)
        
        # Parallel parsing for performance
        if self.config.parallel_loading:
            parse_tasks = [self.parse_file(f) for f in files]
            parse_results = await asyncio.gather(*parse_tasks)
            for file_path, result in zip(files, parse_results):
                if result:
                    results[str(file_path)] = result
        else:
            for file_path in files:
                result = await self.parse_file(file_path)
                if result:
                    results[str(file_path)] = result
        
        # Build module index
        modules = self._build_module_index(results)
        
        # Extract functions
        functions = self._extract_all_functions(results)
        
        return {
            "files": results,
            "modules": modules,
            "functions": functions,
            "total_files": len(results),
            "total_errors": sum(len(r.errors) for r in results.values()),
        }
    
    async def parse_file(self, file_path: Path) -> ParseResult | None:
        """Parse a single file"""
        if not file_path.exists():
            return None
        
        # Determine language
        language = self._detect_language(file_path)
        if not language:
            return None
        
        # Check cache
        cache_key = str(file_path)
        if self.config.cache_enabled and cache_key in self.parse_cache:
            cached = self.parse_cache[cache_key]
            # Check if file hasn't changed
            # In production, compare mtime/hash
            return cached
        
        # Parse file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            result = await self._parse_content(content, language, str(file_path))
            
            # Cache result
            if self.config.cache_enabled:
                self.parse_cache[cache_key] = result
            
            return result
        except Exception as e:
            return ParseResult(
                file_path=str(file_path),
                language=language,
                errors=[SyntaxError(message=str(e), line=1, column=0)]
            )
    
    async def _parse_content(self, content: str, language: str, 
                           file_path: str) -> ParseResult:
        """Parse content using Tree-sitter"""
        import time
        start_time = time.time()
        
        errors = []
        tree = None
        
        if TREE_SITTER_AVAILABLE and language in self.parsers:
            parser = self.parsers[language]
            
            # Parse content
            # tree = parser.parse(bytes(content, "utf8"))
            
            # Note: This is a placeholder. In production:
            # - Use actual Tree-sitter parsing
            # - Handle errors from parser
            # - Build SyntaxNode structure
            pass
        
        # For now, create a basic result (in production, parse properly)
        result = ParseResult(
            file_path=file_path,
            language=language,
            tree=None,  # Would be actual tree in production
            errors=errors,
            parse_time_ms=(time.time() - start_time) * 1000,
        )
        
        return result
    
    async def update_incremental(self, changed_files: list[str]) -> dict[str, Any]:
        """
        Perform incremental update for changed files only.
        
        This is critical for performance - we don't reparse the entire
        codebase for small changes.
        """
        results = {}
        
        for file_path in changed_files:
            path = Path(file_path)
            result = await self.parse_file(path)
            if result:
                result.is_incremental = True
                results[file_path] = result
        
        # Update cache
        for file_path, result in results.items():
            self.parse_cache[file_path] = result
        
        return results
    
    def query(self, file_path: str, query: str) -> list[dict]:
        """
        Execute a Tree-sitter query on a parsed file.
        
        This allows pattern matching in the syntax tree.
        
        Example queries:
        - (function_definition name: (identifier) @func_name)
        - (call function: (identifier) @call)
        - (import_statement module: (module) @import)
        """
        if file_path not in self.parse_cache:
            return []
        
        result = self.parse_cache[file_path]
        if not result.tree:
            return []
        
        # Execute query
        # In production: Use tree-sitter query engine
        matches = []
        
        return matches
    
    def get_changed_regions(self, old_content: str, new_content: str) -> list[dict]:
        """
        Identify changed regions between two versions of a file.
        
        This uses Tree-sitter's incremental parsing to find only
        the changed portions of the file.
        """
        # In production, use tree-sitter's edit functionality
        # to get minimal diff regions
        return []
    
    async def _discover_files(self, repo_path: Path) -> list[Path]:
        """Discover all parseable files in the repository"""
        files = []
        
        for root, dirs, filenames in repo_path.walk():
            # Skip hidden and common non-source directories
            dirs[:] = [d for d in dirs if not d.startswith('.') 
                      and d not in ('node_modules', 'venv', '__pycache__', 
                                   'dist', 'build', 'target')]
            
            for filename in filenames:
                path = Path(root) / filename
                if self._detect_language(path):
                    files.append(path)
        
        return files
    
    def _detect_language(self, file_path: Path) -> str | None:
        """Detect programming language from file extension"""
        ext = file_path.suffix.lower()
        
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".h": "c",
            ".hpp": "cpp",
        }
        
        return lang_map.get(ext)
    
    def _build_module_index(self, results: dict[str, ParseResult]) -> dict:
        """Build an index of modules from parse results"""
        modules = {}
        
        for file_path, result in results.items():
            # Determine module from file path
            parts = Path(file_path).parts
            
            # Group by top-level module
            if len(parts) > 1:
                module_path = str(Path(*parts[:-1]))
                if module_path not in modules:
                    modules[module_path] = {
                        "files": [],
                        "functions": [],
                        "classes": [],
                    }
                
                modules[module_path]["files"].append(file_path)
                modules[module_path]["functions"].extend(result.get_functions())
                modules[module_path]["classes"].extend(result.get_classes())
        
        return modules
    
    def _extract_all_functions(self, results: dict[str, ParseResult]) -> dict:
        """Extract all functions across all files"""
        functions = {}
        
        for file_path, result in results.items():
            funcs = result.get_functions()
            for func in funcs:
                func_key = f"{file_path}:{func['name']}"
                functions[func_key] = func
        
        return functions
    
    def get_syntax_summary(self, file_path: str) -> dict:
        """Get a quick syntax summary of a file"""
        if file_path not in self.parse_cache:
            return {}
        
        result = self.parse_cache[file_path]
        
        return {
            "language": result.language,
            "functions": len(result.get_functions()),
            "classes": len(result.get_classes()),
            "imports": len(result.get_imports()),
            "calls": len(result.get_calls()),
            "errors": len(result.errors),
            "parse_time_ms": result.parse_time_ms,
        }
