"""
OmniAgent X ULTIMATE - Persistent Memory System
================================================
Long-term memory with semantic search using embeddings
"""
import os
import json
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)

# Try to import sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except:
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
        """Load JSON file"""
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
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
        except:
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
            except:
                pass
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