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