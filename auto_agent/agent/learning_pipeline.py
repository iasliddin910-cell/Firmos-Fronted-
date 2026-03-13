"""
OmniAgent X - Continuous Learning Pipeline
==========================================
Automated learning from internet sources

Features:
- Source discovery and trust ranking
- Content extraction and processing
- Knowledge storage with embeddings
- Stale knowledge cleanup
- Auto-ingestion on schedule
- Fact freshness scoring
- Scheduled refresh
"""
import os
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class SourceType(Enum):
    """Type of knowledge source"""
    DOCUMENTATION = "documentation"
    BLOG = "blog"
    FORUM = "forum"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    PAPER = "paper"
    NEWS = "news"
    WIKI = "wiki"


class TrustLevel(Enum):
    """Trust level for sources"""
    HIGH = 3   # Official docs, peer-reviewed
    MEDIUM = 2  # Blogs, tutorials
    LOW = 1    # Forums, social media
    UNKNOWN = 0


# ==================== DATA CLASSES ====================

@dataclass
class KnowledgeSource:
    """A knowledge source"""
    url: str
    source_type: SourceType
    trust_level: TrustLevel
    last_checked: float
    last_updated: float
    content_hash: str
    fetch_count: int = 0
    error_count: int = 0


@dataclass
class KnowledgeItem:
    """A piece of knowledge"""
    id: str
    content: str
    source_url: str
    source_type: SourceType
    trust_level: TrustLevel
    embedding: List[float] = field(default_factory=list)
    created_at: float
    last_accessed: float
    access_count: int = 0
    relevance_score: float = 1.0
    freshness_score: float = 1.0
    tags: List[str] = field(default_factory=list)
    verified: bool = False


@dataclass
class LearningTask:
    """A learning task"""
    task_id: str
    source_url: str
    status: str  # pending, running, completed, failed
    created_at: float
    completed_at: Optional[float]
    items_learned: int
    error: Optional[str]


# ==================== SOURCE DISCOVERY ====================

class SourceDiscovery:
    """
    Discovers and ranks knowledge sources
    """
    
    # Known high-quality sources by category
    SOURCE_PATTERNS = {
        "python": [
            "docs.python.org",
            "peps.python.org",
            "realpython.com",
            "fullstackpython.com",
        ],
        "javascript": [
            "developer.mozilla.org",
            "nodejs.org",
            "react.dev",
            "vuejs.org",
        ],
        "ai_ml": [
            "paperswithcode.com",
            "arxiv.org",
            "huggingface.co",
            "openai.com",
        ],
        "devops": [
            "kubernetes.io",
            "docs.docker.com",
            "terraform.io",
            "github.com",
        ],
    }
    
    def __init__(self):
        self.sources: Dict[str, KnowledgeSource] = {}
        self._load_sources()
        
        logger.info("🔍 Source Discovery initialized")
    
    def discover_sources(self, topic: str) -> List[KnowledgeSource]:
        """Discover sources for a topic"""
        discovered = []
        
        # Check known patterns
        for category, patterns in self.SOURCE_PATTERNS.items():
            if topic.lower() in category or any(p in topic.lower() for p in patterns):
                for pattern in patterns:
                    if pattern not in self.sources:
                        source = KnowledgeSource(
                            url=f"https://{pattern}",
                            source_type=SourceType.DOCUMENTATION,
                            trust_level=TrustLevel.HIGH,
                            last_checked=0,
                            last_updated=time.time(),
                            content_hash=""
                        )
                        self.sources[pattern] = source
                        discovered.append(source)
        
        return discovered
    
    def get_trusted_sources(self, min_trust: TrustLevel = TrustLevel.MEDIUM) -> List[KnowledgeSource]:
        """Get sources above trust threshold"""
        return [
            s for s in self.sources.values()
            if s.trust_level.value >= min_trust.value
        ]
    
    def update_source(self, url: str, content_hash: str):
        """Update source after fetching"""
        import urllib.parse
        
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        
        if domain in self.sources:
            self.sources[domain].fetch_count += 1
            self.sources[domain].last_checked = time.time()
            
            if content_hash != self.sources[domain].content_hash:
                self.sources[domain].content_hash = content_hash
                self.sources[domain].last_updated = time.time()
        
        self._save_sources()
    
    def _save_sources(self):
        """Save sources to disk"""
        import json
        import os
        os.makedirs("data/learning", exist_ok=True)
        with open("data/learning/sources.json", "w") as f:
            json.dump(self.sources, f, indent=2, default=str)
    
    def _load_sources(self):
        """Load sources from disk"""
        import json
        import os
        sources_file = "data/learning/sources.json"
        if os.path.exists(sources_file):
            with open(sources_file, "r") as f:
                self.sources = json.load(f)


# ==================== CONTENT PROCESSOR ====================

class ContentProcessor:
    """
    Process and extract knowledge from web content
    """
    
    def __init__(self):
        self.max_content_length = 10000
        self.chunk_size = 500
        
        logger.info("📄 Content Processor initialized")
    
    def process(self, url: str, html_content: str) -> List[str]:
        """Process HTML content into knowledge chunks"""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Clean
        text = text.strip()
        
        # Truncate if too long
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length]
        
        # Chunk
        chunks = self._chunk_text(text)
        
        return chunks
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into semantic chunks"""
        chunks = []
        
        # Split by sentences (simplified)
        sentences = text.split('. ')
        
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < self.chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def extract_code_blocks(self, html_content: str) -> List[str]:
        """Extract code blocks from HTML"""
        import re
        
        # Find code blocks
        code_blocks = re.findall(r'<pre[^>]*>(.*?)</pre>', html_content, re.DOTALL)
        
        # Also find inline code
        inline = re.findall(r'<code[^>]*>(.*?)</code>', html_content, re.DOTALL)
        
        return [self._clean_code(c) for c in code_blocks + inline]
    
    def _clean_code(self, code: str) -> str:
        """Clean code block"""
        import re
        # Remove HTML entities
        code = re.sub(r'&lt;', '<', code)
        code = re.sub(r'&gt;', '>', code)
        code = re.sub(r'&amp;', '&', code)
        
        return code.strip()


# ==================== KNOWLEDGE STORE ====================

class KnowledgeStore:
    """
    Store and manage learned knowledge
    """
    
    def __init__(self, storage_dir: str = "data/knowledge"):
        self.storage_dir = os.path.join(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.items: Dict[str, KnowledgeItem] = {}
        
        # Index by tags
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Index by source
        self.source_index: Dict[str, Set[str]] = defaultdict(set)
        
        self._load()
        
        logger.info("💾 Knowledge Store initialized")
    
    def add(self, content: str, source_url: str, source_type: SourceType,
           trust_level: TrustLevel, tags: List[str] = None) -> str:
        """Add knowledge item"""
        
        # Generate ID
        content_hash = hashlib.md5(content.encode()).hexdigest()
        item_id = f"kb_{content_hash[:12]}"
        
        # Check for duplicates
        if item_id in self.items:
            # Update access time
            self.items[item_id].last_accessed = time.time()
            self.items[item_id].access_count += 1
            return item_id
        
        # Create item
        item = KnowledgeItem(
            id=item_id,
            content=content,
            source_url=source_url,
            source_type=source_type,
            trust_level=trust_level,
            created_at=time.time(),
            last_accessed=time.time(),
            tags=tags or []
        )
        
        # Index
        self.items[item_id] = item
        
        for tag in item.tags:
            self.tag_index[tag].add(item_id)
        
        self.source_index[source_url].add(item_id)
        
        self._save()
        
        return item_id
    
    def get(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get knowledge item"""
        if item_id in self.items:
            self.items[item_id].last_accessed = time.time()
            self.items[item_id].access_count += 1
            return self.items[item_id]
        return None
    
    def search(self, query: str, tags: List[str] = None,
              min_trust: TrustLevel = TrustLevel.LOW) -> List[KnowledgeItem]:
        """Search knowledge"""
        results = []
        
        # Filter by tags if specified
        if tags:
            candidate_ids = set()
            for tag in tags:
                candidate_ids.update(self.tag_index.get(tag, set()))
        else:
            candidate_ids = set(self.items.keys())
        
        # Filter by trust and relevance
        for item_id in candidate_ids:
            item = self.items[item_id]
            
            if item.trust_level.value < min_trust.value:
                continue
            
            # Simple relevance - check if query in content
            if query.lower() in item.content.lower():
                results.append(item)
        
        # Sort by relevance and freshness
        results.sort(
            key=lambda x: (x.relevance_score * x.freshness_score, x.access_count),
            reverse=True
        )
        
        return results[:20]
    
    def get_by_source(self, source_url: str) -> List[KnowledgeItem]:
        """Get all items from source"""
        item_ids = self.source_index.get(source_url, set())
        return [self.items[i] for i in item_ids if i in self.items]
    
    def prune_stale(self, max_age_days: int = 90, min_trust: TrustLevel = TrustLevel.MEDIUM):
        """Remove stale knowledge"""
        removed = []
        
        cutoff_time = time.time() - (max_age_days * 86400)
        
        for item_id, item in list(self.items.items()):
            # Don't remove high-trust items
            if item.trust_level == TrustLevel.HIGH:
                continue
            
            # Remove if old and low access
            if item.last_accessed < cutoff_time and item.access_count < 3:
                del self.items[item_id]
                
                # Remove from indexes
                for tag in item.tags:
                    self.tag_index[tag].discard(item_id)
                
                self.source_index[item.source_url].discard(item_id)
                
                removed.append(item_id)
        
        if removed:
            self._save()
            logger.info(f"🗑️ Pruned {len(removed)} stale items")
        
        return removed
    
    def deduplicate(self):
        """Remove duplicate knowledge using content hashing"""
        import hashlib
        
        seen_hashes = set()
        removed = []
        
        for item_id in list(self.items.keys()):
            item = self.items[item_id]
            # Create hash of content
            content_hash = hashlib.md5(item.content.encode()).hexdigest()
            
            if content_hash in seen_hashes:
                # Remove duplicate
                del self.items[item_id]
                removed.append(item_id)
                # Remove from indexes
                for tag in item.tags:
                    self.tag_index[tag].discard(item_id)
                self.source_index[item.source_url].discard(item_id)
            else:
                seen_hashes.add(content_hash)
        
        if removed:
            self._save()
            logger.info(f"🗑️ Removed {len(removed)} duplicate items")
        
        return removed
    
    def get_stats(self) -> Dict:
        """Get store statistics"""
        return {
            "total_items": len(self.items),
            "by_trust": {
                "high": sum(1 for i in self.items.values() if i.trust_level == TrustLevel.HIGH),
                "medium": sum(1 for i in self.items.values() if i.trust_level == TrustLevel.MEDIUM),
                "low": sum(1 for i in self.items.values() if i.trust_level == TrustLevel.LOW),
            },
            "by_source": len(self.source_index),
            "tags": len(self.tag_index),
        }
    
    def _save(self):
        """Save to disk"""
        try:
            data = {
                "items": [
                    {
                        "id": k,
                        "content": v.content,
                        "source_url": v.source_url,
                        "source_type": v.source_type.value,
                        "trust_level": v.trust_level.value,
                        "created_at": v.created_at,
                        "last_accessed": v.last_accessed,
                        "access_count": v.access_count,
                        "tags": v.tags,
                    }
                    for k, v in self.items.items()
                ]
            }
            
            with open(os.path.join(self.storage_dir, "knowledge.json"), "w") as f:
                json.dump(data, f)
        
        except Exception as e:
            logger.error(f"Failed to save knowledge: {e}")
    
    def _load(self):
        """Load from disk"""
        try:
            path = os.path.join(self.storage_dir, "knowledge.json")
            if not os.path.exists(path):
                return
            
            with open(path, "r") as f:
                data = json.load(f)
            
            for item_data in data.get("items", []):
                item = KnowledgeItem(
                    id=item_data["id"],
                    content=item_data["content"],
                    source_url=item_data["source_url"],
                    source_type=SourceType(item_data["source_type"]),
                    trust_level=TrustLevel(item_data["trust_level"]),
                    created_at=item_data["created_at"],
                    last_accessed=item_data["last_accessed"],
                    access_count=item_data["access_count"],
                    tags=item_data["tags"]
                )
                
                self.items[item.id] = item
                
                for tag in item.tags:
                    self.tag_index[tag].add(item.id)
                
                self.source_index[item.source_url].add(item.id)
        
        except Exception as e:
            logger.error(f"Failed to load knowledge: {e}")


# ==================== CONTINUOUS LEARNING PIPELINE ====================

class ContinuousLearningPipeline:
    """
    End-to-end continuous learning system
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
        # Components
        self.discovery = SourceDiscovery()
        self.processor = ContentProcessor()
        self.store = KnowledgeStore()
        
        # Scheduler
        self.scheduled_tasks: List[Dict] = []
        self.running = False
        
        # Topics to learn
        self.topics = [
            "python",
            "javascript", 
            "ai machine learning",
            "software development",
            "devops",
        ]
        
        logger.info("📚 Continuous Learning Pipeline initialized")
    
    def learn_from_url(self, url: str, tags: List[str] = None) -> int:
        """Learn from a URL"""
        try:
            import requests
            
            # Fetch content
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine source type and trust
            source_type = self._classify_source(url)
            trust_level = self._assess_trust(url)
            
            # Process content
            chunks = self.processor.process(url, response.text)
            
            # Extract code
            code_blocks = self.processor.extract_code_blocks(response.text)
            
            # Add to store
            items_added = 0
            
            for chunk in chunks:
                self.store.add(
                    content=chunk,
                    source_url=url,
                    source_type=source_type,
                    trust_level=trust_level,
                    tags=tags
                )
                items_added += 1
            
            for code in code_blocks:
                self.store.add(
                    content=f"```\n{code}\n```",
                    source_url=url,
                    source_type=source_type,
                    trust_level=trust_level,
                    tags=tags + ["code"]
                )
                items_added += 1
            
            # Update source info
            content_hash = hashlib.md5(response.text.encode()).hexdigest()
            self.discovery.update_source(url, content_hash)
            
            logger.info(f"✅ Learned {items_added} items from {url}")
            return items_added
        
        except Exception as e:
            logger.error(f"Failed to learn from {url}: {e}")
            return 0
    
    def learn_topic(self, topic: str, max_sources: int = 5) -> int:
        """Learn about a topic"""
        total_items = 0
        
        # Discover sources
        sources = self.discovery.discover_sources(topic)
        
        for source in sources[:max_sources]:
            items = self.learn_from_url(source.url, tags=[topic])
            total_items += items
        
        return total_items
    
    def start_auto_learning(self, interval_hours: int = 24):
        """Start automatic learning on schedule"""
        self.running = True
        
        def loop():
            while self.running:
                for topic in self.topics:
                    if not self.running:
                        break
                    
                    logger.info(f"📚 Auto-learning: {topic}")
                    self.learn_topic(topic)
                
                # Sleep until next interval
                time.sleep(interval_hours * 3600)
        
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        
        logger.info(f"🔄 Auto-learning started (every {interval_hours}h)")
    
    def stop_auto_learning(self):
        """Stop automatic learning"""
        self.running = False
        logger.info("⏹️ Auto-learning stopped")
    
    def run_maintenance(self):
        """Run maintenance tasks"""
        logger.info("🔧 Running maintenance...")
        
        # Prune stale knowledge
        removed = self.store.prune_stale()
        
        # Deduplicate
        self.store.deduplicate()
        
        return f"Maintenance complete: {len(removed)} items pruned"
    
    def _classify_source(self, url: str) -> SourceType:
        """Classify source type from URL"""
        url_lower = url.lower()
        
        if "docs" in url_lower or "documentation" in url_lower:
            return SourceType.DOCUMENTATION
        elif "github.com" in url_lower:
            return SourceType.GITHUB
        elif "stackoverflow.com" in url_lower:
            return SourceType.STACKOVERFLOW
        elif "blog" in url_lower:
            return SourceType.BLOG
        elif "arxiv.org" in url_lower or "paper" in url_lower:
            return SourceType.PAPER
        elif "wiki" in url_lower:
            return SourceType.WIKI
        else:
            return SourceType.FORUM
    
    def _assess_trust(self, url: str) -> TrustLevel:
        """Assess trust level of source"""
        url_lower = url.lower()
        
        # High trust
        high_trust = ["docs.python.org", "developer.mozilla.org", "kubernetes.io",
                     "docs.docker.com", "nodejs.org", "react.dev"]
        
        if any(d in url_lower for d in high_trust):
            return TrustLevel.HIGH
        
        # Medium trust
        medium_trust = ["realpython.com", "blog.", "tutorial", "guide"]
        
        if any(d in url_lower for d in medium_trust):
            return TrustLevel.MEDIUM
        
        return TrustLevel.LOW
    
    def get_status(self) -> Dict:
        """Get pipeline status"""
        return {
            "running": self.running,
            "topics": self.topics,
            "knowledge_stats": self.store.get_stats(),
            "sources": len(self.discovery.sources)
        }




    # ==================== ADDITIONAL METHODS ====================
    
    def deduplicate(self):
        """Remove duplicate knowledge"""
        seen = set()
        unique_items = []
        for item_id, item in list(self.store.items.items()):
            content_hash = hashlib.md5(item.content.encode()).hexdigest()
            if content_hash not in seen:
                seen.add(content_hash)
                unique_items.append(item_id)
            else:
                del self.store.items[item_id]
        self.store._save()
        logger.info(f"🗑️ Deduplicated: {len(self.store.items)} unique items")
    
    def score_confidence(self, item_id: str) -> float:
        """Calculate confidence score for knowledge item"""
        item = self.store.get(item_id)
        if not item:
            return 0.0
        
        score = 1.0
        
        # Trust level factor
        trust_weights = {"high": 1.0, "medium": 0.7, "low": 0.4}
        score *= trust_weights.get(item.trust_level.value, 0.5)
        
        # Recency factor
        age_days = (time.time() - item.created_at) / 86400
        if age_days < 30:
            score *= 1.0
        elif age_days < 90:
            score *= 0.8
        else:
            score *= 0.5
        
        # Access frequency factor
        if item.access_count > 10:
            score *= 1.2
        elif item.access_count > 5:
            score *= 1.0
        else:
            score *= 0.9
        
        return min(1.0, score)
    
    def prune_by_confidence(self, min_confidence: float = 0.3):
        """Remove low confidence knowledge"""
        to_remove = []
        
        for item_id, item in list(self.store.items.items()):
            confidence = self.score_confidence(item_id)
            if confidence < min_confidence:
                to_remove.append(item_id)
        
        for item_id in to_remove:
            del self.store.items[item_id]
        
        if to_remove:
            self.store._save()
            logger.info(f"🗑️ Pruned {len(to_remove)} low confidence items")
        
        return len(to_remove)
    
    def refresh_source(self, source_url: str):
        """Refresh knowledge from a source"""
        return self.learn_from_url(source_url)


# ==================== FACTORY ====================

def create_learning_pipeline(api_key: str = None) -> ContinuousLearningPipeline:
    """Create learning pipeline"""
    return ContinuousLearningPipeline(api_key)
