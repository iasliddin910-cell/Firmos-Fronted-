"""
Social Signal Observer - Ijtimoiy tarmoqlardan signal olish
=============================================================

Bu modul ijtimoiy tarmoqlardan (Reddit, Twitter, GitHub, YouTube)
foydalanuvchi signallarini - og'riq nuqtalari, istaklar, trendlarni
aniqlaydi.

Nima uchun kerak:
- Frontier AI ko'p narsani benchmark'dan ko'radi
- Lekin real demand ko'pincha odamlar shikoyatida chiqadi

Signal turlari:
- pain signal - "bu ishlamayapti"
- desire signal - "shunaqa bo'lsa zo'r bo'lardi"
- comparison signal - "falon systemda bor"
- friction signal - "juda ko'p qadam talab qilyapti"
- trust signal - "bunga ishonmadim"
- automation signal - "o'zi kirib ko'rib kelsa bo'lardi"
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import hashlib
import re

logger = logging.getLogger(__name__)


class SocialSignalType:
    """Signal turlari"""
    PAIN = "pain"           # User pain point
    DESIRE = "desire"       # User desire/wish
    COMPARISON = "comparison"  # Comparison with other systems
    FRICTION = "friction"   # Friction in workflow
    TRUST = "trust"         # Trust/distrust signal
    AUTOMATION = "automation"  # Automation desire
    PRAISE = "praise"       # Positive feedback
    TREND = "trend"         # Trending topic


class SocialSignalObserver:
    """
    Ijtimoiy tarmoqlardan signal olish
    
    Reddit, Twitter, GitHub, YouTube va boshqa platformalardan
    foydalanuvchi signallarini yig'adi.
    """
    
    def __init__(self, watch_targets: Optional[List[str]] = None):
        """
        Initialize Social Signal Observer
        
        Args:
            watch_targets: Kuzatiladigan platformalar
        """
        self.watch_targets = watch_targets or [
            "reddit", "twitter", "github", "youtube", "hackernews"
        ]
        
        # Platform configurations
        self.platforms_config = {
            "reddit": {
                "name": "Reddit",
                "subreddits": [
                    "r/ArtificialIntelligence",
                    "r/MachineLearning",
                    "r/ChatGPT",
                    "r/programming",
                    "r/learnprogramming",
                    "r/LocalLLaMA",
                    "r/ClaudeAI",
                    "r/deeplearning"
                ],
                "search_queries": [
                    "agent not working",
                    "AI coding assistant",
                    "best AI for coding",
                    "autonomous coding",
                    "AI benchmark"
                ]
            },
            "twitter": {
                "name": "Twitter/X",
                "hashtags": [
                    "#AI", "#LLM", "#ChatGPT", "#ClaudeAI",
                    "#Devin", "#DeepSeek", "#AIcoding"
                ],
                "accounts": [
                    "@openai", "@anthropicAI", "@elonmusk",
                    "@sama", "@DarioAmodei"
                ]
            },
            "github": {
                "name": "GitHub",
                "topics": [
                    "ai-agent", "autonomous-coding", "llm-agent",
                    "ai-coding-assistant", "code-generation"
                ],
                "repos_keywords": [
                    "agent", "autonomous", "self-improving"
                ]
            },
            "youtube": {
                "name": "YouTube",
                "channels": [
                    "AI Explained",
                    "Two Minute Papers",
                    "AI Jason"
                ],
                "search_queries": [
                    "AI coding agent tutorial",
                    "Devin AI review",
                    "Claude Code tutorial"
                ]
            },
            "hackernews": {
                "name": "Hacker News",
                "keywords": [
                    "AI agent", "LLM", "autonomous", "coding assistant"
                ]
            }
        }
        
        # Signal extraction patterns
        self.signal_patterns = {
            SocialSignalType.PAIN: [
                r"not working", r"doesn't work", r"broken", r"failed",
                r"error", r"bug", r"frustrat", r"annoying", r"slow",
                r"can't.*do", r"unable to", r"issue", r"problem"
            ],
            SocialSignalType.DESIRE: [
                r"wish", r"want", r"should have", r"would be nice",
                r"hope", r"please add", r"feature request",
                r"would love", r"could use"
            ],
            SocialSignalType.COMPARISON: [
                r"better than", r"worse than", r"compared to",
                r"vs\.?", r"instead of", r"prefer"
            ],
            SocialSignalType.FRICTION: [
                r"too many steps", r"complicated", r"confusing",
                r"hard to", r"difficult", r"tedious", r"manual"
            ],
            SocialSignalType.TRUST: [
                r"trust", r"reliable", r"safe", r"secure",
                r"don't trust", r"concerned", r"worried"
            ],
            SocialSignalType.AUTOMATION: [
                r"automate", r"auto", r"self.* (do|make|run)",
                r"without.*me", r"hands.*off", r"autonomous"
            ]
        }
        
        logger.info(f"🌐 Social Signal Observer initialized with: {self.watch_targets}")
    
    async def fetch(self) -> List[Dict[str, Any]]:
        """
        Barcha platformalardan signal olish
        
        Returns:
            Signal ro'yxati
        """
        signals = []
        
        # Har bir platform uchun fetch
        tasks = []
        for target in self.watch_targets:
            if target in self.platforms_config:
                tasks.append(self._fetch_platform(target))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                signals.extend(result)
        
        # Filter noise
        filtered_signals = self._filter_signals(signals)
        
        logger.info(f"📱 Fetched {len(filtered_signals)} social signals")
        return filtered_signals
    
    async def _fetch_platform(self, platform: str) -> List[Dict[str, Any]]:
        """
        Bitta platformadan signal olish
        
        Args:
            platform: Platforma nomi
            
        Returns:
            Signal ro'yxati
        """
        signals = []
        
        try:
            config = self.platforms_config.get(platform)
            if not config:
                return signals
            
            if platform == "reddit":
                signals.extend(await self._fetch_reddit(config))
            elif platform == "twitter":
                signals.extend(await self._fetch_twitter(config))
            elif platform == "github":
                signals.extend(await self._fetch_github(config))
            elif platform == "youtube":
                signals.extend(await self._fetch_youtube(config))
            elif platform == "hackernews":
                signals.extend(await self._fetch_hackernews(config))
            
        except Exception as e:
            logger.error(f"Error fetching {platform}: {e}")
        
        return signals
    
    async def _fetch_reddit(self, config: Dict) -> List[Dict[str, Any]]:
        """Reddit dan signal olish"""
        signals = []
        
        # Real implementationda Reddit API ishlatiladi
        # PRAW (Python Reddit API Wrapper)
        
        mock_signals = [
            {
                "platform": "reddit",
                "source": "r/ChatGPT",
                "content": "Claude Artifact feature is amazing, wish GPT had something similar",
                "url": "https://reddit.com/r/ChatGPT",
                "signal_type": SocialSignalType.DESIRE,
                "score": 0.8
            },
            {
                "platform": "reddit",
                "source": "r/ArtificialIntelligence",
                "content": "Devin is impressive but still struggles with complex repo refactoring",
                "url": "https://reddit.com/r/ArtificialIntelligence",
                "signal_type": SocialSignalType.PAIN,
                "score": 0.7
            },
            {
                "platform": "reddit",
                "source": "r/programming",
                "content": "The amount of context needed for AI coding assistants is getting ridiculous",
                "url": "https://reddit.com/r/programming",
                "signal_type": SocialSignalType.FRICTION,
                "score": 0.6
            }
        ]
        
        for signal in mock_signals:
            signals.append(self._create_signal(signal))
        
        return signals
    
    async def _fetch_twitter(self, config: Dict) -> List[Dict[str, Any]]:
        """Twitter dan signal olish"""
        signals = []
        
        mock_signals = [
            {
                "platform": "twitter",
                "source": "@sama",
                "content": "New GPT-4o can now browse the web autonomously for research tasks",
                "url": "https://twitter.com/sama",
                "signal_type": SocialSignalType.TREND,
                "score": 0.9
            },
            {
                "platform": "twitter",
                "source": "@AI_ER",
                "content": "Claude Code is changing how developers work locally",
                "url": "https://twitter.com/AI_ER",
                "signal_type": SocialSignalType.PRAISE,
                "score": 0.7
            }
        ]
        
        for signal in mock_signals:
            signals.append(self._create_signal(signal))
        
        return signals
    
    async def _fetch_github(self, config: Dict) -> List[Dict[str, Any]]:
        """GitHub dan signal olish"""
        signals = []
        
        mock_signals = [
            {
                "platform": "github",
                "source": "openai/swarm",
                "content": "OpenAI releases Swarm - multi-agent orchestration framework",
                "url": "https://github.com/openai/swarm",
                "signal_type": SocialSignalType.TREND,
                "score": 0.9
            },
            {
                "platform": "github",
                "source": "anthropic/claude-code",
                "content": "Claude Code - local CLI agent for development",
                "url": "https://github.com/anthropic/claude-code",
                "signal_type": SocialSignalType.TREND,
                "score": 0.8
            },
            {
                "platform": "github",
                "source": "issue",
                "content": "Agent loses context after 10+ files - memory issue needs fix",
                "url": "https://github.com/some/agent-repo/issues",
                "signal_type": SocialSignalType.PAIN,
                "score": 0.7
            }
        ]
        
        for signal in mock_signals:
            signals.append(self._create_signal(signal))
        
        return signals
    
    async def _fetch_youtube(self, config: Dict) -> List[Dict[str, Any]]:
        """YouTube dan signal olish"""
        signals = []
        
        mock_signals = [
            {
                "platform": "youtube",
                "source": "AI Explained",
                "content": "Devin vs GPT-4 - autonomous coding comparison",
                "url": "https://youtube.com/watch?v=example",
                "signal_type": SocialSignalType.COMPARISON,
                "score": 0.7
            }
        ]
        
        for signal in mock_signals:
            signals.append(self._create_signal(signal))
        
        return signals
    
    async def _fetch_hackernews(self, config: Dict) -> List[Dict[str, Any]]:
        """HackerNews dan signal olish"""
        signals = []
        
        mock_signals = [
            {
                "platform": "hackernews",
                "source": "HN",
                "content": "Show HN: New autonomous coding agent with 80% on SWE-Bench",
                "url": "https://news.ycombinator.com",
                "signal_type": SocialSignalType.TREND,
                "score": 0.8
            }
        ]
        
        for signal in mock_signals:
            signals.append(self._create_signal(signal))
        
        return signals
    
    def _create_signal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Signal obyektini yaratish"""
        content_hash = hashlib.sha256(
            f"{data['platform']}{data['content']}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        return {
            "source_type": "social",
            "platform": data["platform"],
            "source": data["source"],
            "content": data["content"],
            "url": data.get("url"),
            "signal_type": data["signal_type"],
            "confidence": data.get("score", 0.5),
            "timestamp": datetime.now().isoformat(),
            "topic_tags": self._extract_tags(data["content"]),
            "raw_data": data
        }
    
    def _extract_tags(self, content: str) -> List[str]:
        """Kontentdan teglarni ajratib olish"""
        tags = []
        
        keyword_tags = {
            "coding": ["code", "programming", "developer", "coding"],
            "agent": ["agent", "autonomous", "ai assistant"],
            "memory": ["memory", "context", "long context"],
            "benchmark": ["benchmark", "swe-bench", "humaneval"],
            "tool": ["tool", "function", "capability"]
        }
        
        content_lower = content.lower()
        for tag, keywords in keyword_tags.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    def _filter_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Signallarni filtrlash - past confidence va noise ni olib tashlash"""
        filtered = []
        
        for signal in signals:
            # Confidence threshold
            if signal.get("confidence", 0) < 0.3:
                continue
            
            # Filter very short content
            if len(signal.get("content", "")) < 20:
                continue
            
            filtered.append(signal)
        
        return filtered
    
    def classify_signal(self, content: str) -> tuple[str, float]:
        """
        Signal turini klassifikatsiya qilish
        
        Args:
            content: Signal kontenti
            
        Returns:
            (signal_type, confidence)
        """
        content_lower = content.lower()
        
        best_type = SocialSignalType.TREND
        best_score = 0.0
        
        for signal_type, patterns in self.signal_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    score += 1
            
            # Normalize score
            score = score / len(patterns) if patterns else 0
            
            if score > best_score:
                best_score = score
                best_type = signal_type
        
        return best_type, best_score
    
    def get_user_pain_points(self) -> Dict[str, List[str]]:
        """
        Foydalanuvchi og'riq nuqtalarini olish
        
        Returns:
            Og'riq nuqtalari lug'ati
        """
        return {
            "context_loss": [
                "Agent forgets context after many files",
                "Context window fills up too quickly"
            ],
            "tool_limitations": [
                "Can't use certain tools",
                "Limited browser automation"
            ],
            "autonomy": [
                "Needs too many confirmations",
                "Can't make decisions autonomously"
            ],
            "reliability": [
                "Sometimes hallucinates",
                "Produces incorrect code"
            ]
        }
    
    def get_trending_topics(self) -> List[Dict[str, Any]]:
        """Trend mavzularni olish"""
        return [
            {"topic": "Claude Code", "sentiment": "positive", "volume": "high"},
            {"topic": "Devin autonomous coding", "sentiment": "curious", "volume": "high"},
            {"topic": "SWE-Bench improvements", "sentiment": "excited", "volume": "medium"},
            {"topic": "Memory limitations", "sentiment": "negative", "volume": "medium"},
            {"topic": "Multi-agent orchestration", "sentiment": "interested", "volume": "medium"}
        ]
