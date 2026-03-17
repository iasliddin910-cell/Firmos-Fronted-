"""
DedupAnalyzer - Duplicate Detection
==================================

Task duplicate va overlap aniqlash.

Bu modul:
- Prompt similarity
- Fixture similarity
- Verifier similarity
- Capability overlap
- Failure mode overlap

aniqlaydi.

Definition of Done:
4. Dedup va contamination scan ishlaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from difflib import SequenceMatcher
import hashlib
import os
import json


@dataclass
class DuplicateGroup:
    """Duplicate tasklar guruhi."""
    representative_id: str
    duplicate_ids: List[str]
    similarity_type: str  # prompt, fixture, capability, mixed
    similarity_score: float
    reason: str


@dataclass
class OverlapResult:
    """Overlap natijasi."""
    task_id_1: str
    task_id_2: str
    overlap_type: str
    overlap_score: float
    details: Dict[str, Any] = field(default_factory=dict)


class TextSimilarity:
    """Matn o'xshashligini hisoblash."""
    
    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Ikki matn o'xshashligi (0-1)."""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    @staticmethod
    def similarity_hash(text: str, n: int = 3) -> Set[str]:
        """N-gram hash."""
        text = text.lower()
        return set(text[i:i+n] for i in range(len(text) - n + 1))


class DedupAnalyzer:
    """
    Duplicate va overlap analyzer.
    
    Definition of Done:
    4. Dedup va contamination scan ishlaydi.
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.text_similarity = TextSimilarity()
        
        # Task cache
        self.task_prompts: Dict[str, str] = {}
        self.task_fixtures: Dict[str, Any] = {}
        self.task_metadata: Dict[str, Dict[str, Any]] = {}
    
    def load_tasks(
        self,
        tasks_data: Dict[str, Dict[str, Any]],
        fixtures_path: str = None,
    ) -> None:
        """Tasklarni yuklash."""
        self.task_metadata = tasks_data
        
        # Load prompts
        for task_id, data in tasks_data.items():
            prompt = data.get("prompt", "") or data.get("description", "")
            self.task_prompts[task_id] = prompt
        
        # Load fixtures
        if fixtures_path and os.path.exists(fixtures_path):
            for filename in os.listdir(fixtures_path):
                if filename.endswith(".json"):
                    task_id = filename.replace(".json", "")
                    with open(os.path.join(fixtures_path, filename), 'r') as f:
                        self.task_fixtures[task_id] = json.load(f)
    
    def find_prompt_duplicates(self) -> List[DuplicateGroup]:
        """Prompt asosidagi duplicateelar."""
        duplicates = []
        task_ids = list(self.task_prompts.keys())
        
        for i, id1 in enumerate(task_ids):
            group = [id1]
            
            for id2 in task_ids[i+1:]:
                sim = self.text_similarity.similarity(
                    self.task_prompts[id1],
                    self.task_prompts[id2],
                )
                
                if sim >= self.similarity_threshold:
                    group.append(id2)
            
            if len(group) > 1:
                duplicates.append(DuplicateGroup(
                    representative_id=group[0],
                    duplicate_ids=group[1:],
                    similarity_type="prompt",
                    similarity_score=self.text_similarity.similarity(
                        self.task_prompts[group[0]],
                        self.task_prompts[group[1]] if len(group) > 1 else "",
                    ),
                    reason="High prompt similarity",
                ))
        
        return duplicates
    
    def find_capability_duplicates(self) -> List[DuplicateGroup]:
        """Capability asosidagi duplicateelar."""
        duplicates = []
        
        # Group by capabilities
        cap_groups: Dict[str, List[str]] = {}
        for task_id, data in self.task_metadata.items():
            caps = tuple(sorted(data.get("capabilities", [])))
            if caps:
                if caps not in cap_groups:
                    cap_groups[caps] = []
                cap_groups[caps].append(task_id)
        
        # Find groups with multiple tasks
        for caps, task_ids in cap_groups.items():
            if len(task_ids) > 1:
                duplicates.append(DuplicateGroup(
                    representative_id=task_ids[0],
                    duplicate_ids=task_ids[1:],
                    similarity_type="capability",
                    similarity_score=1.0,
                    reason=f"Same capabilities: {caps}",
                ))
        
        return duplicates
    
    def find_fixture_duplicates(self) -> List[DuplicateGroup]:
        """Fixture asosidagi duplicateelar."""
        duplicates = []
        
        # Hash fixtures
        fixture_hashes: Dict[str, List[str]] = {}
        for task_id, fixture in self.task_fixtures.items():
            fixture_str = json.dumps(fixture, sort_keys=True)
            fixture_hash = hashlib.md5(fixture_str.encode()).hexdigest()
            
            if fixture_hash not in fixture_hashes:
                fixture_hashes[fixture_hash] = []
            fixture_hashes[fixture_hash].append(task_id)
        
        # Find duplicates
        for fixture_hash, task_ids in fixture_hashes.items():
            if len(task_ids) > 1:
                duplicates.append(DuplicateGroup(
                    representative_id=task_ids[0],
                    duplicate_ids=task_ids[1:],
                    similarity_type="fixture",
                    similarity_score=1.0,
                    reason="Identical fixtures",
                ))
        
        return duplicates
    
    def analyze_overlap(
        self,
        task_id_1: str,
        task_id_2: str,
    ) -> OverlapResult:
        """Ikki task o'rtasidagi overlap."""
        data1 = self.task_metadata.get(task_id_1, {})
        data2 = self.task_metadata.get(task_id_2, {})
        
        # Capability overlap
        caps1 = set(data1.get("capabilities", []))
        caps2 = set(data2.get("capabilities", []))
        
        if caps1 and caps2:
            intersection = len(caps1 & caps2)
            union = len(caps1 | caps2)
            cap_overlap = intersection / union if union > 0 else 0
        else:
            cap_overlap = 0
        
        # Prompt overlap
        prompt_overlap = self.text_similarity.similarity(
            self.task_prompts.get(task_id_1, ""),
            self.task_prompts.get(task_id_2, ""),
        )
        
        # Determine overlap type
        if cap_overlap > 0.8 and prompt_overlap > 0.7:
            overlap_type = "high"
        elif cap_overlap > 0.5 or prompt_overlap > 0.5:
            overlap_type = "medium"
        else:
            overlap_type = "low"
        
        return OverlapResult(
            task_id_1=task_id_1,
            task_id_2=task_id_2,
            overlap_type=overlap_type,
            overlap_score=(cap_overlap + prompt_overlap) / 2,
            details={
                "capability_overlap": cap_overlap,
                "prompt_overlap": prompt_overlap,
            },
        )
    
    def find_all_duplicates(self) -> List[DuplicateGroup]:
        """Barcha typdagi duplicateelar."""
        all_duplicates = []
        
        # Find each type
        all_duplicates.extend(self.find_prompt_duplicates())
        all_duplicates.extend(self.find_capability_duplicates())
        all_duplicates.extend(self.find_fixture_duplicates())
        
        # Merge overlapping groups
        return self._merge_duplicate_groups(all_duplicates)
    
    def _merge_duplicate_groups(
        self,
        groups: List[DuplicateGroup],
    ) -> List[DuplicateGroup]:
        """Duplicate guruhlarni birlashtirish."""
        if not groups:
            return []
        
        # Build task -> group mapping
        task_to_group: Dict[str, int] = {}
        for i, group in enumerate(groups):
            task_to_group[group.representative_id] = i
            for dup_id in group.duplicate_ids:
                task_to_group[dup_id] = i
        
        # Merge
        merged: Dict[int, Set[str]] = {}
        for task_id, group_idx in task_to_group.items():
            if group_idx not in merged:
                merged[group_idx] = set()
            merged[group_idx].add(task_id)
        
        # Convert back to DuplicateGroup
        result = []
        for group_idx, task_ids in merged.items():
            task_ids = list(task_ids)
            result.append(DuplicateGroup(
                representative_id=task_ids[0],
                duplicate_ids=task_ids[1:],
                similarity_type="mixed",
                similarity_score=1.0,
                reason="Merged duplicate groups",
            ))
        
        return result
    
    def get_dedup_report(self) -> Dict[str, Any]:
        """Dedup hisoboti."""
        duplicates = self.find_all_duplicates()
        
        total_tasks = len(self.task_metadata)
        duplicate_tasks = len(set(
            d.representative_id for d in duplicates
        ) + [
            d_id for d in duplicates for d_id in d.duplicate_ids
        ])
        
        return {
            "total_tasks": total_tasks,
            "duplicate_groups": len(duplicates),
            "affected_tasks": duplicate_tasks,
            "duplicate_ratio": duplicate_tasks / total_tasks if total_tasks > 0 else 0,
            "duplicates": [
                {
                    "representative": d.representative_id,
                    "duplicates": d.duplicate_ids,
                    "type": d.similarity_type,
                    "reason": d.reason,
                }
                for d in duplicates
            ],
        }


# ==================== FACTORY ====================

def create_dedup_analyzer(similarity_threshold: float = 0.85) -> DedupAnalyzer:
    """DedupAnalyzer yaratish."""
    return DedupAnalyzer(similarity_threshold)
