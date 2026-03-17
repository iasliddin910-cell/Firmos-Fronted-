"""
CapabilityGapGenerator - Gap-Driven Task Generation Module

Bu modul capability heatmap bo'yicha yangi tasklar yaratadi.

Misol:
- retrieval zaif → retrieval-heavy tasks
- browser recovery zaif → brittle selector flows
- self-mod safety zaif → sandboxed self-patch tasks

Bu modul No1 World+ tizimning eng muhim qismlaridan biri.
Tizim o'zining keyingi imtihonini o'zi yaratadi.

Policy 5: Capability-gap driven generation - yangi tasklar tasodifiy emas.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class CapabilityType(Enum):
    """Types of capabilities being evaluated"""
    CODE_GENERATION = "code_generation"
    CODE_EDIT = "code_edit"
    CODE_UNDERSTANDING = "code_understanding"
    RETRIEVAL = "retrieval"
    BROWSER_AUTOMATION = "browser_automation"
    TOOL_USE = "tool_use"
    SELF_MODIFICATION = "self_modification"
    DEBUGGING = "debugging"
    PLANNING = "planning"
    AMBIGUITY_HANDLING = "ambiguity_handling"
    VERIFICATION = "verification"
    RETRY_RECOVERY = "retry_recovery"


class GapSeverity(Enum):
    """Severity of capability gap"""
    CRITICAL = "critical"    # <30% success
    HIGH = "high"           # 30-50% success
    MODERATE = "moderate"   # 50-70% success
    LOW = "low"             # 70-85% success


@dataclass
class CapabilityScore:
    """Score for a specific capability"""
    capability: CapabilityType
    score: float           # 0-1 success rate
    task_count: int        # Number of tasks evaluated
    confidence: float      # Confidence in score
    trend: str             # improving, stable, declining


@dataclass
class CapabilityGap:
    """A gap in agent capability"""
    capability: CapabilityType
    severity: GapSeverity
    current_score: float
    target_score: float
    gap_size: float
    priority: float
    recommended_tasks: List[str]


@dataclass
class GeneratedTaskSpec:
    """Specification for a generated task"""
    task_id: str
    capability_focus: CapabilityType
    description: str
    difficulty: float
    success_criteria: List[str]
    hints: List[str]
    constraints: Dict[str, Any]
    expected_capability_improvement: float


class CapabilityGapGenerator:
    """
    Generates tasks based on capability gaps.
    
    Bu modul:
    1. Capability heatmapdan zaif joylarni topadi
    2. Har bir gap uchun maxsus tasklar yaratadi
    3. Tasklar targeted bo'lib, aniq capabilityni rivojlantiradi
    """
    
    # Capability-specific task templates
    CAPABILITY_TEMPLATES = {
        CapabilityType.CODE_GENERATION: [
            "Generate {language} code for {scenario}",
            "Write a {function_type} that handles {edge_case}",
            "Create a complete {module} implementation"
        ],
        CapabilityType.CODE_EDIT: [
            "Fix the bug in {file} while preserving {constraint}",
            "Refactor {code_pattern} to improve {aspect}",
            "Apply patch to resolve {issue_type}"
        ],
        CapabilityType.CODE_UNDERSTANDING: [
            "Analyze {codebase} and explain {aspect}",
            "Find the root cause of {problem}",
            "Document the behavior of {component}"
        ],
        CapabilityType.RETRIEVAL: [
            "Find information about {topic} in {source}",
            "Search and extract {data_type} from {location}",
            "Locate the relevant code for {functionality}"
        ],
        CapabilityType.BROWSER_AUTOMATION: [
            "Navigate to {url} and extract {data}",
            "Fill form with {data} and submit",
            "Handle dynamic element {element_type}"
        ],
        CapabilityType.TOOL_USE: [
            "Use {tool} to accomplish {goal}",
            "Chain {tool1} and {tool2} for {task}",
            "Select optimal tool for {scenario}"
        ],
        CapabilityType.SELF_MODIFICATION: [
            "Improve the agent's own code for {aspect}",
            "Apply targeted fix to {component}",
            "Self-patch to resolve {issue}"
        ],
        CapabilityType.DEBUGGING: [
            "Debug and fix {error_type} in {location}",
            "Diagnose why {behavior} is happening",
            "Find and resolve the race condition"
        ],
        CapabilityType.PLANNING: [
            "Create a plan to accomplish {goal}",
            "Break down {complex_task} into steps",
            "Coordinate multiple subtasks for {objective}"
        ],
        CapabilityType.AMBIGUITY_HANDLING: [
            "Handle incomplete specification for {task}",
            "Clarify and resolve ambiguity in {requirement}",
            "Make reasonable assumptions for {unclear_aspect}"
        ],
        CapabilityType.VERIFICATION: [
            "Verify that {solution} meets {criteria}",
            "Test {code} for edge cases",
            "Validate the fix for {issue}"
        ],
        CapabilityType.RETRY_RECOVERY: [
            "Recover from {failure_type} and complete {task}",
            "Retry strategy for {error_scenario}",
            "Handle {tool} failure and adapt"
        ]
    }
    
    # Gap severity thresholds
    GAP_SEVERITY_THRESHOLDS = {
        GapSeverity.CRITICAL: (0.0, 0.3),
        GapSeverity.HIGH: (0.3, 0.5),
        GapSeverity.MODERATE: (0.5, 0.7),
        GapSeverity.LOW: (0.7, 0.85)
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rng = random.Random(self.config.get('seed', 42))
        self.capability_history: Dict[CapabilityType, List[CapabilityScore]] = {}
        
    def analyze_capability_gaps(
        self,
        capability_scores: List[CapabilityScore],
        target_scores: Optional[Dict[CapabilityType, float]] = None
    ) -> List[CapabilityGap]:
        """
        Analyze capability scores and identify gaps.
        
        Args:
            capability_scores: Current scores for each capability
            target_scores: Target scores to reach (default: 0.85)
            
        Returns:
            List of CapabilityGap ordered by priority
        """
        if target_scores is None:
            target_scores = {cap: 0.85 for cap in CapabilityType}
        
        gaps = []
        
        for score in capability_scores:
            target = target_scores.get(score.capability, 0.85)
            gap_size = target - score.score
            
            if gap_size > 0:
                severity = self._determine_severity(score.score)
                priority = self._calculate_priority(
                    gap_size, score.confidence, score.trend
                )
                
                gap = CapabilityGap(
                    capability=score.capability,
                    severity=severity,
                    current_score=score.score,
                    target_score=target,
                    gap_size=gap_size,
                    priority=priority,
                    recommended_tasks=self._get_task_recommendations(
                        score.capability, severity
                    )
                )
                gaps.append(gap)
        
        # Sort by priority
        gaps.sort(key=lambda g: g.priority, reverse=True)
        
        return gaps
    
    def generate_tasks_for_gap(
        self,
        gap: CapabilityGap,
        count: int = 5,
        difficulty_range: Tuple[float, float] = (0.4, 0.7)
    ) -> List[GeneratedTaskSpec]:
        """
        Generate tasks specifically for a capability gap.
        
        Args:
            gap: The capability gap to generate tasks for
            count: Number of tasks to generate
            difficulty_range: Target difficulty range for tasks
            
        Returns:
            List of GeneratedTaskSpec
        """
        tasks = []
        capability = gap.capability
        
        templates = self.CAPABILITY_TEMPLATES.get(capability, [
            "Complete the task: {description}"
        ])
        
        for i in range(count):
            # Select template
            template = self.rng.choice(templates)
            
            # Generate specific parameters
            params = self._generate_task_params(capability, gap.severity)
            
            # Fill template
            description = template.format(**params)
            
            # Calculate difficulty based on gap severity
            difficulty = self._calculate_task_difficulty(
                gap, difficulty_range, i
            )
            
            # Generate success criteria
            criteria = self._generate_success_criteria(capability, params)
            
            # Generate hints
            hints = self._generate_hints(capability, gap.severity)
            
            # Generate constraints
            constraints = self._generate_constraints(capability, gap.severity)
            
            task_id = f"gen_{capability.value}_{gap.severity.value}_{i}_{self.rng.randint(1000, 9999)}"
            
            task = GeneratedTaskSpec(
                task_id=task_id,
                capability_focus=capability,
                description=description,
                difficulty=difficulty,
                success_criteria=criteria,
                hints=hints,
                constraints=constraints,
                expected_capability_improvement=gap.gap_size * 0.2
            )
            
            tasks.append(task)
        
        return tasks
    
    def generate_comprehensive_task_set(
        self,
        gaps: List[CapabilityGap],
        tasks_per_gap: int = 3
    ) -> List[GeneratedTaskSpec]:
        """
        Generate a comprehensive set of tasks covering all gaps.
        
        Args:
            gaps: List of capability gaps
            tasks_per_gap: Number of tasks per gap
            
        Returns:
            Combined list of GeneratedTaskSpec
        """
        all_tasks = []
        
        for gap in gaps:
            # Adjust difficulty based on gap severity
            if gap.severity == GapSeverity.CRITICAL:
                diff_range = (0.6, 0.85)
            elif gap.severity == GapSeverity.HIGH:
                diff_range = (0.5, 0.75)
            elif gap.severity == GapSeverity.MODERATE:
                diff_range = (0.4, 0.6)
            else:
                diff_range = (0.3, 0.5)
            
            tasks = self.generate_tasks_for_gap(
                gap,
                count=tasks_per_gap,
                difficulty_range=diff_range
            )
            all_tasks.extend(tasks)
        
        return all_tasks
    
    def _determine_severity(self, score: float) -> GapSeverity:
        """Determine gap severity from score"""
        for severity, (low, high) in self.GAP_SEVERITY_THRESHOLDS.items():
            if low <= score < high:
                return severity
        return GapSeverity.LOW
    
    def _calculate_priority(
        self,
        gap_size: float,
        confidence: float,
        trend: str
    ) -> float:
        """Calculate priority for addressing a gap"""
        priority = gap_size * 0.5
        
        # Higher confidence = higher priority
        priority += confidence * 0.3
        
        # Declining trend = higher priority
        if trend == "declining":
            priority += 0.2
        elif trend == "stable":
            priority += 0.1
        
        return priority
    
    def _get_task_recommendations(
        self,
        capability: CapabilityType,
        severity: GapSeverity
    ) -> List[str]:
        """Get task recommendations for a capability gap"""
        recommendations = {
            CapabilityType.CODE_GENERATION: [
                "Generate code with complex logic",
                "Handle edge cases in generation",
                "Create complete implementations"
            ],
            CapabilityType.RETRIEVAL: [
                "Search in large codebases",
                "Extract information from docs",
                "Find relevant code patterns"
            ],
            CapabilityType.BROWSER_AUTOMATION: [
                "Handle dynamic content",
                "Work with complex selectors",
                "Manage browser state"
            ],
            CapabilityType.SELF_MODIFICATION: [
                "Self-patch with safety",
                "Targeted code improvements",
                "Delta-based modifications"
            ],
            CapabilityType.DEBUGGING: [
                "Debug complex errors",
                "Find root causes",
                "Handle race conditions"
            ]
        }
        
        return recommendations.get(capability, [
            f"Practice {capability.value} tasks",
            f"Improve {capability.value} accuracy"
        ])
    
    def _generate_task_params(
        self,
        capability: CapabilityType,
        severity: GapSeverity
    ) -> Dict[str, str]:
        """Generate parameters for task template"""
        param_pools = {
            "language": ["Python", "JavaScript", "TypeScript", "Rust", "Go"],
            "scenario": ["API handling", "data processing", "error handling", "concurrency"],
            "function_type": ["recursive", "async", "class-based", "functional"],
            "edge_case": ["null values", "race conditions", "overflow", "unicode"],
            "module": ["auth", "database", "cache", "api"],
            "file": ["main.py", "utils.py", "handler.js", "service.ts"],
            "constraint": ["existing tests", "API compatibility", "performance"],
            "code_pattern": ["nested loops", "global state", "callback hell"],
            "aspect": ["readability", "performance", "maintainability"],
            "issue_type": ["memory leak", "race condition", "null pointer"],
            "codebase": ["large project", "legacy system", "microservice"],
            "problem": ["performance issue", "memory leak", "crash"],
            "component": ["authentication", "caching", "queue"],
            "topic": ["API", "configuration", "architecture"],
            "source": ["documentation", "code comments", "issues"],
            "data_type": ["function signatures", "config values", "error messages"],
            "location": ["multiple files", "external dependency", "generated code"],
            "functionality": ["authentication", "file handling", "data processing"],
            "url": ["dynamic content", "SPA", "authenticated page"],
            "data": ["form data", "search query", "filter criteria"],
            "element_type": ["dropdown", "modal", "infinite scroll"],
            "tool": ["grep", "sed", "git", "docker"],
            "goal": ["code search", "file modification", "container setup"],
            "task": ["data extraction", "text processing", "file conversion"],
            "aspect": ["error handling", "performance", "type safety"],
            "component": ["core logic", "API client", "data layer"],
            "issue": ["bug", "performance", "security"],
            "error_type": ["runtime", "compilation", "logic"],
            "location": ["async code", "database queries", "API calls"],
            "behavior": ["slow response", "crash", "incorrect output"],
            "goal": ["deploy", "migrate", "optimize"],
            "complex_task": ["system redesign", "migration", "refactoring"],
            "task": ["build", "test", "deploy"],
            "objective": ["data pipeline", "API integration", "feature rollout"],
            "task": ["implement feature", "fix bug", "optimize"],
            "requirement": ["API design", "UI specification", "data format"],
            "unclear_aspect": ["input format", "output format", "behavior"],
            "solution": ["algorithm", "implementation", "configuration"],
            "criteria": ["performance", "correctness", "compatibility"],
            "code": ["function", "class", "module"],
            "issue": ["bug", "vulnerability", "performance"],
            "failure_type": ["timeout", "authentication", "resource"],
            "task": ["data processing", "API call", "file operation"],
            "error_scenario": ["network failure", "invalid input", "service down"],
            "tool": ["API call", "file read", "command execution"]
        }
        
        # Select relevant parameters for capability
        if capability in param_pools:
            pool = param_pools[capacity]
            params = {
                key: self.rng.choice(values)
                for key, values in param_pools.items()
                if values
            }
        else:
            params = {"description": f"Task for {capability.value}"}
        
        return params
    
    def _calculate_task_difficulty(
        self,
        gap: CapabilityGap,
        difficulty_range: Tuple[float, float],
        index: int
    ) -> float:
        """Calculate difficulty for a task"""
        base_difficulty = difficulty_range[0] + (
            (difficulty_range[1] - difficulty_range[0]) * 
            (index / 5)  # Progressive difficulty
        )
        
        # Adjust for gap severity
        severity_bonus = {
            GapSeverity.CRITICAL: 0.1,
            GapSeverity.HIGH: 0.05,
            GapSeverity.MODERATE: 0.0,
            GapSeverity.LOW: -0.05
        }.get(gap.severity, 0.0)
        
        return min(0.95, base_difficulty + severity_bonus)
    
    def _generate_success_criteria(
        self,
        capability: CapabilityType,
        params: Dict[str, str]
    ) -> List[str]:
        """Generate success criteria for a task"""
        criteria_templates = {
            CapabilityType.CODE_GENERATION: [
                "Code compiles without errors",
                "Passes all unit tests",
                "Meets performance requirements"
            ],
            CapabilityType.RETRIEVAL: [
                "Finds correct information",
                "Completes within time limit",
                "Handles not found case"
            ],
            CapabilityType.BROWSER_AUTOMATION: [
                "Completes navigation successfully",
                "Extracts correct data",
                "Handles errors gracefully"
            ],
            CapabilityType.SELF_MODIFICATION: [
                "Applies change safely",
                "Preserves existing functionality",
                "Passes verification tests"
            ]
        }
        
        return criteria_templates.get(capability, [
            "Task completed successfully",
            "Meets quality standards"
        ])
    
    def _generate_hints(
        self,
        capability: CapabilityType,
        severity: GapSeverity
    ) -> List[str]:
        """Generate hints for task completion"""
        base_hints = [
            "Break down the task into smaller steps",
            "Verify each step before proceeding",
            "Test edge cases"
        ]
        
        # Add capability-specific hints
        capability_hints = {
            CapabilityType.RETRIEVAL: [
                "Start with broad search, then narrow down",
                "Check multiple sources for verification"
            ],
            CapabilityType.SELF_MODIFICATION: [
                "Make small, targeted changes",
                "Test after each modification"
            ],
            CapabilityType.DEBUGGING: [
                "Add logging to trace the issue",
                "Start with simplest test case"
            ]
        }
        
        hints = base_hints.copy()
        hints.extend(capability_hints.get(capability, []))
        
        return hints
    
    def _generate_constraints(
        self,
        capability: CapabilityType,
        severity: GapSeverity
    ) -> Dict[str, Any]:
        """Generate constraints for the task"""
        constraints = {
            "time_limit": 300,  # 5 minutes
            "max_attempts": 3,
            "allow_tools": True
        }
        
        # Add severity-specific constraints
        if severity == GapSeverity.CRITICAL:
            constraints["time_limit"] = 600
            constraints["max_attempts"] = 5
        elif severity == GapSeverity.HIGH:
            constraints["time_limit"] = 450
            constraints["max_attempts"] = 4
        
        return constraints
    
    def get_gap_report(
        self,
        gaps: List[CapabilityGap]
    ) -> Dict[str, Any]:
        """Generate report on capability gaps"""
        return {
            "total_gaps": len(gaps),
            "critical_gaps": len([g for g in gaps if g.severity == GapSeverity.CRITICAL]),
            "high_gaps": len([g for g in gaps if g.severity == GapSeverity.HIGH]),
            "gaps": [
                {
                    "capability": g.capability.value,
                    "severity": g.severity.value,
                    "current_score": g.current_score,
                    "target_score": g.target_score,
                    "gap_size": g.gap_size,
                    "priority": g.priority
                }
                for g in gaps[:10]
            ]
        }


__all__ = [
    'CapabilityGapGenerator',
    'CapabilityType',
    'GapSeverity',
    'CapabilityScore',
    'CapabilityGap',
    'GeneratedTaskSpec'
]
