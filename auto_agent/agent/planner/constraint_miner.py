"""
Constraint Miner
===============
Extracts constraints from code understanding.

This module is part of the Change Planner system.

Key responsibilities:
- Extract invariants that must be preserved
- Identify red-zone modules (never touch without approval)
- Find required tests
- Identify data flow risks
- Find dependency constraints
- Identify security-sensitive symbols
- Find hot paths (performance-critical)
"""

import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field

from agent.planner.contracts import ConstraintSpec

logger = logging.getLogger(__name__)


# Security-sensitive keywords
SECURITY_KEYWORDS = {
    'auth', 'authentication', 'login', 'logout',
    'token', 'jwt', 'oauth', 'session',
    'password', 'secret', 'api_key', 'credential',
    'permission', 'role', 'access_control',
    'encryption', 'decrypt', 'hash', 'signature',
    'payment', 'billing', 'invoice', 'stripe',
    'admin', 'root', 'sudo',
}

# Critical system modules
CRITICAL_MODULES = {
    'kernel', 'core', 'main', 'app',
    'auth', 'security', 'payment', 'billing',
    'database', 'db', 'migration',
    'self_improvement', 'self_edit', 'core',
}

# Hot path indicators
HOT_PATH_KEYWORDS = {
    'hot_path', 'critical_path', 'main_loop',
    'request_handler', 'api_endpoint', 'controller',
    'middleware', 'interceptor',
}


class ConstraintMiner:
    """
    Mines constraints from code understanding.
    
    This is Layer 2 of the Change Planner.
    
    FIXED: Complete implementation with all required extraction.
    """
    
    def __init__(self):
        self.mining_history: List[Dict] = []
    
    def mine(self, code_analysis: Dict[str, Any]) -> ConstraintSpec:
        """
        Main entry point: Extract constraints from code analysis.
        
        Args:
            code_analysis: Output from Code Understanding Engine
            
        Returns:
            ConstraintSpec with all extracted constraints
        """
        logger.info(f"⛏️ ConstraintMiner: Mining constraints from code analysis...")
        
        # Step 1: Extract invariants
        invariants = self._extract_invariants(code_analysis)
        
        # Step 2: Identify red-zone modules
        red_zone_modules = self._identify_red_zones(code_analysis)
        
        # Step 3: Find required tests
        required_tests = self._find_required_tests(code_analysis)
        
        # Step 4: Identify data flow risks
        data_flow_risks = self._identify_data_flow_risks(code_analysis)
        
        # Step 5: Extract dependency constraints
        dependency_constraints = self._extract_dependency_constraints(code_analysis)
        
        # Step 6: Find migration constraints
        migration_constraints = self._find_migration_constraints(code_analysis)
        
        # Step 7: Identify security symbols
        security_symbols = self._identify_security_symbols(code_analysis)
        
        # Step 8: Identify hot paths
        hot_paths = self._identify_hot_paths(code_analysis)
        
        # Create ConstraintSpec
        constraint_spec = ConstraintSpec(
            invariants=invariants,
            red_zone_modules=red_zone_modules,
            required_tests=required_tests,
            data_flow_risks=data_flow_risks,
            dependency_constraints=dependency_constraints,
            migration_constraints=migration_constraints,
            security_symbols=security_symbols,
            hot_paths=hot_paths
        )
        
        # Record history
        self.mining_history.append({
            'analysis_keys': list(code_analysis.keys()) if code_analysis else [],
            'invariants_count': len(invariants),
            'red_zones_count': len(red_zone_modules)
        })
        
        logger.info(f"✅ ConstraintMiner: Mined {len(invariants)} invariants, "
                   f"{len(red_zone_modules)} red zones")
        
        return constraint_spec
    
    def _extract_invariants(self, analysis: Dict) -> List[str]:
        """
        Extract code invariants that must be preserved.
        
        Examples:
        - "auth token must be validated before every request"
        - "billing calculation must use decimal precision"
        - "user_id cannot be null after login"
        """
        invariants = []
        
        if not analysis:
            return invariants
        
        # Extract from symbol analysis
        symbols = analysis.get('symbols', {})
        for symbol_name, symbol_data in symbols.items():
            if isinstance(symbol_data, dict):
                # Check for assertions/invariants
                if symbol_data.get('has_invariant'):
                    invariants.append(f"{symbol_name}_invariant_preserved")
                
                # Check for critical contracts
                if symbol_data.get('critical'):
                    invariants.append(f"{symbol_name}_contract_maintained")
                
                # Check for return type contracts
                if symbol_data.get('return_type'):
                    invariants.append(f"{symbol_name}_return_type_preserved")
        
        # Extract from function analysis
        functions = analysis.get('functions', {})
        for func_name, func_data in functions.items():
            if isinstance(func_data, dict):
                # Check preconditions
                if func_data.get('preconditions'):
                    invariants.append(f"{func_name}_preconditions_hold")
                
                # Check postconditions
                if func_data.get('postconditions'):
                    invariants.append(f"{func_name}_postconditions_hold")
        
        # Extract from class analysis
        classes = analysis.get('classes', {})
        for class_name, class_data in classes.items():
            if isinstance(class_data, dict):
                # Check class invariants
                if class_data.get('invariants'):
                    for inv in class_data['invariants']:
                        invariants.append(f"{class_name}_{inv}")
                
                # Check inheritance contracts
                if class_data.get('parent_classes'):
                    invariants.append(f"{class_name}_inheritance_contract")
        
        return list(set(invariants))  # Remove duplicates
    
    def _identify_red_zones(self, analysis: Dict) -> Set[str]:
        """
        Identify red-zone modules that require extra approval.
        
        FIXED: Comprehensive red-zone detection.
        """
        red_zones = set()
        
        if not analysis:
            return red_zones
        
        # Check file paths
        files = analysis.get('files', [])
        for file_path in files:
            file_lower = str(file_path).lower()
            
            # Check critical modules
            for critical in CRITICAL_MODULES:
                if critical in file_lower:
                    red_zones.add(str(file_path))
        
        # Check symbols
        symbols = analysis.get('symbols', {})
        for symbol_name in symbols:
            symbol_lower = str(symbol_name).lower()
            
            # Check security keywords
            for sec_keyword in SECURITY_KEYWORDS:
                if sec_keyword in symbol_lower:
                    red_zones.add(f"symbol:{symbol_name}")
        
        # Check functions
        functions = analysis.get('functions', {})
        for func_name in functions:
            func_lower = str(func_name).lower()
            
            for sec_keyword in SECURITY_KEYWORDS:
                if sec_keyword in func_lower:
                    red_zones.add(f"function:{func_name}")
        
        # Check classes
        classes = analysis.get('classes', {})
        for class_name in classes:
            class_lower = str(class_name).lower()
            
            for critical in CRITICAL_MODULES:
                if critical in class_lower:
                    red_zones.add(f"class:{class_name}")
        
        return red_zones
    
    def _find_required_tests(self, analysis: Dict) -> List[str]:
        """
        Find required tests for the change.
        
        FIXED: Test detection based on code analysis.
        """
        required_tests = []
        
        if not analysis:
            return required_tests
        
        # Check for existing tests
        existing_tests = analysis.get('tests', [])
        
        # Check for test patterns
        functions = analysis.get('functions', {})
        for func_name in functions:
            # Add unit test
            required_tests.append(f"test_{func_name}")
            
            # Add integration test if function is API-facing
            func_data = functions[func_name]
            if isinstance(func_data, dict):
                if func_data.get('is_api') or func_data.get('is_endpoint'):
                    required_tests.append(f"test_{func_name}_integration")
        
        # Check for classes
        classes = analysis.get('classes', {})
        for class_name in classes:
            required_tests.append(f"Test{class_name}")
        
        # Include existing tests
        for test in existing_tests:
            if test not in required_tests:
                required_tests.append(test)
        
        return list(set(required_tests))
    
    def _identify_data_flow_risks(self, analysis: Dict) -> List[str]:
        """
        Identify data flow risks.
        
        Examples:
        - "user_input flows to SQL query without sanitization"
        - "file path from user input used in os.path.join"
        """
        risks = []
        
        if not analysis:
            return risks
        
        # Check for data flow analysis
        data_flow = analysis.get('data_flow', {})
        
        for flow_path, flow_data in data_flow.items():
            if isinstance(flow_data, dict):
                # Check for unsafe flows
                if flow_data.get('tainted'):
                    risks.append(f"tainted_flow:{flow_path}")
                
                # Check for SQL injection risks
                if flow_data.get('sql_injection_risk'):
                    risks.append(f"sql_injection:{flow_path}")
                
                # Check for path traversal risks
                if flow_data.get('path_traversal_risk'):
                    risks.append(f"path_traversal:{flow_path}")
        
        # Check for external inputs
        external_inputs = analysis.get('external_inputs', [])
        for inp in external_inputs:
            risks.append(f"external_input:{inp}")
        
        return risks
    
    def _extract_dependency_constraints(self, analysis: Dict) -> Dict[str, Any]:
        """
        Extract dependency constraints.
        
        FIXED: Complete dependency analysis.
        """
        constraints = {}
        
        if not analysis:
            return constraints
        
        # Check dependencies
        dependencies = analysis.get('dependencies', {})
        
        for dep_name, dep_data in dependencies.items():
            if isinstance(dep_data, dict):
                # Version constraints
                if dep_data.get('version_constraint'):
                    constraints[f"{dep_name}_version"] = dep_data['version_constraint']
                
                # API compatibility
                if dep_data.get('breaking_change'):
                    constraints[f"{dep_name}_breaking"] = True
        
        # Check for circular dependencies
        circular = analysis.get('circular_dependencies', [])
        if circular:
            constraints['circular_deps'] = circular
        
        return constraints
    
    def _find_migration_constraints(self, analysis: Dict) -> List[str]:
        """
        Find migration constraints.
        
        Examples:
        - "must migrate user table before adding new columns"
        - "backup required before schema change"
        """
        constraints = []
        
        if not analysis:
            return constraints
        
        # Check for migrations
        migrations = analysis.get('migrations', [])
        
        for migration in migrations:
            if isinstance(migration, dict):
                migration_type = migration.get('type', 'unknown')
                constraints.append(f"migration_required:{migration_type}")
        
        # Check for schema changes
        if analysis.get('schema_changed'):
            constraints.append("schema_backup_required")
        
        # Check for data migrations
        if analysis.get('data_migration_required'):
            constraints.append("data_migration_order_matters")
        
        return constraints
    
    def _identify_security_symbols(self, analysis: Dict) -> Set[str]:
        """
        Identify security-sensitive symbols.
        
        FIXED: Comprehensive security detection.
        """
        security_symbols = set()
        
        if not analysis:
            return security_symbols
        
        # Check symbols
        symbols = analysis.get('symbols', {})
        for symbol_name in symbols:
            symbol_lower = str(symbol_name).lower()
            
            for sec_keyword in SECURITY_KEYWORDS:
                if sec_keyword in symbol_lower:
                    security_symbols.add(symbol_name)
        
        # Check functions
        functions = analysis.get('functions', {})
        for func_name in functions:
            func_lower = str(func_name).lower()
            
            for sec_keyword in SECURITY_KEYWORDS:
                if sec_keyword in func_lower:
                    security_symbols.add(func_name)
        
        # Check classes
        classes = analysis.get('classes', {})
        for class_name in classes:
            class_lower = str(class_name).lower()
            
            for sec_keyword in SECURITY_KEYWORDS:
                if sec_keyword in class_lower:
                    security_symbols.add(class_name)
        
        return security_symbols
    
    def _identify_hot_paths(self, analysis: Dict) -> Set[str]:
        """
        Identify performance-critical hot paths.
        
        FIXED: Hot path detection.
        """
        hot_paths = set()
        
        if not analysis:
            return hot_paths
        
        # Check for hot path indicators
        functions = analysis.get('functions', {})
        for func_name, func_data in functions.items():
            func_lower = str(func_name).lower()
            
            # Check keywords
            for keyword in HOT_PATH_KEYWORDS:
                if keyword in func_lower:
                    hot_paths.add(func_name)
            
            # Check annotations
            if isinstance(func_data, dict):
                if func_data.get('hot_path') or func_data.get('performance_critical'):
                    hot_paths.add(func_name)
        
        # Check for frequently called functions
        call_graph = analysis.get('call_graph', {})
        for func_name, callers in call_graph.items():
            if isinstance(callers, list) and len(callers) > 10:
                hot_paths.add(func_name)
        
        return hot_paths
    
    def get_mining_stats(self) -> Dict:
        """Get mining statistics."""
        return {
            'total_minings': len(self.mining_history),
            'recent_minings': self.mining_history[-10:]
        }
