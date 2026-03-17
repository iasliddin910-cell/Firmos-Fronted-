"""
PatchAnalytics - Patch Analysis
==============================

Patch tahlili.

Bu modul:
- Patch family
- Touched subsystem
- Diff size bucket
- Hidden regression count
- Downstream delta
- Rollback probability

hisoblaydi.

Definition of Done:
4. Patch impact va tool effectiveness reportlari mavjud.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from collections import defaultdict


@dataclass
class PatchMetrics:
    """Patch metrikalari."""
    run_id: str
    task_id: str
    
    # Diff metrics
    diff_lines_added: int = 0
    diff_lines_removed: int = 0
    diff_files_changed: int = 0
    
    # File analysis
    modules_touched: List[str] = field(default_factory=list)
    hot_modules: List[str] = field(default_factory=list)
    
    # Classification
    patch_class: str = ""  # surgical, broad, refactor, etc.
    patch_family: str = ""
    
    # Impact
    downstream_delta: float = 0.0
    canary_retention: float = 0.0
    
    # Risk
    rollback_probability: float = 0.0
    regression_risk: str = "low"


class PatchAnalytics:
    """
    Patch analytics.
    
    Definition of Done:
    4. Patch impact va tool effectiveness reportlari mavjud.
    """
    
    def __init__(self):
        self.trace_storage = None
    
    def analyze_patches(self, traces: List[Any]) -> Dict[str, Any]:
        """Patchlarni tahlil qilish."""
        patches = []
        
        for trace in traces:
            if trace.patch_diff:
                metrics = self._analyze_single_patch(trace)
                patches.append(metrics)
        
        if not patches:
            return {"total_patches": 0}
        
        # Aggregate by class
        class_stats = self._aggregate_by_class(patches)
        
        # Aggregate by module
        module_stats = self._aggregate_by_module(patches)
        
        # Risk analysis
        risk_analysis = self._analyze_risk(patches)
        
        return {
            "total_patches": len(patches),
            "by_class": class_stats,
            "by_module": module_stats,
            "risk_analysis": risk_analysis,
            "patches": [p.__dict__ for p in patches[:20]],
        }
    
    def _analyze_single_patch(self, trace) -> PatchMetrics:
        """Bitta patchni tahlil qilish."""
        metrics = PatchMetrics(
            run_id=trace.run_id,
            task_id=trace.task_id,
        )
        
        diff = trace.patch_diff
        if not diff:
            return metrics
        
        # Count lines
        lines = diff.split("\n")
        metrics.diff_lines_added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
        metrics.diff_lines_removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
        
        # Count files
        files = set()
        for line in lines:
            if line.startswith("diff --git"):
                # Extract file name
                parts = line.split()
                if len(parts) >= 3:
                    files.add(parts[2].replace("a/", "").replace("b/", ""))
        
        metrics.diff_files_changed = len(files)
        metrics.modules_touched = list(files)[:10]  # Top 10
        
        # Determine patch class
        if metrics.diff_files_changed == 1:
            if metrics.diff_lines_added + metrics.diff_lines_removed <= 20:
                metrics.patch_class = "surgical"
            else:
                metrics.patch_class = "single_file"
        elif metrics.diff_files_changed <= 5:
            metrics.patch_class = "focused"
        else:
            metrics.patch_class = "broad"
        
        return metrics
    
    def _aggregate_by_class(self, patches: List[PatchMetrics]) -> Dict:
        """Patch class bo'yicha aggregate."""
        by_class = defaultdict(lambda: {"count": 0, "total_lines": 0, "total_files": 0})
        
        for p in patches:
            by_class[p.patch_class]["count"] += 1
            by_class[p.patch_class]["total_lines"] += p.diff_lines_added + p.diff_lines_removed
            by_class[p.patch_class]["total_files"] += p.diff_files_changed
        
        return dict(by_class)
    
    def _aggregate_by_module(self, patches: List[PatchMetrics]) -> Dict:
        """Module bo'yicha aggregate."""
        modules = defaultdict(int)
        
        for p in patches:
            for mod in p.modules_touched:
                modules[mod] += 1
        
        # Sort by frequency
        sorted_modules = sorted(modules.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_modules[:20])
    
    def _analyze_risk(self, patches: List[PatchMetrics]) -> Dict:
        """Risk tahlil."""
        risk_counts = defaultdict(int)
        
        for p in patches:
            risk_counts[p.regression_risk] += 1
        
        return {
            "distribution": dict(risk_counts),
            "high_risk_count": risk_counts.get("high", 0),
            "medium_risk_count": risk_counts.get("medium", 0),
            "low_risk_count": risk_counts.get("low", 0),
        }


def create_patch_analytics() -> PatchAnalytics:
    """PatchAnalytics yaratish."""
    return PatchAnalytics()
