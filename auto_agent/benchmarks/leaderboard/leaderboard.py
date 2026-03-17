"""
Leaderboard - Multi-Axis Score Board Management
===============================================

Manages stable and experimental leaderboards with full
multi-axis support.

This module provides:
- LeaderboardManager: Manage multiple leaderboards
- Board storage and retrieval
- Historical tracking
- Slice views

Definition of Done:
2. Per-suite, per-capability, per-difficulty scoreboardlar bor.
4. Stable va experimental board alohida.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import json
import os
from datetime import datetime
from pathlib import Path


# ==================== BOARD TYPES ====================

class BoardType(str, Enum):
    """Leaderboard types."""
    STABLE = "stable"
    EXPERIMENTAL = "experimental"


class SliceType(str, Enum):
    """Slice types for leaderboard views."""
    ALL = "all"
    HARD_FRONTIER = "hard_frontier"
    CANARY = "canary"
    SELF_MOD = "self_mod"
    BROWSER = "browser"
    REALISTIC = "realistic"
    CHEAP_RUN = "cheap_run"
    HIGH_INTEGRITY = "high_integrity"


# ==================== BOARD ENTRIES ====================

@dataclass
class BoardEntry:
    """
    A single entry in a leaderboard.
    """
    run_id: str
    agent_version: str
    timestamp: str
    
    # Main scores
    global_score: float
    
    # Dimension scores
    dimension_scores: Dict[str, float]
    
    # Suite scores
    suite_scores: Dict[str, float]
    
    # Capability scores
    capability_scores: Dict[str, float]
    
    # Difficulty scores
    difficulty_scores: Dict[str, float]
    
    # Additional metadata
    task_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    
    # Metrics
    total_cost: float = 0.0
    avg_time: float = 0.0
    avg_steps: float = 0.0
    
    # Tags
    tags: List[str] = field(default_factory=list)
    
    # Parent info
    parent_run_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "agent_version": self.agent_version,
            "timestamp": self.timestamp,
            "global_score": self.global_score,
            "dimension_scores": self.dimension_scores,
            "suite_scores": self.suite_scores,
            "capability_scores": self.capability_scores,
            "difficulty_scores": self.difficulty_scores,
            "task_count": self.task_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "total_cost": self.total_cost,
            "avg_time": self.avg_time,
            "avg_steps": self.avg_steps,
            "tags": self.tags,
            "parent_run_id": self.parent_run_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BoardEntry':
        """Create from dictionary."""
        return cls(**data)


# ==================== LEADERBOARD ====================

@dataclass
class Leaderboard:
    """
    A leaderboard with multiple slices.
    """
    board_type: BoardType
    entries: List[BoardEntry] = field(default_factory=list)
    
    # Slice cache
    _slices: Dict[str, List[BoardEntry]] = field(default_factory=dict, repr=False)
    
    def add_entry(self, entry: BoardEntry) -> None:
        """Add an entry to the leaderboard."""
        self.entries.append(entry)
        # Invalidate slice cache
        self._slices = {}
    
    def get_entries(
        self,
        slice_type: SliceType = SliceType.ALL,
        sort_by: str = "global_score",
        ascending: bool = False,
        limit: int = None,
    ) -> List[BoardEntry]:
        """Get entries with optional slicing."""
        entries = self._get_slice(slice_type)
        
        # Sort
        if sort_by == "global_score":
            entries = sorted(entries, key=lambda e: e.global_score, reverse=not ascending)
        elif sort_by == "timestamp":
            entries = sorted(entries, key=lambda e: e.timestamp, reverse=not ascending)
        
        # Limit
        if limit:
            entries = entries[:limit]
        
        return entries
    
    def _get_slice(self, slice_type: SliceType) -> List[BoardEntry]:
        """Get entries for a specific slice."""
        if slice_type in self._slices:
            return self._slices[slice_type]
        
        # Compute slice
        if slice_type == SliceType.ALL:
            sliced = self.entries
        elif slice_type == SliceType.HARD_FRONTIER:
            sliced = [
                e for e in self.entries
                if e.difficulty_scores.get("hard", 0) > 0 or e.difficulty_scores.get("frontier", 0) > 0
            ]
        elif slice_type == SliceType.CANARY:
            sliced = [e for e in self.entries if "canary" in e.tags]
        elif slice_type == SliceType.SELF_MOD:
            sliced = [
                e for e in self.entries
                if e.suite_scores.get("self_modification", 0) > 0
            ]
        elif slice_type == SliceType.BROWSER:
            sliced = [
                e for e in self.entries
                if e.suite_scores.get("browser_workflow", 0) > 0
            ]
        elif slice_type == SliceType.REALISTIC:
            sliced = [e for e in self.entries if "realistic" in e.tags]
        elif slice_type == SliceType.CHEAP_RUN:
            sliced = [e for e in self.entries if e.total_cost < 10.0]
        elif slice_type == SliceType.HIGH_INTEGRITY:
            sliced = [
                e for e in self.entries
                if e.dimension_scores.get("integrity", 0) >= 0.95
            ]
        else:
            sliced = self.entries
        
        self._slices[slice_type] = sliced
        return sliced
    
    def get_top(
        self,
        n: int = 10,
        slice_type: SliceType = SliceType.ALL,
    ) -> List[BoardEntry]:
        """Get top N entries."""
        return self.get_entries(slice_type=slice_type, limit=n)
    
    def get_rank(self, run_id: str) -> Optional[int]:
        """Get rank of a specific run."""
        entries = self.get_entries()
        for i, entry in enumerate(entries):
            if entry.run_id == run_id:
                return i + 1
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "board_type": self.board_type.value,
            "entries": [e.to_dict() for e in self.entries],
            "entry_count": len(self.entries),
        }
    
    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Leaderboard':
        """Create from dictionary."""
        board = cls(board_type=BoardType(data["board_type"]))
        for entry_data in data.get("entries", []):
            board.add_entry(BoardEntry.from_dict(entry_data))
        return board


# ==================== LEADERBOARD MANAGER ====================

class LeaderboardManager:
    """
    Manages stable and experimental leaderboards.
    
    Definition of Done:
    4. Stable va experimental board alohida.
    5. Integrity/reliability/efficiency alohida ko'rinadi.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.stable_board = Leaderboard(BoardType.STABLE)
        self.experimental_board = Leaderboard(BoardType.EXPERIMENTAL)
        
        # Historical data
        self.historical_runs: List[BoardEntry] = []
        
        # Load from storage if available
        if storage_path:
            self._load_boards()
    
    # ==================== BOARD OPERATIONS ====================
    
    def add_to_stable(self, entry: BoardEntry) -> None:
        """Add entry to stable board."""
        self.stable_board.add_entry(entry)
        self.historical_runs.append(entry)
        self._save_boards()
    
    def add_to_experimental(self, entry: BoardEntry) -> None:
        """Add entry to experimental board."""
        self.experimental_board.add_entry(entry)
        self.historical_runs.append(entry)
        self._save_boards()
    
    def promote_to_stable(
        self,
        run_id: str,
        reason: str = "",
    ) -> bool:
        """
        Promote a run from experimental to stable.
        
        Returns True if successful.
        """
        # Find in experimental
        entry = None
        for e in self.experimental_board.entries:
            if e.run_id == run_id:
                entry = e
                break
        
        if not entry:
            return False
        
        # Add to stable
        entry.tags.append(f"promoted: {reason}")
        self.stable_board.add_entry(entry)
        
        # Remove from experimental
        self.experimental_board.entries = [
            e for e in self.experimental_board.entries if e.run_id != run_id
        ]
        
        self._save_boards()
        return True
    
    def get_stable_board(
        self,
        slice_type: SliceType = SliceType.ALL,
    ) -> List[BoardEntry]:
        """Get stable board entries."""
        return self.stable_board.get_entries(slice_type=slice_type)
    
    def get_experimental_board(
        self,
        slice_type: SliceType = SliceType.ALL,
    ) -> List[BoardEntry]:
        """Get experimental board entries."""
        return self.experimental_board.get_entries(slice_type=slice_type)
    
    def get_rank(
        self,
        run_id: str,
        board_type: BoardType = None,
    ) -> Optional[int]:
        """Get rank of a run."""
        if board_type == BoardType.STABLE:
            return self.stable_board.get_rank(run_id)
        elif board_type == BoardType.EXPERIMENTAL:
            return self.experimental_board.get_rank(run_id)
        else:
            # Check both
            rank = self.stable_board.get_rank(run_id)
            if rank:
                return rank
            return self.experimental_board.get_rank(run_id)
    
    # ==================== ANALYSIS ====================
    
    def compare_runs(
        self,
        run_id_1: str,
        run_id_2: str,
    ) -> Dict[str, Any]:
        """Compare two runs."""
        entry_1 = self._find_entry(run_id_1)
        entry_2 = self._find_entry(run_id_2)
        
        if not entry_1 or not entry_2:
            return {"error": "One or both runs not found"}
        
        # Compare dimensions
        dim_deltas = {}
        for dim in entry_1.dimension_scores:
            delta = (
                entry_2.dimension_scores.get(dim, 0) -
                entry_1.dimension_scores.get(dim, 0)
            )
            dim_deltas[dim] = delta
        
        # Compare suites
        suite_deltas = {}
        for suite in entry_1.suite_scores:
            delta = (
                entry_2.suite_scores.get(suite, 0) -
                entry_1.suite_scores.get(suite, 0)
            )
            suite_deltas[suite] = delta
        
        return {
            "run_1": entry_1.run_id,
            "run_2": entry_2.run_id,
            "global_delta": entry_2.global_score - entry_1.global_score,
            "dimension_deltas": dim_deltas,
            "suite_deltas": suite_deltas,
            "run_1_entry": entry_1.to_dict(),
            "run_2_entry": entry_2.to_dict(),
        }
    
    def get_improvements(
        self,
        run_id: str,
        baseline_run_id: str = None,
    ) -> Dict[str, Any]:
        """Get improvements compared to baseline."""
        current = self._find_entry(run_id)
        
        if not current:
            return {"error": "Run not found"}
        
        # Use best stable as baseline if not specified
        if not baseline_run_id:
            baseline = self.stable_board.get_entries(limit=1)
            baseline = baseline[0] if baseline else None
        else:
            baseline = self._find_entry(baseline_run_id)
        
        if not baseline:
            return {"current": current.to_dict(), "baseline": None}
        
        comparison = self.compare_runs(baseline.run_id, run_id)
        
        return {
            "current": current.to_dict(),
            "baseline": baseline.to_dict(),
            "improvements": comparison,
        }
    
    def get_historical_trend(
        self,
        metric: str = "global_score",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get historical trend for a metric."""
        # Sort by timestamp
        sorted_runs = sorted(
            self.historical_runs,
            key=lambda e: e.timestamp,
        )
        
        # Get metric values
        trend = []
        for entry in sorted_runs[-limit:]:
            if metric == "global_score":
                value = entry.global_score
            elif metric in entry.dimension_scores:
                value = entry.dimension_scores[metric]
            elif metric in entry.suite_scores:
                value = entry.suite_scores[metric]
            else:
                value = None
            
            if value is not None:
                trend.append({
                    "run_id": entry.run_id,
                    "timestamp": entry.timestamp,
                    "value": value,
                    "agent_version": entry.agent_version,
                })
        
        return trend
    
    # ==================== PERSISTENCE ====================
    
    def _get_storage_path(self, board_type: BoardType) -> str:
        """Get storage path for a board."""
        if not self.storage_path:
            return None
        
        filename = f"{board_type.value}_board.json"
        return os.path.join(self.storage_path, filename)
    
    def _save_boards(self) -> None:
        """Save boards to storage."""
        if not self.storage_path:
            return
        
        # Save stable
        stable_path = self._get_storage_path(BoardType.STABLE)
        if stable_path:
            with open(stable_path, 'w') as f:
                f.write(self.stable_board.to_json())
        
        # Save experimental
        exp_path = self._get_storage_path(BoardType.EXPERIMENTAL)
        if exp_path:
            with open(exp_path, 'w') as f:
                f.write(self.experimental_board.to_json())
    
    def _load_boards(self) -> None:
        """Load boards from storage."""
        if not self.storage_path:
            return
        
        # Load stable
        stable_path = self._get_storage_path(BoardType.STABLE)
        if stable_path and os.path.exists(stable_path):
            try:
                with open(stable_path, 'r') as f:
                    data = json.load(f)
                    self.stable_board = Leaderboard.from_dict(data)
            except Exception as e:
                print(f"Error loading stable board: {e}")
        
        # Load experimental
        exp_path = self._get_storage_path(BoardType.EXPERIMENTAL)
        if exp_path and os.path.exists(exp_path):
            try:
                with open(exp_path, 'r') as f:
                    data = json.load(f)
                    self.experimental_board = Leaderboard.from_dict(data)
            except Exception as e:
                print(f"Error loading experimental board: {e}")
    
    def _find_entry(self, run_id: str) -> Optional[BoardEntry]:
        """Find entry by run_id."""
        for entry in self.historical_runs:
            if entry.run_id == run_id:
                return entry
        return None
    
    # ==================== EXPORT ====================
    
    def export_capability_matrix(
        self,
        board_type: BoardType = None,
    ) -> Dict[str, Any]:
        """Export capability matrix view."""
        if board_type == BoardType.STABLE:
            entries = self.stable_board.entries
        elif board_type == BoardType.EXPERIMENTAL:
            entries = self.experimental_board.entries
        else:
            entries = self.historical_runs
        
        # Build matrix
        all_suites = set()
        all_capabilities = set()
        
        for entry in entries:
            all_suites.update(entry.suite_scores.keys())
            all_capabilities.update(entry.capability_scores.keys())
        
        matrix = []
        for entry in entries:
            row = {
                "run_id": entry.run_id,
                "agent_version": entry.agent_version,
                "global_score": entry.global_score,
                "timestamp": entry.timestamp,
            }
            
            for suite in sorted(all_suites):
                row[suite] = entry.suite_scores.get(suite, 0.0)
            
            for cap in sorted(all_capabilities):
                row[cap] = entry.capability_scores.get(cap, 0.0)
            
            matrix.append(row)
        
        return {
            "suites": sorted(list(all_suites)),
            "capabilities": sorted(list(all_capabilities)),
            "matrix": matrix,
        }


# ==================== FACTORY ====================

def create_leaderboard_manager(
    storage_path: str = None,
) -> LeaderboardManager:
    """Create leaderboard manager."""
    return LeaderboardManager(storage_path)


def create_entry_from_scorecard(
    scorecard_data: Dict[str, Any],
) -> BoardEntry:
    """Create board entry from scorecard data."""
    summary = scorecard_data.get("summary", {})
    
    return BoardEntry(
        run_id=scorecard_data.get("run_id", ""),
        agent_version=scorecard_data.get("agent_version", ""),
        timestamp=datetime.utcnow().isoformat(),
        global_score=scorecard_data.get("global_score", 0.0),
        dimension_scores=scorecard_data.get("dimension_scores", {}),
        suite_scores=scorecard_data.get("suite_scores", {}),
        capability_scores=scorecard_data.get("capability_scores", {}),
        difficulty_scores=scorecard_data.get("difficulty_scores", {}),
        task_count=summary.get("total_tasks", 0),
        passed_count=summary.get("passed_tasks", 0),
        failed_count=summary.get("failed_tasks", 0),
        tags=scorecard_data.get("tags", []),
    )
