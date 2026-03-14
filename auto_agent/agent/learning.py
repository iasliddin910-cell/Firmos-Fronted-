"""
OmniAgent X - Self-Learning Engine (Legacy Helper)
==================================================
DEPRECATED: Use learning_pipeline.py instead.

This module is kept for backward compatibility.
The main learning functionality is now in learning_pipeline.py.

Migration:
    from agent.learning_pipeline import UnifiedLearning, create_unified_learning
    
    # Instead of:
    learning = SelfLearningEngine()
    
    # Use:
    learning = create_unified_learning()
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

# Import from learning_pipeline for unified interface
try:
    from agent.learning_pipeline import (
        UnifiedLearning,
        create_unified_learning as _create_pipeline,
        SourceType,
        KnowledgeType,
        TrustLevel,
        ConfidenceLevel
    )
    HAS_PIPELINE = True
except ImportError:
    HAS_PIPELINE = False
    logger.warning("learning_pipeline not available, using legacy mode")


class SelfLearningEngine:
    """
    Mustaqil o'rganish tizimi - xatolaridan o'rganadi va yaxshi bo'lib boradi
    
    DEPRECATED: This class is maintained for backward compatibility.
    Use UnifiedLearning from learning_pipeline.py for new code.
    """
    
    # Reference to unified learning pipeline (if available)
    _unified: Optional[Any] = None
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "learning"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to use unified pipeline if available
        if HAS_PIPELINE and SelfLearningEngine._unified is None:
            try:
                SelfLearningEngine._unified = _create_pipeline(str(data_dir))
                logger.info("Using UnifiedLearning from learning_pipeline")
            except Exception as e:
                logger.warning(f"Could not initialize unified pipeline: {e}")
        
        # Legacy file-based storage (for backward compatibility)
        self.errors_file = self.data_dir / "errors.json"
        self.patterns_file = self.data_dir / "patterns.json"
        self.preferences_file = self.data_dir / "preferences.json"
        self.skills_file = self.data_dir / "skills.json"
        self.conversations_file = self.data_dir / "conversations.json"
        
        # Load knowledge
        self.errors = self._load_json(self.errors_file)
        self.patterns = self._load_json(self.patterns_file)
        self.preferences = self._load_json(self.preferences_file)
        self.skills = self._load_json(self.skills_file)
        self.conversations = self._load_json(self.conversations_file)
        
        # Stats
        self.session_stats = {
            "total_interactions": 0,
            "successful": 0,
            "failed": 0,
            "start_time": datetime.now().isoformat(),
            "legacy_mode": not HAS_PIPELINE
        }
        
        logger.warning("⚠️ SelfLearningEngine is DEPRECATED. Use learning_pipeline.py instead.")
        logger.info("🧠 Self-Learning Engine initialized (legacy mode: %s)", not HAS_PIPELINE)
    
    def _load_json(self, filepath: Path) -> Dict:
        """Load JSON file or return empty dict"""
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted JSON file {filepath}: {e}")
                return {}
            except Exception as e:
                logger.error(f"Error loading {filepath}: {e}")
                return {}
        return {}
    
    def _save_json(self, filepath: Path, data: Dict):
        """Save data to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
    
    # ==================== LEARN FROM ERRORS ====================
    
    def learn_from_error(self, task: str, error: str, solution: str = None):
        """
        Xatodan o'rganish
        """
        task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
        
        if task_hash not in self.errors:
            self.errors[task_hash] = {
                "task": task,
                "attempts": 0,
                "errors": [],
                "solutions": [],
                "success_rate": 0.0,
                "first_seen": datetime.now().isoformat()
            }
        
        self.errors[task_hash]["attempts"] += 1
        self.errors[task_hash]["errors"].append({
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
        if solution:
            self.errors[task_hash]["solutions"].append({
                "solution": solution,
                "timestamp": datetime.now().isoformat()
            })
        
        # Update success rate
        total = self.errors[task_hash]["attempts"]
        successes = len(self.errors[task_hash]["solutions"])
        self.errors[task_hash]["success_rate"] = successes / total if total > 0 else 0
        
        self._save_json(self.errors_file, self.errors)
        
        logger.info(f"🧠 Learned from error: {task[:30]}... (attempts: {total})")
    
    def learn_from_success(self, task: str, approach: str):
        """
        Muvaffaqiyatdan o'rganish
        """
        task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
        
        if task_hash not in self.patterns:
            self.patterns[task_hash] = {
                "task": task,
                "approaches": [],
                "success_count": 0,
                "first_success": datetime.now().isoformat()
            }
        
        # Check if this approach already exists
        approaches = self.patterns[task_hash]["approaches"]
        found = False
        for app in approaches:
            if app["approach"] == approach:
                app["count"] += 1
                app["last_used"] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            approaches.append({
                "approach": approach,
                "count": 1,
                "first_used": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat()
            })
        
        self.patterns[task_hash]["success_count"] += 1
        
        self._save_json(self.patterns_file, self.patterns)
        
        logger.info(f"🧠 Learned success pattern: {task[:30]}...")
    
    # ==================== RECALL ====================
    
    def recall_error(self, task: str) -> Optional[Dict]:
        """
        Oldingi xatoni eslash
        """
        task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
        return self.errors.get(task_hash)
    
    def recall_best_approach(self, task: str) -> Optional[str]:
        """
        Eng yaxshi yondashuvni eslash
        """
        task_hash = hashlib.md5(task.encode()).hexdigest()[:8]
        if task_hash in self.patterns:
            approaches = self.patterns[task_hash]["approaches"]
            if approaches:
                # Sort by count
                best = max(approaches, key=lambda x: x["count"])
                return best["approach"]
        return None
    
    def get_learned_tasks(self) -> List[str]:
        """
        O'rganilgan vazifalar ro'yxatini olish
        """
        learned = []
        for task_hash, data in self.patterns.items():
            learned.append({
                "task": data["task"],
                "success_count": data["success_count"]
            })
        return sorted(learned, key=lambda x: x["success_count"], reverse=True)
    
    # ==================== PREFERENCES ====================
    
    def learn_preference(self, key: str, value: Any):
        """
        Foydalanuvchi afzalliklarini o'rganish
        """
        if key not in self.preferences:
            self.preferences[key] = {"values": [], "count": 0}
        
        if value not in self.preferences[key]["values"]:
            self.preferences[key]["values"].append(value)
        
        self.preferences[key]["count"] += 1
        
        self._save_json(self.preferences_file, self.preferences)
        logger.info(f"🧠 Learned preference: {key} = {value}")
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Afzallikni olish
        """
        if key in self.preferences and self.preferences[key]["values"]:
            return self.preferences[key]["values"][-1]
        return default
    
    # ==================== SKILLS ====================
    
    def learn_skill(self, skill_name: str, description: str, examples: List[str] = None):
        """
        Yangi ko'nikma o'rganish
        """
        if skill_name not in self.skills:
            self.skills[skill_name] = {
                "description": description,
                "examples": examples or [],
                "times_used": 0,
                "success_rate": 0.0,
                "first_learned": datetime.now().isoformat()
            }
        else:
            if examples:
                for ex in examples:
                    if ex not in self.skills[skill_name]["examples"]:
                        self.skills[skill_name]["examples"].append(ex)
        
        self._save_json(self.skills_file, self.skills)
        logger.info(f"🧠 Learned skill: {skill_name}")
    
    def use_skill(self, skill_name: str, success: bool):
        """
        Ko'nikmani qo'llash natijasini yozish
        """
        if skill_name in self.skills:
            self.skills[skill_name]["times_used"] += 1
            if success:
                current = self.skills[skill_name]["success_rate"]
                times = self.skills[skill_name]["times_used"]
                self.skills[skill_name]["success_rate"] = (current * (times - 1) + 1) / times
            self._save_json(self.skills_file, self.skills)
    
    def get_skills(self) -> List[Dict]:
        """
        Barcha ko'nikmalarni olish
        """
        return [
            {
                "name": name,
                "description": data["description"],
                "times_used": data["times_used"],
                "success_rate": data["success_rate"]
            }
            for name, data in self.skills.items()
        ]
    
    # ==================== STATS ====================
    
    def record_interaction(self, success: bool):
        """
        Interaksiyani yozish
        """
        self.session_stats["total_interactions"] += 1
        if success:
            self.session_stats["successful"] += 1
        else:
            self.session_stats["failed"] += 1
    
    def get_stats(self) -> str:
        """
        Statistikani olish
        """
        total = self.session_stats["total_interactions"]
        successful = self.session_stats["successful"]
        failed = self.session_stats["failed"]
        
        # Load lifetime stats
        total_errors = len(self.errors)
        total_patterns = len(self.patterns)
        total_skills = len(self.skills)
        
        return f"""🧠 **O'rganish Statistikasi:**

**Joriy sessiya:**
- Jami interaksiyalar: {total}
- Muvaffaqiyatli: {successful}
- Muvaffaqiyatsiz: {failed}
- Muvaffaqiyat darajasi: {(successful/total*100) if total > 0 else 0}%

**Umumiy (barcha vaqtlarda):**
- O'rganilgan xatolar: {total_errors}
- Muvaffaqiyatli patternlar: {total_patterns}
- Ko'nikmalar: {total_skills}
- Foydalanuvchi afzalliklari: {len(self.preferences)}
"""
    
    # ==================== AUTO-LEARN ====================
    
    def analyze_and_learn(self, task: str, result: str, was_successful: bool):
        """
        Natijani tahlil qilish va avtomatik o'rganish
        """
        self.record_interaction(was_successful)
        
        if was_successful:
            # Learn successful approach
            self.learn_from_success(task, result[:200])
        else:
            # Learn from error
            error_msg = result if "xato" in result.lower() or "error" in result.lower() else "Noma'lum xato"
            self.learn_from_error(task, error_msg)
    
    def get_advice(self, task: str) -> Optional[str]:
        """
        Vazifa bo'yicha maslahat olish
        """
        # Check for learned errors
        error = self.recall_error(task)
        if error and error["success_rate"] < 0.5:
            return f"⚠️ Diqqat: Bu vazifa oldin {error['attempts']} marta urunilgan, {error['success_rate']*100}% muvaffaqiyat. Xatolar: {error['errors'][-1]['error'][:100]}"
        
        # Check for best approach
        approach = self.recall_best_approach(task)
        if approach:
            return f"💡 Maslahat: Bu vazifa uchun sinab ko'rilgan yondashuv: {approach[:100]}..."
        
        return None
    
    # ==================== RESET ====================
    
    def reset_learning(self):
        """Barcha o'rganilgan narsalarni tozalash"""
        self.errors = {}
        self.patterns = {}
        self.preferences = {}
        self.skills = {}
        self.conversations = {}
        
        self._save_json(self.errors_file, self.errors)
        self._save_json(self.patterns_file, self.patterns)
        self._save_json(self.preferences_file, self.preferences)
        self._save_json(self.skills_file, self.skills)
        self._save_json(self.conversations_file, self.conversations)
        
        logger.info("🧠 Learning memory cleared")


# Global instance
_learning_engine = None

def get_learning_engine(data_dir: Path = None):
    """Get or create learning engine"""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = SelfLearningEngine(data_dir)
    return _learning_engine