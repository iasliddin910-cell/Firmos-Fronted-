"""
Runtime Understanding Layer
==========================

This layer provides practical understanding of how code actually behaves
at runtime through tracing and profiling.

Key capabilities:
- Integration test traces
- API call traces
- Tool execution traces
- Exception tracking
- Latency hotspot identification
- Retry/failure loop detection

This layer bridges the gap between "what the code says" and "what the code does".
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TraceEventType(Enum):
    """Types of trace events"""
    FUNCTION_ENTRY = "function_entry"
    FUNCTION_EXIT = "function_exit"
    FUNCTION_CALL = "function_call"
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    DATABASE_QUERY = "database_query"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK_REQUEST = "network_request"
    NETWORK_RESPONSE = "network_response"
    EXCEPTION = "exception"
    ERROR = "error"
    RETRY = "retry"
    TIMEOUT = "timeout"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"


@dataclass
class TraceEvent:
    """Represents a single trace event"""
    event_type: TraceEventType
    timestamp: str
    trace_id: str
    span_id: str
    
    # Event details
    name: str
    category: str = ""
    
    # Location
    file_path: str = ""
    function_name: str = ""
    line_number: int = 0
    
    # Timing
    duration_ms: float = 0.0
    
    # Data
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    
    # Context
    parent_span_id: str = ""
    thread_id: str = ""
    process_id: str = ""


@dataclass
class ExecutionTrace:
    """Complete execution trace"""
    trace_id: str
    started_at: str
    ended_at: str = ""
    duration_ms: float = 0.0
    
    events: list[TraceEvent] = field(default_factory=list)
    
    # Summary
    total_calls: int = 0
    total_errors: int = 0
    total_retries: int = 0
    
    # Performance
    slow_calls: list[dict] = field(default_factory=list)
    error_calls: list[dict] = field(default_factory=list)
    
    # Statistics
    call_counts: dict = field(default_factory=dict)  # function -> count
    error_counts: dict = field(default_factory=dict)  # error_type -> count


@dataclass
class LatencyHotspot:
    """Represents a performance hotspot"""
    function_path: str
    total_time_ms: float
    call_count: int
    avg_time_ms: float
    max_time_ms: float
    percentage_of_total: float
    
    # Analysis
    is_n_plus_one: bool = False
    has_retry_loop: bool = False
    has_blocking_call: bool = False
    suggestions: list[str] = field(default_factory=list)


@dataclass
class RuntimePattern:
    """Represents a runtime behavior pattern"""
    pattern_type: str
    description: str
    
    # Pattern details
    functions_involved: list[str] = field(default_factory=list)
    frequency: int = 0
    severity: str = "low"  # low, medium, high
    
    # Suggestions
    recommendations: list[str] = field(default_factory=list)


class RuntimeUnderstandingLayer:
    """
    Runtime Understanding Layer
    
    This layer provides practical understanding through:
    - Execution tracing
    - Performance profiling
    - Error pattern detection
    - Runtime behavior analysis
    
    Key insights:
    - Theory vs practice: Code that "should work" may have runtime issues
    - Hidden bottlenecks: Slow calls not visible in static analysis
    - Retry storms: Exponential backoff failures
    - Cascading failures: One error causing many more
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.max_trace_depth = config.max_trace_depth
        
        # Trace storage
        self.traces: dict[str, ExecutionTrace] = {}
        self.active_traces: dict[str, ExecutionTrace] = {}
        
        # Analysis results
        self.latency_hotspots: list[LatencyHotspot] = []
        self.runtime_patterns: list[RuntimePattern] = []
        
        # Profiler (in production, would use actual profiling tools)
        self.profiler = None
    
    async def collect_traces(self, repo_path: Path) -> dict[str, Any]:
        """
        Collect runtime traces from the codebase.
        
        This would typically involve:
        1. Running integration tests
        2. Instrumenting the application
        3. Collecting APM/trace data
        """
        traces = {}
        
        # In production, would:
        # 1. Run test suite with tracing enabled
        # 2. Collect OpenTelemetry/traces
        # 3. Analyze logs for patterns
        
        # For now, create a placeholder structure
        traces = {
            "traces": [],
            "hotspots": [],
            "patterns": [],
            "statistics": {
                "total_traces": 0,
                "total_events": 0,
                "error_rate": 0.0,
            },
        }
        
        return traces
    
    async def trace_execution(self, test_path: str, 
                            context: dict) -> ExecutionTrace:
        """
        Trace a specific execution (e.g., test run).
        
        Returns detailed trace with timing and events.
        """
        trace = ExecutionTrace(
            trace_id=f"trace-{datetime.now().timestamp()}",
            started_at=datetime.now().isoformat(),
        )
        
        # In production, would:
        # 1. Instrument code or use existing tracing
        # 2. Run the target
        # 3. Collect all events
        
        return trace
    
    def analyze_trace(self, trace: ExecutionTrace) -> dict:
        """Analyze a trace for patterns and issues"""
        analysis = {
            "summary": {
                "total_events": len(trace.events),
                "total_calls": trace.total_calls,
                "errors": trace.total_errors,
                "retries": trace.total_retries,
            },
            "slow_calls": trace.slow_calls,
            "error_calls": trace.error_calls,
            "call_counts": trace.call_counts,
        }
        
        return analysis
    
    def find_latency_hotspots(self, traces: list[ExecutionTrace]) -> list[LatencyHotspot]:
        """Identify performance hotspots from traces"""
        hotspots = []
        
        # Aggregate timing data
        function_times: dict[str, list[float]] = {}
        
        for trace in traces:
            for event in trace.events:
                if event.event_type == TraceEventType.FUNCTION_EXIT:
                    if event.name not in function_times:
                        function_times[event.name] = []
                    function_times[event.name].append(event.duration_ms)
        
        # Calculate statistics
        total_time = sum(
            sum(times) 
            for times in function_times.values()
        )
        
        for func_name, times in function_times.items():
            if not times:
                continue
            
            total_func_time = sum(times)
            avg_time = total_func_time / len(times)
            max_time = max(times)
            
            hotspot = LatencyHotspot(
                function_path=func_name,
                total_time_ms=total_func_time,
                call_count=len(times),
                avg_time_ms=avg_time,
                max_time_ms=max_time,
                percentage_of_total=(total_func_time / total_time * 100) if total_time > 0 else 0,
            )
            
            # Analyze for patterns
            if len(times) > 10 and avg_time < 1.0:
                # Many calls with low average - potential N+1
                hotspot.is_n_plus_one = True
                hotspot.suggestions.append(
                    "Potential N+1 query detected. Consider batching."
                )
            
            if max_time > avg_time * 10:
                hotspot.has_blocking_call = True
                hotspot.suggestions.append(
                    "High variance in call times. Check for blocking operations."
                )
            
            hotspots.append(hotspot)
        
        # Sort by total time
        hotspots.sort(key=lambda h: h.total_time_ms, reverse=True)
        
        self.latency_hotspots = hotspots[:10]  # Top 10
        return self.latency_hotspots
    
    def detect_runtime_patterns(self, traces: list[ExecutionTrace]) -> list[RuntimePattern]:
        """Detect common runtime behavior patterns"""
        patterns = []
        
        # Pattern 1: Retry Storms
        retry_counts: dict[str, int] = {}
        
        for trace in traces:
            for event in trace.events:
                if event.event_type == TraceEventType.RETRY:
                    key = f"{event.name}:{event.metadata.get('error', 'unknown')}"
                    retry_counts[key] = retry_counts.get(key, 0) + 1
        
        for key, count in retry_counts.items():
            if count > 3:
                func_name, error = key.split(":", 1)
                patterns.append(RuntimePattern(
                    pattern_type="retry_storm",
                    description=f"Function '{func_name}' retried {count} times",
                    functions_involved=[func_name],
                    frequency=count,
                    severity="high",
                    recommendations=[
                        "Add circuit breaker pattern",
                        "Review retry logic and backoff",
                        "Check for downstream unavailability",
                    ],
                ))
        
        # Pattern 2: Cascading Errors
        error_sequences = self._find_error_sequences(traces)
        
        for seq in error_sequences:
            if len(seq) > 2:
                patterns.append(RuntimePattern(
                    pattern_type="cascading_failure",
                    description=f"Cascading error sequence: {' -> '.join(seq)}",
                    functions_involved=seq,
                    severity="high",
                    recommendations=[
                        "Add error handling boundaries",
                        "Implement bulkhead pattern",
                        "Review failure isolation",
                    ],
                ))
        
        # Pattern 3: Slow Endpoints
        slow_endpoints = self._find_slow_endpoints(traces)
        
        for endpoint in slow_endpoints:
            patterns.append(RuntimePattern(
                pattern_type="slow_endpoint",
                description=f"Endpoint '{endpoint['path']}' averages {endpoint['avg_ms']}ms",
                functions_involved=[endpoint["handler"]],
                frequency=endpoint["count"],
                severity="medium",
                recommendations=[
                    "Profile the handler",
                    "Check database queries",
                    "Consider caching",
                ],
            ))
        
        # Pattern 4: Memory Leaks (detected via increasing memory usage)
        # Would analyze memory trends over time
        
        self.runtime_patterns = patterns
        return patterns
    
    def _find_error_sequences(self, traces: list[ExecutionTrace]) -> list[list[str]]:
        """Find sequences of errors that cascade"""
        sequences = []
        
        for trace in traces:
            error_sequence = []
            
            for event in trace.events:
                if event.event_type in (TraceEventType.EXCEPTION, TraceEventType.ERROR):
                    error_sequence.append(event.name)
                elif error_sequence and event.event_type == TraceEventType.FUNCTION_EXIT:
                    if len(error_sequence) > 1:
                        sequences.append(error_sequence[:])
                    error_sequence = []
        
        return sequences
    
    def _find_slow_endpoints(self, traces: list[ExecutionTrace]) -> list[dict]:
        """Find slow HTTP endpoints"""
        endpoint_times: dict[str, dict] = {}
        
        for trace in traces:
            for event in trace.events:
                if event.event_type == TraceEventType.API_REQUEST:
                    path = event.metadata.get("path", "unknown")
                    
                    if path not in endpoint_times:
                        endpoint_times[path] = {
                            "times": [],
                            "handler": event.name,
                            "count": 0,
                        }
                    
                    endpoint_times[path]["count"] += 1
                
                elif event.event_type == TraceEventType.API_RESPONSE:
                    path = event.metadata.get("path", "unknown")
                    
                    if path in endpoint_times:
                        endpoint_times[path]["times"].append(event.duration_ms)
        
        slow_endpoints = []
        
        for path, data in endpoint_times.items():
            if data["times"]:
                avg_ms = sum(data["times"]) / len(data["times"])
                
                if avg_ms > 1000:  # Over 1 second
                    slow_endpoints.append({
                        "path": path,
                        "handler": data["handler"],
                        "avg_ms": avg_ms,
                        "count": data["count"],
                    })
        
        return slow_endpoints
    
    def merge_runtime_with_code_graph(self, runtime_data: dict, 
                                     semantic_graph: dict) -> dict:
        """
        Merge runtime data with static code graph.
        
        This answers: "Does theory match practice?"
        """
        merged = {
            "theory_vs_reality": [],
            "unexecuted_code": [],
            "unexpected_bottlenecks": [],
        }
        
        # Compare static call graph with runtime calls
        static_calls = set()
        runtime_calls = set()
        
        # Extract from semantic graph
        for node in semantic_graph.get("nodes", []):
            if node.get("type") == "function":
                static_calls.add(node.get("name"))
        
        # Extract from runtime
        # (simplified - would match actual trace data)
        
        # Find unexecuted code
        unexecuted = static_calls - runtime_calls
        merged["unexecuted_code"] = list(unexecuted)
        
        # Find unexpected bottlenecks
        # (functions that are called much more/less than expected)
        
        return merged
    
    def get_trace_summary(self, trace_id: str) -> dict:
        """Get a quick summary of a trace"""
        trace = self.traces.get(trace_id)
        
        if not trace:
            return {}
        
        return {
            "trace_id": trace.trace_id,
            "duration_ms": trace.duration_ms,
            "total_events": len(trace.events),
            "total_calls": trace.total_calls,
            "errors": trace.total_errors,
            "slow_calls_count": len(trace.slow_calls),
        }
    
    def export_traces(self, format: str = "json") -> str:
        """Export traces in specified format"""
        # In production, would export to various formats
        # (JSON, Jaeger, Zipkin, etc.)
        
        import json
        return json.dumps({
            "traces": [
                {
                    "trace_id": t.trace_id,
                    "events": len(t.events),
                    "duration_ms": t.duration_ms,
                }
                for t in self.traces.values()
            ],
        }, indent=2)


class Tracer:
    """
    In-code tracer for manual instrumentation.
    
    Usage:
        tracer = Tracer()
        
        with tracer.trace("my_function"):
            # do work
            pass
    """
    
    def __init__(self, service_name: str = "default"):
        self.service_name = service_name
        self.trace_id = ""
        self.span_stack: list[TraceEvent] = []
    
    def start_trace(self) -> str:
        """Start a new trace"""
        import uuid
        self.trace_id = str(uuid.uuid4())
        return self.trace_id
    
    def trace(self, name: str, **kwargs):
        """Context manager for tracing a block"""
        return _TraceContext(self, name, **kwargs)
    
    def emit_event(self, event: TraceEvent):
        """Emit a trace event"""
        # In production, would send to trace collector
        pass


class _TraceContext:
    """Context manager for tracing"""
    
    def __init__(self, tracer: Tracer, name: str, **kwargs):
        self.tracer = tracer
        self.name = name
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        
        event = TraceEvent(
            event_type=TraceEventType.FUNCTION_ENTRY,
            timestamp=datetime.now().isoformat(),
            trace_id=self.tracer.trace_id,
            span_id="",  # Would generate
            name=self.name,
            **self.kwargs,
        )
        
        self.tracer.emit_event(event)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration_ms = (time.time() - self.start_time) * 1000
        
        event = TraceEvent(
            event_type=TraceEventType.FUNCTION_EXIT,
            timestamp=datetime.now().isoformat(),
            trace_id=self.tracer.trace_id,
            span_id="",
            name=self.name,
            duration_ms=duration_ms,
        )
        
        self.tracer.emit_event(event)
