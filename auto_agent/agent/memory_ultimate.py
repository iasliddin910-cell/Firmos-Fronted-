"""
OmniAgent X ULTIMATE - Persistent Memory System
================================================
Long-term memory with semantic search using embeddings
"""
import os
import json
import logging
import hashlib
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import numpy as np

logger = logging.getLogger(__name__)

# Try to import sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except Exception as e:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available - using simple search")


class VectorMemory:
    """
    Persistent memory with vector embeddings for semantic search
    """
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "memory"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory storage
        self.memories_file = self.data_dir / "memories.json"
        self.conversations_file = self.data_dir / "conversations.json"
        self.knowledge_file = self.data_dir / "knowledge.json"
        self.preferences_file = self.data_dir / "preferences.json"
        
        # Load data
        self.memories = self._load_json(self.memories_file)
        self.conversations = self._load_json(self.conversations_file)
        self.knowledge = self._load_json(self.knowledge_file)
        self.preferences = self._load_json(self.preferences_file)
        
        # Embedding model
        self.embedding_model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("📚 Embedding model loaded")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
        
        # Memory index
        self.memory_vectors = {}
        self._rebuild_index()
        
        logger.info("💾 Vector Memory initialized")
    
    def _load_json(self, filepath: Path) -> Dict:
        """Load JSON file with proper error handling"""
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted JSON file {filepath}: {e}")
                # Backup corrupted file
                backup_path = filepath.with_suffix('.json.backup')
                try:
                    filepath.rename(backup_path)
                    logger.info(f"Backed up corrupted file to {backup_path}")
                except Exception as backup_err:
                    logger.error(f"Failed to backup corrupted file: {backup_err}")
                return {}
            except PermissionError as e:
                logger.error(f"Permission denied reading {filepath}: {e}")
                return {}
            except Exception as e:
                logger.error(f"Error loading {filepath}: {e}")
                return {}
        return {}
    
    def _save_json(self, filepath: Path, data: Dict):
        """Save data to JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
    
    def _rebuild_index(self):
        """Rebuild memory index"""
        if not self.memories:
            return
        
        if self.embedding_model:
            try:
                texts = [m["content"] for m in self.memories.values()]
                if texts:
                    self.memory_vectors = self.embedding_model.encode(texts, show_progress_bar=False)
            except Exception as e:
                logger.warning(f"Failed to build index: {e}")
    
    # ==================== MEMORY OPERATIONS ====================
    
    def add_memory(self, content: str, memory_type: str = "general", importance: float = 0.5) -> str:
        """
        Add a new memory
        """
        # Generate ID
        mem_id = hashlib.md5(content.encode()).hexdigest()[:12]
        timestamp = datetime.now().isoformat()
        
        # Store memory
        self.memories[mem_id] = {
            "id": mem_id,
            "content": content,
            "type": memory_type,
            "importance": importance,
            "created_at": timestamp,
            "accessed_at": timestamp,
            "access_count": 0,
            "tags": self._extract_tags(content)
        }
        
        # Rebuild index
        self._rebuild_index()
        
        # Save
        self._save_json(self.memories_file, self.memories)
        
        logger.info(f"💾 Memory added: {mem_id}")
        return f"✅ Xotiraga qo'shildi: {mem_id}"
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content"""
        # Simple keyword extraction
        words = content.lower().split()
        # Filter common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "that", "this", "it", "its"}
        tags = [w for w in words if len(w) > 3 and w not in stop_words][:5]
        return list(set(tags))
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search memories using semantic search
        """
        if not self.memories:
            return []
        
        try:
            if self.embedding_model and hasattr(self, 'memory_vectors') and len(self.memory_vectors) > 0:
                # Vector search
                query_vector = self.embedding_model.encode([query])[0]
                
                # Calculate similarities
                similarities = np.dot(self.memory_vectors, query_vector)
                
                # Get top results
                top_indices = np.argsort(similarities)[::-1][:limit]
                
                results = []
                memories_list = list(self.memories.values())
                for idx in top_indices:
                    if idx < len(memories_list):
                        mem = memories_list[idx]
                        mem["similarity"] = float(similarities[idx])
                        results.append(mem)
                
                return results
            else:
                # Fallback to keyword search
                return self._keyword_search(query, limit)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return self._keyword_search(query, limit)
    
    def _keyword_search(self, query: str, limit: int) -> List[Dict]:
        """Simple keyword-based search"""
        query_words = set(query.lower().split())
        results = []
        
        for mem in self.memories.values():
            # Check content
            content_words = set(mem["content"].lower().split())
            matches = len(query_words & content_words)
            
            if matches > 0:
                mem["similarity"] = matches
                results.append(mem)
        
        # Sort by similarity
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return results[:limit]
    
    def recall(self, query: str) -> str:
        """
        Recall relevant memories
        """
        results = self.search_memories(query)
        
        if not results:
            return "❌ Hech qanday xotira topilmadi"
        
        response = f"📚 *Topilgan xotiralar ({len(results)} ta):*\n\n"
        
        for i, mem in enumerate(results, 1):
            similarity = mem.get("similarity", 0)
            content = mem["content"][:200]
            created = mem.get("created_at", "")[:10]
            
            response += f"{i}. 📝 {content}...\n"
            response += f"   🔗 O'xshashlik: {similarity:.2f} | Vaqt: {created}\n\n"
        
        return response
    
    def get_all_memories(self, memory_type: str = None) -> List[Dict]:
        """Get all memories, optionally filtered by type"""
        if memory_type:
            return [m for m in self.memories.values() if m.get("type") == memory_type]
        return list(self.memories.values())
    
    # ==================== CONVERSATION STORAGE ====================
    
    def save_conversation(self, messages: List[Dict]):
        """Save conversation history"""
        conv_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12]
        
        self.conversations[conv_id] = {
            "id": conv_id,
            "timestamp": datetime.now().isoformat(),
            "messages": messages[-50:]  # Keep last 50 messages
        }
        
        # Keep only last 100 conversations
        if len(self.conversations) > 100:
            # Remove oldest
            oldest = min(self.conversations.keys(), key=lambda k: self.conversations[k]["timestamp"])
            del self.conversations[oldest]
        
        self._save_json(self.conversations_file, self.conversations)
    
    def load_recent_conversations(self, limit: int = 5) -> List[Dict]:
        """Load recent conversations"""
        sorted_convs = sorted(
            self.conversations.values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        return sorted_convs[:limit]
    
    # ==================== KNOWLEDGE BASE ====================
    
    def add_knowledge(self, topic: str, content: str):
        """Add knowledge about a topic"""
        if topic not in self.knowledge:
            self.knowledge[topic] = []
        
        self.knowledge[topic].append({
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_json(self.knowledge_file, self.knowledge)
        logger.info(f"📚 Knowledge added: {topic}")
    
    def get_knowledge(self, topic: str) -> Optional[str]:
        """Get knowledge about a topic"""
        if topic in self.knowledge:
            entries = self.knowledge[topic]
            if entries:
                return entries[-1]["content"]
        return None
    
    def search_knowledge(self, query: str) -> str:
        """Search knowledge base"""
        results = []
        
        for topic, entries in self.knowledge.items():
            if query.lower() in topic.lower():
                results.append(f"📚 {topic}")
                for entry in entries[-2:]:
                    results.append(f"   - {entry['content'][:100]}...")
        
        if not results:
            return "❌ Bilim topilmadi"
        
        return "\n".join(results)
    
    # ==================== PREFERENCES ====================
    
    def learn_preference(self, key: str, value: Any):
        """Learn user preference"""
        if key not in self.preferences:
            self.preferences[key] = {"values": [], "count": 0}
        
        if value not in self.preferences[key]["values"]:
            self.preferences[key]["values"].append(value)
        
        self.preferences[key]["count"] += 1
        self._save_json(self.preferences_file, self.preferences)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get learned preference"""
        if key in self.preferences and self.preferences[key]["values"]:
            return self.preferences[key]["values"][-1]
        return default
    
    # ==================== STATS ====================
    
    def get_stats(self) -> str:
        """Get memory statistics"""
        total_memories = len(self.memories)
        total_conversations = len(self.conversations)
        total_knowledge = len(self.knowledge)
        total_preferences = len(self.preferences)
        
        # Calculate memory usage
        try:
            total_size = sum(
                os.path.getsize(f) 
                for f in [self.memories_file, self.conversations_file, self.knowledge_file, self.preferences_file]
                if f.exists()
            )
            size_mb = total_size / (1024 * 1024)
        except Exception as e:
            size_mb = 0
        
        return f"""💾 **Xotira Statistikasi:**

• Xotiralar soni: {total_memories}
• Suhbatlar soni: {total_conversations}
• Bilimlar soni: {total_knowledge}
• Afzalliklar: {total_preferences}
• Hajm: {size_mb:.2f} MB

*Bu xotira uzoq muddatli - sessiyalar oralig'ida saqlanadi*"""
    
    def clear(self):
        """Clear all memories"""
        self.memories = {}
        self.conversations = {}
        self.knowledge = {}
        self.preferences = {}
        
        self._save_json(self.memories_file, self.memories)
        self._save_json(self.conversations_file, self.conversations)
        self._save_json(self.knowledge_file, self.knowledge)
        self._save_json(self.preferences_file, self.preferences)
        
        logger.info("💾 All memories cleared")


# Global instance
_memory_system = None

def get_memory_system(data_dir: Path = None):
    """Get or create memory system"""
    global _memory_system
    if _memory_system is None:
        _memory_system = VectorMemory(data_dir)
    return _memory_system


# ==================== NEW: AGENT STATE MEMORY ====================

class AgentStateMemory:
    """
    Agent operating memory - tracks task states, run history, tool reliability
    Added: Task-state memory, run history, tool reliability history, session resume
    """
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "agent_state"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage files
        self.task_history_file = self.data_dir / "task_history.json"
        self.tool_reliability_file = self.data_dir / "tool_reliability.json"
        self.file_changes_file = self.data_dir / "file_changes.json"
        self.error_patterns_file = self.data_dir / "error_patterns.json"
        self.session_resume_file = self.data_dir / "session_resume.json"
        
        # Load data
        self.task_history = self._load_json(self.task_history_file)
        self.tool_reliability = self._load_json(self.tool_reliability_file)
        self.file_changes = self._load_json(self.file_changes_file)
        self.error_patterns = self._load_json(self.error_patterns_file)
        self.session_resume = self._load_json(self.session_resume_file)
        
        logger.info("🧠 Agent State Memory initialized")
    
    def _load_json(self, filepath: Path) -> Dict:
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e: logger.warning(f"Exception: {e}")
        return {}
    
    def _save_json(self, filepath: Path, data: Dict):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
    
    # ==================== TASK STATE MEMORY ====================
    
    def save_task_state(self, task_id: str, state: Dict):
        """Save task state"""
        self.task_history[task_id] = {
            "id": task_id,
            "state": state,
            "timestamp": datetime.now().isoformat()
        }
        self._save_json(self.task_history_file, self.task_history)
    
    def get_task_state(self, task_id: str) -> Optional[Dict]:
        """Get task state"""
        return self.task_history.get(task_id)
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict]:
        """Get recent tasks"""
        tasks = sorted(
            self.task_history.values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        return tasks[:limit]
    
    # ==================== RUN HISTORY ====================
    
    def save_run(self, run_data: Dict):
        """Save run history"""
        run_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12]
        
        self.task_history[run_id] = {
            "id": run_id,
            "data": run_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Keep only last 1000 runs
        if len(self.task_history) > 1000:
            oldest = sorted(
                self.task_history.keys(),
                key=lambda k: self.task_history[k].get("timestamp", "")
            )[:100]
            for key in oldest:
                del self.task_history[key]
        
        self._save_json(self.task_history_file, self.task_history)
    
    def get_run_stats(self) -> Dict:
        """Get run statistics"""
        total_runs = len(self.task_history)
        
        # Calculate success rate
        successful = sum(
            1 for t in self.task_history.values()
            if t.get("data", {}).get("success", False)
        )
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful,
            "success_rate": successful / max(total_runs, 1)
        }
    
    # ==================== TOOL RELIABILITY HISTORY ====================
    
    def record_tool_use(self, tool_name: str, success: bool, duration: float, error: str = None):
        """Record tool usage for reliability tracking"""
        if tool_name not in self.tool_reliability:
            self.tool_reliability[tool_name] = {
                "total_uses": 0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0.0,
                "errors": []
            }
        
        stats = self.tool_reliability[tool_name]
        stats["total_uses"] += 1
        stats["total_duration"] += duration
        
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            if error:
                stats["errors"].append({
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                })
                # Keep only last 10 errors
                stats["errors"] = stats["errors"][-10:]
        
        self._save_json(self.tool_reliability_file, self.tool_reliability)
    
    def get_tool_reliability(self, tool_name: str) -> Dict:
        """Get reliability stats for a tool"""
        if tool_name not in self.tool_reliability:
            return {"total_uses": 0, "success_rate": 0.0}
        
        stats = self.tool_reliability[tool_name]
        return {
            "total_uses": stats["total_uses"],
            "successes": stats["successes"],
            "failures": stats["failures"],
            "success_rate": stats["successes"] / max(stats["total_uses"], 1),
            "avg_duration": stats["total_duration"] / max(stats["total_uses"], 1),
            "recent_errors": stats["errors"][-3:]
        }
    
    def get_most_reliable_tools(self, limit: int = 5) -> List[Dict]:
        """Get most reliable tools"""
        tools = []
        
        for name, stats in self.tool_reliability.items():
            if stats["total_uses"] > 0:
                tools.append({
                    "name": name,
                    "success_rate": stats["successes"] / stats["total_uses"],
                    "total_uses": stats["total_uses"]
                })
        
        tools.sort(key=lambda x: x["success_rate"], reverse=True)
        return tools[:limit]
    
    # ==================== FILE CHANGE MEMORY ====================
    
    def record_file_change(self, filepath: str, change_type: str, content_preview: str = ""):
        """Record file change"""
        file_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
        
        if file_id not in self.file_changes:
            self.file_changes[file_id] = {
                "filepath": filepath,
                "changes": []
            }
        
        self.file_changes[file_id]["changes"].append({
            "type": change_type,
            "timestamp": datetime.now().isoformat(),
            "preview": content_preview[:100] if content_preview else ""
        })
        
        # Keep only last 20 changes per file
        self.file_changes[file_id]["changes"] = self.file_changes[file_id]["changes"][-20:]
        
        self._save_json(self.file_changes_file, self.file_changes)
    
    def get_file_history(self, filepath: str) -> List[Dict]:
        """Get file change history"""
        file_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
        
        if file_id in self.file_changes:
            return self.file_changes[file_id]["changes"]
        
        return []
    
    # ==================== ERROR PATTERN MEMORY ====================
    
    def record_error_pattern(self, error_type: str, error_message: str, solution: str = ""):
        """Record error pattern"""
        pattern_id = hashlib.md5(error_type.encode()).hexdigest()[:12]
        
        self.error_patterns[pattern_id] = {
            "type": error_type,
            "message": error_message[:200],
            "solution": solution,
            "occurrences": self.error_patterns.get(pattern_id, {}).get("occurrences", 0) + 1,
            "last_seen": datetime.now().isoformat()
        }
        
        self._save_json(self.error_patterns_file, self.error_patterns)
    
    def get_common_errors(self, limit: int = 10) -> List[Dict]:
        """Get most common errors"""
        errors = list(self.error_patterns.values())
        errors.sort(key=lambda x: x.get("occurrences", 0), reverse=True)
        return errors[:limit]
    
    # ==================== SESSION RESUME ====================
    
    def save_session_state(self, session_id: str, state: Dict):
        """Save session state for resume"""
        self.session_resume[session_id] = {
            "state": state,
            "timestamp": datetime.now().isoformat()
        }
        
        self._save_json(self.session_resume_file, self.session_resume)
    
    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """Get session state for resume"""
        return self.session_resume.get(session_id)
    
    def get_latest_session(self) -> Optional[Dict]:
        """Get latest session state"""
        if not self.session_resume:
            return None
        
        latest = max(
            self.session_resume.items(),
            key=lambda x: x[1].get("timestamp", "")
        )
        
        return latest[1]
    
    def clear_session(self, session_id: str):
        """Clear session state"""
        if session_id in self.session_resume:
            del self.session_resume[session_id]
            self._save_json(self.session_resume_file, self.session_resume)
    
    # ==================== STATS ====================
    
    def get_all_stats(self) -> str:
        """Get all memory stats"""
        run_stats = self.get_run_stats()
        reliable_tools = self.get_most_reliable_tools(5)
        common_errors = self.get_common_errors(5)
        
        stats = f"""🧠 **Agent State Memory:**

📊 **Run History:**
- Total runs: {run_stats['total_runs']}
- Success rate: {run_stats['success_rate']:.1%}

🔧 **Tool Reliability:**
"""
        
        for tool in reliable_tools:
            stats += f"- {tool['name']}: {tool['success_rate']:.1%} ({tool['total_uses']} uses)\n"
        
        stats += "\n❌ **Common Errors:**\n"
        
        for error in common_errors:
            stats += f"- {error['type']}: {error['occurrences']} times\n"
        
        return stats


# Global state memory instance
_state_memory = None

def get_agent_state_memory(data_dir: Path = None):
    """Get or create agent state memory"""
    global _state_memory
    if _state_memory is None:
        _state_memory = AgentStateMemory(data_dir)
    return _state_memory

# ==================== ENHANCED PROCEDURAL MEMORY ====================

class ProceduralMemory:
    """
    Enhanced procedural memory with 4-layer architecture:
    - Working: current task context
    - Episodic: failed/success experiences
    - - Semantic: general knowledge
    - Procedural: learned procedures
    """
    
    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 4 Layers
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralStore()
        
    def store_task_context(self, task_id: str, context: Dict):
        """Store working memory for current task"""
        self.working.store(task_id, context)
        
    def record_episode(self, episode: Dict):
        """Record an episodic memory (success/failure)"""
        self.episodic.store(episode)
        
    def store_knowledge(self, key: str, value: Any):
        """Store semantic knowledge"""
        self.semantic.store(key, value)
        
    def store_procedure(self, name: str, steps: List[Dict]):
        """Store a procedure"""
        self.procedural.store(name, steps)
        
    def get_relevant(self, query: str) -> List[Dict]:
        """Get relevant memories from all layers"""
        results = []
        results.extend(self.working.search(query))
        results.extend(self.episodic.search(query))
        results.extend(self.semantic.search(query))
        results.extend(self.procedural.search(query))
        return results

    # ==================== TOOL RELIABILITY (if missing) ====================
    
    def record_tool_usage(self, tool_name: str, success: bool, duration: float):
        """Record tool usage for reliability tracking"""
        if not hasattr(self, 'tool_reliability_history'):
            from collections import defaultdict
            self.tool_reliability_history = defaultdict(lambda: {"success": 0, "failure": 0, "total": 0})
        
        stats = self.tool_reliability_history[tool_name]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
        stats["last_used"] = time.time()
        stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0
        
    def get_unreliable_tools(self, threshold: float = 0.5) -> List[Dict]:
        """Get tools that frequently fail"""
        if not hasattr(self, 'tool_reliability_history'):
            return []
        unreliable = []
        for tool, stats in self.tool_reliability_history.items():
            if stats.get("success_rate", 1.0) < threshold:
                unreliable.append({"tool": tool, "success_rate": stats["success_rate"], "failure_count": stats["failure"]})
        return sorted(unreliable, key=lambda x: x["failure_count"], reverse=True)

    # ==================== PATCH MEMORIES (if missing) ====================
    
    def record_failed_patch(self, patch_info: Dict):
        """Record a failed patch"""
        if not hasattr(self, 'failed_patch_memory'):
            self.failed_patch_memory = {}
        patch_id = patch_info.get("patch_id", str(time.time()))
        self.failed_patch_memory[patch_id] = patch_info
        
    def record_accepted_patch(self, patch_id: str, reason: str, success_rate: float, benchmark_improvement: float):
        """Record an accepted patch"""
        if not hasattr(self, 'accepted_patch_memory'):
            self.accepted_patch_memory = {}
        self.accepted_patch_memory[patch_id] = {"reason": reason, "success_rate": success_rate, "benchmark_improvement": benchmark_improvement}
        
    def record_rejected_patch(self, patch_id: str, reason: str):
        """Record a rejected patch"""
        if not hasattr(self, 'rejected_patch_memory'):
            self.rejected_patch_memory = {}
        self.rejected_patch_memory[patch_id] = {"reason": reason}

    # ==================== BENCHMARK LINEAGE ====================
    
    def record_benchmark_result(self, benchmark_id: str, patch_id: str, score: float):
        """Record benchmark result over time"""
        if not hasattr(self, 'benchmark_lineage'):
            self.benchmark_lineage = {}
        if benchmark_id not in self.benchmark_lineage:
            self.benchmark_lineage[benchmark_id] = {"scores": [], "patch_id": patch_id}
        self.benchmark_lineage[benchmark_id]["scores"].append(score)
        
    def get_benchmark_trend(self, benchmark_id: str) -> Dict:
        """Get benchmark performance trend"""
        if not hasattr(self, 'benchmark_lineage') or benchmark_id not in self.benchmark_lineage:
            return {}
        scores = self.benchmark_lineage[benchmark_id].get("scores", [])
        if len(scores) < 2:
            return {"trend": "insufficient_data"}
        recent = sum(scores[-3:]) / min(3, len(scores))
        older = sum(scores[:3]) / min(3, len(scores))
        return {"trend": "improving" if recent > older else "declining" if recent < older else "stable", "change_percent": ((recent-older)/older*100) if older>0 else 0}




class WorkingMemory:
    """Layer 1: Current task context"""
    
    def __init__(self):
        self.contexts = {}
        
    def store(self, task_id: str, context: Dict):
        self.contexts[task_id] = {
            "context": context,
            "timestamp": time.time()
        }
        
    def get(self, task_id: str) -> Optional[Dict]:
        return self.contexts.get(task_id)
        
    def search(self, query: str) -> List[Dict]:
        # Search in current working contexts
        results = []
        for task_id, data in self.contexts.items():
            if query.lower() in str(data["context"]).lower():
                results.append({"type": "working", "task_id": task_id, "data": data})
        return results


class EpisodicMemory:
    """Layer 2: Failed/success experiences"""
    
    def __init__(self):
        self.episodes = []
        self.failed_patches = []
        self.tool_reliability = defaultdict(lambda: {"success": 0, "failure": 0})
        self.recovery_history = []
        
    def store(self, episode: Dict):
        self.episodes.append(episode)
        # Keep last 1000
        if len(self.episodes) > 1000:
            self.episodes = self.episodes[-1000:]
            
    def record_failed_patch(self, patch_info: Dict):
        """Record a failed patch for learning"""
        self.failed_patches.append({
            **patch_info,
            "timestamp": time.time()
        })
        
    def record_tool_use(self, tool_name: str, success: bool):
        """Record tool reliability"""
        if success:
            self.tool_reliability[tool_name]["success"] += 1
        else:
            self.tool_reliability[tool_name]["failure"] += 1
            
    def get_tool_reliability(self, tool_name: str) -> float:
        """Get tool reliability score"""
        stats = self.tool_reliability[tool_name]
        total = stats["success"] + stats["failure"]
        return stats["success"] / total if total > 0 else 0.5
        
    def search(self, query: str) -> List[Dict]:
        results = []
        for ep in self.episodes[-100:]:
            if query.lower() in str(ep).lower():
                results.append({"type": "episodic", "data": ep})
        return results


class SemanticMemory:
    """Layer 3: General knowledge"""
    
    def __init__(self):
        self.knowledge = {}
        
    def store(self, key: str, value: Any):
        self.knowledge[key] = {
            "value": value,
            "timestamp": time.time()
        }
        
    def get(self, key: str) -> Optional[Any]:
        return self.knowledge.get(key, {}).get("value")
        
    def search(self, query: str) -> List[Dict]:
        results = []
        for key, data in self.knowledge.items():
            if query.lower() in key.lower() or query.lower() in str(data["value"]).lower():
                results.append({"type": "semantic", "key": key, "data": data})
        return results


class ProceduralStore:
    """Layer 4: Learned procedures"""
    
    def __init__(self):
        self.procedures = {}
        self.benchmark_history = []
        self.approval_history = []
        
    def store(self, name: str, steps: List[Dict]):
        self.procedures[name] = {
            "steps": steps,
            "timestamp": time.time(),
            "usage_count": 0
        }
        
    def get(self, name: str) -> Optional[Dict]:
        if name in self.procedures:
            self.procedures[name]["usage_count"] += 1
        return self.procedures.get(name)
        
    def record_benchmark(self, benchmark_info: Dict):
        """Record benchmark result"""
        self.benchmark_history.append({
            **benchmark_info,
            "timestamp": time.time()
        })
        
    def record_approval(self, approval_info: Dict):
        """Record approval decision"""
        self.approval_history.append({
            **approval_info,
            "timestamp": time.time()
        })
        
    def search(self, query: str) -> List[Dict]:
        results = []
        for name, data in self.procedures.items():
            if query.lower() in name.lower():
                results.append({"type": "procedural", "name": name, "data": data})
        return results


# ==================== MEMORY GOVERNANCE ====================

class MemoryGovernance:
    LAYER_CONFIG = {
        "working": {"max_items": 100, "ttl_seconds": 3600, "eviction": "lru"},
        "episodic": {"max_items": 1000, "ttl_seconds": 86400*30, "eviction": "importance"},
        "semantic": {"max_items": 10000, "ttl_seconds": 86400*365, "eviction": "confidence"},
        "procedural": {"max_items": 5000, "ttl_seconds": 86400*365*5, "eviction": "usage"}
    }
    
    def __init__(self):
        self.layer_stats = defaultdict(dict)
        self.last_gc = time.time()
        self.gc_interval = 3600
    
    def should_evict(self, layer, current_count):
        config = self.LAYER_CONFIG.get(layer, {})
        return current_count >= config.get("max_items", 1000)
    
    def run_gc(self, memory_system):
        current_time = time.time()
        results = {"evicted": {}, "preserved": {}}
        if current_time - self.last_gc < self.gc_interval:
            return results
        self.last_gc = current_time
        return results
    
    def get_layer_health(self, memory_system):
        health = {}
        for layer_name in ["working", "episodic", "semantic", "procedural"]:
            layer = getattr(memory_system, layer_name, None)
            if not layer:
                continue
            config = self.LAYER_CONFIG[layer_name]
            count = len(getattr(layer, 'memories', {}) or getattr(layer, 'contexts', {}) or getattr(layer, 'procedures', {}))
            health[layer_name] = {"count": count, "max": config["max_items"], "usage_percent": (count/config["max_items"])*100}
        return health


def create_memory_system(data_dir=None):
    return UnifiedMemory(data_dir=data_dir)


# ==================== PROCEDURAL LEARNING MEMORY ====================
# Specialized memory for self-improvement learning

class ProceduralLearningMemory:
    """
    Procedural Learning Memory for Self-Improvement
    
    Tracks:
    - Which patches were accepted
    - Which patches were rejected
    - Which recoveries worked
    - Which tools crashed frequently
    - Which benchmarks dropped
    
    This is the "No1 learning memory" for autonomous improvement.
    """
    
    def __init__(self, data_dir: str = "data/procedural_memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Core learning data
        self.patch_history: List[Dict] = []
        self.recovery_history: List[Dict] = []
        self.tool_failures: Dict[str, Dict] = {}
        self.benchmark_history: List[Dict] = []
        
        # Learning indices
        self._build_indices()
        
        # Statistics
        self.stats = {
            "total_patches": 0,
            "accepted_patches": 0,
            "rejected_patches": 0,
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "total_benchmarks": 0,
            "failed_benchmarks": 0
        }
        
        logger.info("🧠 Procedural Learning Memory initialized")
    
    def _build_indices(self):
        """Build indices for fast lookup"""
        self.patch_by_type: Dict[str, List[Dict]] = defaultdict(list)
        self.patch_by_error: Dict[str, List[Dict]] = defaultdict(list)
        self.recovery_by_type: Dict[str, List[Dict]] = defaultdict(list)
        self.tool_by_category: Dict[str, List[Dict]] = defaultdict(list)
    
    # ==================== PATCH LEARNING ====================
    
    def record_patch(self, patch_info: Dict):
        """
        Record a patch attempt for learning.
        
        Stores:
        - patch_id, file_path, error_type
        - root_cause, fix_strategy
        - result: accepted/rejected
        - execution_time, iterations
        """
        patch_info["timestamp"] = time.time()
        patch_info["id"] = patch_info.get("id", str(uuid.uuid4())[:8])
        
        self.patch_history.append(patch_info)
        
        # Update indices
        error_type = patch_info.get("error_type", "unknown")
        self.patch_by_type[patch_info.get("result", "unknown")].append(patch_info)
        self.patch_by_error[error_type].append(patch_info)
        
        # Update stats
        self.stats["total_patches"] += 1
        if patch_info.get("result") == "accepted":
            self.stats["accepted_patches"] += 1
        else:
            self.stats["rejected_patches"] += 1
        
        self._save_patch_history()
        
        logger.info(f"🩹 Recorded patch: {patch_info['id']} - {patch_info.get('result')}")
    
    def get_successful_patches(self, error_type: str = None) -> List[Dict]:
        """Get patches that were accepted, optionally filtered by error type"""
        if error_type:
            return [p for p in self.patch_by_error.get(error_type, []) 
                   if p.get("result") == "accepted"]
        return [p for p in self.patch_history if p.get("result") == "accepted"]
    
    def get_rejected_patches(self, error_type: str = None) -> List[Dict]:
        """Get patches that were rejected"""
        if error_type:
            return [p for p in self.patch_by_error.get(error_type, []) 
                   if p.get("result") == "rejected"]
        return [p for p in self.patch_history if p.get("result") == "rejected"]
    
    def get_best_fix_strategy(self, error_type: str) -> Optional[Dict]:
        """Get the best fix strategy for an error type based on history"""
        successful = self.get_successful_patches(error_type)
        
        if not successful:
            return None
        
        # Find strategy with highest success rate
        strategies = {}
        for patch in successful:
            strategy = patch.get("fix_strategy", "unknown")
            if strategy not in strategies:
                strategies[strategy] = {"success": 0, "total": 0}
            strategies[strategy]["success"] += 1
            strategies[strategy]["total"] += 1
        
        # Return best strategy
        best = max(strategies.items(), key=lambda x: x[1]["success"] / max(1, x[1]["total"]))
        
        return {
            "strategy": best[0],
            "success_rate": best[1]["success"] / max(1, best[1]["total"]),
            "sample_count": best[1]["total"]
        }
    
    # ==================== RECOVERY LEARNING ====================
    
    def record_recovery(self, recovery_info: Dict):
        """
        Record a recovery attempt.
        
        Stores:
        - recovery_type, trigger_event
        - strategy_used, result
        - time_to_recover
        """
        recovery_info["timestamp"] = time.time()
        recovery_info["id"] = recovery_info.get("id", str(uuid.uuid4())[:8])
        
        self.recovery_history.append(recovery_info)
        
        # Update index
        recovery_type = recovery_info.get("recovery_type", "unknown")
        self.recovery_by_type[recovery_type].append(recovery_info)
        
        # Update stats
        self.stats["total_recoveries"] += 1
        if recovery_info.get("result") == "success":
            self.stats["successful_recoveries"] += 1
        
        self._save_recovery_history()
        
        logger.info(f"🔧 Recorded recovery: {recovery_info['id']} - {recovery_info.get('result')}")
    
    def get_successful_recoveries(self, recovery_type: str = None) -> List[Dict]:
        """Get recoveries that succeeded"""
        if recovery_type:
            return [r for r in self.recovery_by_type.get(recovery_type, [])
                   if r.get("result") == "success"]
        return [r for r in self.recovery_history if r.get("result") == "success"]
    
    def get_best_recovery_strategy(self, trigger_event: str) -> Optional[Dict]:
        """Get the best recovery strategy for a trigger event"""
        successful = [r for r in self.recovery_history 
                     if r.get("trigger_event") == trigger_event 
                     and r.get("result") == "success"]
        
        if not successful:
            return None
        
        strategies = {}
        for recovery in successful:
            strategy = recovery.get("strategy_used", "unknown")
            if strategy not in strategies:
                strategies[strategy] = 0
            strategies[strategy] += 1
        
        best = max(strategies.items(), key=lambda x: x[1])
        
        return {
            "strategy": best[0],
            "uses": best[1],
            "trigger": trigger_event
        }
    
    # ==================== TOOL FAILURE LEARNING ====================
    
    def record_tool_failure(self, tool_name: str, failure_info: Dict):
        """
        Record a tool failure.
        
        Tracks:
        - tool_name, error_type, error_message
        - frequency, last_failure
        - recovery_action
        """
        if tool_name not in self.tool_failures:
            self.tool_failures[tool_name] = {
                "tool_name": tool_name,
                "failure_count": 0,
                "failures": [],
                "last_failure": None,
                "recovery_actions": []
            }
        
        failure_info["timestamp"] = time.time()
        self.tool_failures[tool_name]["failure_count"] += 1
        self.tool_failures[tool_name]["failures"].append(failure_info)
        self.tool_failures[tool_name]["last_failure"] = failure_info["timestamp"]
        
        if failure_info.get("recovery_action"):
            self.tool_failures[tool_name]["recovery_actions"].append(
                failure_info["recovery_action"]
            )
        
        self._save_tool_failures()
        
        logger.warning(f"🔴 Tool failure recorded: {tool_name} (total: {self.tool_failures[tool_name]['failure_count']})")
    
    def get_failing_tools(self, min_failures: int = 3) -> List[Dict]:
        """Get tools that fail frequently"""
        failing = []
        
        for tool_name, data in self.tool_failures.items():
            if data["failure_count"] >= min_failures:
                failing.append({
                    "tool_name": tool_name,
                    "failure_count": data["failure_count"],
                    "last_failure": data["last_failure"],
                    "recovery_actions": data.get("recovery_actions", [])
                })
        
        # Sort by failure count
        failing.sort(key=lambda x: x["failure_count"], reverse=True)
        
        return failing
    
    def get_tool_patterns(self, tool_name: str) -> Dict:
        """Get failure patterns for a specific tool"""
        if tool_name not in self.tool_failures:
            return {}
        
        data = self.tool_failures[tool_name]
        
        # Analyze error types
        error_types = {}
        for failure in data.get("failures", []):
            error = failure.get("error_type", "unknown")
            error_types[error] = error_types.get(error, 0) + 1
        
        return {
            "total_failures": data["failure_count"],
            "error_types": error_types,
            "common_recovery": self._most_common(data.get("recovery_actions", []))
        }
    
    def _most_common(self, items: List) -> Optional[Any]:
        """Get most common item in list"""
        if not items:
            return None
        counts = Counter(items)
        return counts.most_common(1)[0][0] if counts else None
    
    # ==================== BENCHMARK LEARNING ====================
    
    def record_benchmark(self, benchmark_info: Dict):
        """
        Record a benchmark result.
        
        Tracks:
        - benchmark_name, score
        - delta_from_baseline
        - passed/failed
        """
        benchmark_info["timestamp"] = time.time()
        
        self.benchmark_history.append(benchmark_info)
        
        # Update stats
        self.stats["total_benchmarks"] += 1
        if not benchmark_info.get("passed", True):
            self.stats["failed_benchmarks"] += 1
        
        self._save_benchmark_history()
        
        status = "✅" if benchmark_info.get("passed") else "❌"
        logger.info(f"{status} Benchmark recorded: {benchmark_info.get('name')} - {benchmark_info.get('score')}")
    
    def get_dropping_benchmarks(self, threshold_percent: float = 10.0) -> List[Dict]:
        """Get benchmarks that are dropping below threshold"""
        dropping = []
        
        # Group by benchmark name
        by_name = defaultdict(list)
        for b in self.benchmark_history:
            by_name[b.get("name", "unknown")].append(b)
        
        for name, benchmarks in by_name.items():
            if len(benchmarks) < 2:
                continue
            
            # Get recent and baseline
            recent = benchmarks[-1]
            baseline = benchmarks[0]
            
            recent_score = recent.get("score", 0)
            baseline_score = baseline.get("score", 0)
            
            if baseline_score > 0:
                delta_percent = ((recent_score - baseline_score) / baseline_score) * 100
                
                if delta_percent < -threshold_percent:
                    dropping.append({
                        "benchmark": name,
                        "recent_score": recent_score,
                        "baseline_score": baseline_score,
                        "delta_percent": delta_percent,
                        "sample_count": len(benchmarks)
                    })
        
        return dropping
    
    def get_benchmark_trend(self, benchmark_name: str) -> Dict:
        """Get trend for a specific benchmark"""
        benchmarks = [b for b in self.benchmark_history if b.get("name") == benchmark_name]
        
        if not benchmarks:
            return {}
        
        scores = [b.get("score", 0) for b in benchmarks]
        
        return {
            "name": benchmark_name,
            "sample_count": len(scores),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "trend": "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable"
        }
    
    # ==================== PERSISTENCE ====================
    
    def _save_patch_history(self):
        """Save patch history to disk"""
        try:
            with open(self.data_dir / "patches.json", 'w') as f:
                json.dump(self.patch_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save patch history: {e}")
    
    def _save_recovery_history(self):
        """Save recovery history to disk"""
        try:
            with open(self.data_dir / "recoveries.json", 'w') as f:
                json.dump(self.recovery_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save recovery history: {e}")
    
    def _save_tool_failures(self):
        """Save tool failures to disk"""
        try:
            with open(self.data_dir / "tool_failures.json", 'w') as f:
                json.dump(self.tool_failures, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save tool failures: {e}")
    
    def _save_benchmark_history(self):
        """Save benchmark history to disk"""
        try:
            with open(self.data_dir / "benchmarks.json", 'w') as f:
                json.dump(self.benchmark_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save benchmark history: {e}")
    
    # ==================== QUERY METHODS ====================
    
    def get_learning_summary(self) -> Dict:
        """Get comprehensive learning summary"""
        return {
            "patch_stats": {
                "total": self.stats["total_patches"],
                "accepted": self.stats["accepted_patches"],
                "rejected": self.stats["rejected_patches"],
                "success_rate": self.stats["accepted_patches"] / max(1, self.stats["total_patches"])
            },
            "recovery_stats": {
                "total": self.stats["total_recoveries"],
                "successful": self.stats["successful_recoveries"],
                "success_rate": self.stats["successful_recoveries"] / max(1, self.stats["total_recoveries"])
            },
            "tool_stats": {
                "total_tools": len(self.tool_failures),
                "failing_tools": len(self.get_failing_tools())
            },
            "benchmark_stats": {
                "total": self.stats["total_benchmarks"],
                "failed": self.stats["failed_benchmarks"],
                "dropping": len(self.get_dropping_benchmarks())
            }
        }
    
    def export_learnings(self) -> Dict:
        """Export all learnings for analysis"""
        return {
            "patches": self.patch_history[-100:],  # Last 100
            "recoveries": self.recovery_history[-100:],
            "tool_failures": self.tool_failures,
            "benchmarks": self.benchmark_history[-100:],
            "summary": self.get_learning_summary()
        }


def create_procedural_memory(data_dir: str = None) -> ProceduralLearningMemory:
    """Factory function for ProceduralLearningMemory"""
    return ProceduralLearningMemory(data_dir=data_dir)

